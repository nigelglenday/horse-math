"""
Derby handicap scoring v1.

Method:
  - Score each horse on weighted features
  - Softmax(scores * temperature) -> our win probability
  - Strip morning-line takeout -> market's true probability
  - Overlay = our_prob / market_prob

Run: python3 src/handicap.py
"""
from __future__ import annotations
import csv
import math
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELD = ROOT / "data" / "parsed" / "field.csv"
PP = ROOT / "data" / "parsed" / "past_performances.csv"
LIVE_ODDS = ROOT / "data" / "parsed" / "live_odds.csv"
OUT = ROOT / "data" / "parsed" / "overlays.csv"

# ----------------------------- FEATURE SCORERS -----------------------------
# Each scorer returns 0-100. Higher = better. None = unknown -> mean-impute later.

def trip_adj_from_comment(comment):
    """
    Derive a trip adjustment from the chart-caller's comment.
    Beyer figs don't account for wide trips, trouble, or manner of finish.
    Returns an integer in roughly [-3, +5] to add to the raw Beyer.
    """
    if not comment:
        return 0
    c = comment.lower()
    adj = 0
    # Wide trips: "4w" -> +1, "5w" -> +2, "6w" -> +3 (every path wide ~ 1pt)
    import re
    for m in re.finditer(r"(\d)\s*[wp](?:ide)?\b", c):
        try:
            n = int(m.group(1))
            if n >= 4:
                adj += (n - 3)
        except ValueError:
            pass
    # Hard cap on cumulative wide-trip credit so we don't double-count
    adj = min(adj, 4)
    # Trouble: ran better than the fig says
    for kw in ("wsteadied", "steadied", "checked", "bumped", "bobbled",
              "slip brk", "slipped", "wbpd", "wbpd st", "shuffled", "squeezed", "wsqzd"):
        if kw in c:
            adj += 2
            break  # one trouble bump max
    # Manner of finish — had more
    for kw in ("ridden out", "rddn out", "handily", "in hand"):
        if kw in c:
            adj += 2
            break
    # DQ wins (true winner)
    if "dq" in c:
        adj += 2
    # Inside / rail trips — no excuse
    for kw in ("ins,", " ins ", "rail", "saved ground"):
        if kw in c:
            adj -= 1
            break
    # Outclassed / faded
    for kw in ("yielded", "weakened", "folded", "no match", "outgamed", "no bid", "weaknd"):
        if kw in c:
            adj -= 1
            break
    return max(-3, min(5, adj))

def adjusted_beyer(pp):
    """Raw Beyer + trip adjustment derived from the comment."""
    if pp["beyer"] in ("N/A", ""):
        return None
    return int(pp["beyer"]) + trip_adj_from_comment(pp.get("comment", ""))

def f_last_beyer(pps):
    """Most recent trip-adjusted Beyer (highest predictive single number)."""
    pps = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                 key=lambda p: p["pp_date"], reverse=True)
    if not pps:
        return None
    b = adjusted_beyer(pps[0])
    # 110 -> 100, 70 -> 0, linear in [70, 110]
    return max(0, min(100, (b - 70) * 100 / 40))

def f_top3_beyer(pps):
    """Best of last 3 trip-adjusted Beyers — filters one-off bounces."""
    pps_sorted = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                        key=lambda p: p["pp_date"], reverse=True)[:3]
    if not pps_sorted:
        return None
    b = max(adjusted_beyer(p) for p in pps_sorted)
    return max(0, min(100, (b - 70) * 100 / 40))

def f_pace_fit(pps, projected_meltdown=True):
    """
    Style classified from typical 1st-call position relative to field size in last 3 starts.
    Today's race projects as a pace meltdown (multiple confirmed speeds + first-time blinkers
    on Litmus Test). Closers favored.
    """
    recent = sorted(pps, key=lambda p: p["pp_date"], reverse=True)[:3]
    if not recent:
        return 50
    style_scores = []
    for p in recent:
        try:
            ec = int(p["early_call"])
            fs = int(p["field_size"])
        except (ValueError, KeyError):
            continue
        rel = ec / fs  # 0-1, lower = closer to lead
        if rel <= 0.25:
            style_scores.append("E")     # front
        elif rel <= 0.5:
            style_scores.append("EP")    # press
        elif rel <= 0.7:
            style_scores.append("P")     # stalker
        else:
            style_scores.append("S")     # closer
    if not style_scores:
        return 50
    # Modal style
    mode = max(set(style_scores), key=style_scores.count)
    if projected_meltdown:
        return {"E": 30, "EP": 50, "P": 75, "S": 90}[mode]
    return {"E": 80, "EP": 75, "P": 70, "S": 55}[mode]

# Class-of-prep-won lookup. Keys are race_class strings as they appear in PPs.
PREP_CLASS_SCORE = {
    "Stk-FlaDerby": 100,    # Nigel's bias - historically strong Derby pipeline
    "Stk-SADerby":   95,
    "Stk-ArkDerby":  95,
    "Stk-BlueGrass": 92,
    "Stk-WoodMem":   85,
    "Stk-LaDerby":   85,
    "Stk-FntnOYth":  78,    # Fountain of Youth = FlaDerby prep
    "Stk-Rebel":     80,    # ArkDerby prep
    "Stk-SnFelipe":  78,    # SADerby prep
    "Stk-RisenStr":  72,
    "Stk-TamDby":    75,
    "Stk-VADerby":   65,
    "Stk-UAEDerby":  65,    # international discount
    "Stk-Lex":       70,
    "Stk-SmrtyJns":  60,
    "Stk-Southwst":  72,
    "Stk-LosAlFut":  72,
    "Stk-BrdrsFut":  85,
    "Stk-Remsen":    75,
    "Stk-AmPharoh":  72,
    "Stk-MuchoMM":   55,
    "Stk-SnVicnte":  65,
    "Stk-RBLewis":   72,
    "Stk-CalCupDby": 60,
    "Stk-SunDrby":   55,
    "Stk-FukuryuS":  55,    # Japan
    "Stk-PoinsettiaS": 50,
    "Stk-MochinokiSho": 50,
    "Stk-UAE2000G":  60,
    "Stk-JRSteaks":  68,
    "Stk-JBttgla":   55,
    "Stk-Leonatus":  50,
    "Stk-StretSns":  55,
    "Stk-Gotham":    72,
    "Stk-KyJC":      72,
    "Stk-Lecomte":   65,
    "Stk-SFDavis":   70,
}
DEFAULT_PREP_SCORE = 35  # maiden / allowance / unrecognized

def f_class_of_preps(pps):
    """Score class of races where horse won or finished close (top 2)."""
    best = 0
    for p in pps:
        if p["finish_pos"] not in ("1", "2"):
            continue
        cls = p["race_class"]
        score = PREP_CLASS_SCORE.get(cls, DEFAULT_PREP_SCORE)
        # Win > 2nd
        if p["finish_pos"] == "1":
            score = score
        else:
            score = score * 0.65
        # Distance discount if won at sprint
        try:
            d = float(p["dist_f"])
            if d < 8.0:
                score *= 0.7
        except ValueError:
            pass
        best = max(best, score)
    return min(100, best)

def f_how_won(pps):
    """Quality of recent wins — daylight or impressive comments."""
    wins = [p for p in pps if p["won"] == "1"]
    if not wins:
        return 30
    last_wins = sorted(wins, key=lambda p: p["pp_date"], reverse=True)[:2]
    score = 0
    for w in last_wins:
        try:
            margin = float(str(w["fin_margin"]).replace("DQ", "0"))
        except ValueError:
            margin = 1.0
        # Daylight win = strong
        s = 40 + min(40, margin * 8)  # 1L = 48, 3L = 64, 5L = 80
        comment = w.get("comment", "").lower()
        if any(k in comment for k in ("drove clear", "drew off", "kicked clear", "ridden out", "drwclr", "drove past")):
            s += 15
        if any(k in comment for k in ("driving", "all out", "gamely", "nailed", "missed")):
            s += 5
        score = max(score, s)
    return min(100, score)

def f_distance_fit(pps, sire):
    """
    Has horse run competitively at 9F+? Pedigree distance bias on dam-sire would be ideal
    but we only have sire here. Approximation.
    """
    score = 30  # baseline
    long_starts = [p for p in pps if float(p.get("dist_f") or 0) >= 9.0]
    if long_starts:
        beyers = [int(p["beyer"]) for p in long_starts if p["beyer"] not in ("N/A", "")]
        if beyers:
            top = max(beyers)
            score = max(0, min(100, (top - 70) * 100 / 40))
    # Sire stamina bias (rough)
    stamina_sires = {"Curlin", "Tapit", "Liam s Map", "Constitution", "Into Mischief",
                     "Sky Mesa", "Maxfield", "Blame", "Practical Joke"}
    speed_sires = {"Pavel", "Volatile", "Yaupon", "Connect", "Accelerate"}
    if sire in stamina_sires:
        score += 10
    elif sire in speed_sires:
        score -= 10
    return max(0, min(100, score))

TRAINER_DERBY_SCORE = {
    "Bob Baffert":           95,    # 6 Derbies
    "Todd Pletcher":         80,    # 2 Derbies
    "Brad Cox":              80,
    "Doug O Neill":          82,    # 2 Derbies
    "Kenneth G McPeek":      78,    # Mystik Dan 2024
    "William I Mott":        72,
    "Chad Brown":            70,
    "Mark Casse":            65,
    "Cherie DeVaux":         55,
    "Dallas Stewart":        65,    # multiple Derby longshot 2nds
    "Jeff Mullins":          40,
    "Mark Glatt":            45,
    "Gustavo Delgado":       55,
    "Riley Mott":            55,    # Wm Mott's son
    "John Ennis":            40,
    "D Whitworth Beckman":   35,
    "Manabu Ikezoe":         55,    # Japan
    "Daisuke Takayanagi":    55,    # Japan
    "Bhupat Seemar":         55,    # UAE
    "Dallas Stewart":        65,
}

JOCKEY_BIG_RACE = {
    "John R Velazquez":  100,    # 3 Derbies
    "Mike E Smith":       95,    # 3 Derbies
    "Irad Ortiz Jr":      88,
    "Flavien Prat":       92,    # 1 Derby
    "Luis Saez":          85,
    "Javier Castellano":  82,
    "Tyler Gaffalione":   85,    # Mystik Dan 2024
    "Junior Alvarado":    72,
    "Jose L Ortiz":       78,
    "Brian J Hernandez Jr": 75,
    "Juan J Hernandez":   72,
    "Edwin A Maldonado":  55,
    "Martin Garcia":      62,
    "Cristian A Torres":  60,
    "Jaime A Torres":     60,
    "Manuel Franco":      62,
    "Hector I Berrios":   55,
    "Christopher Elliott": 50,
    "Atsuya Nishimura":   60,
    "Ryusei Sakai":       55,
    "Alex Achard":         35,
    "Emisael Jaramillo":   50,
    "Joseph D Ramos":      40,
}

def f_connections(trainer, jockey):
    t = TRAINER_DERBY_SCORE.get(trainer, 50)
    j = JOCKEY_BIG_RACE.get(jockey, 55)
    return 0.5 * t + 0.5 * j

def f_equipment(horse, blinker_change_today):
    if blinker_change_today:
        return 80   # first-time blinkers, modest positive
    return 50

def f_post(pp):
    """Post position penalty/bonus for 20-horse Derby."""
    try:
        p = int(str(pp).rstrip("A"))
    except ValueError:
        return 50
    if p == 1:
        return 40       # rail death
    if 2 <= p <= 4:
        return 65
    if 5 <= p <= 15:
        return 90
    if 16 <= p <= 20:
        return 70
    return 30           # also-eligible (won't run unless scratch)

# ---- prior-rich features Nigel asked about ----
def f_florida_derby_bonus(pps):
    """Nigel's stated bias: FlaDerby winners get a bump."""
    for p in pps:
        if p["race_class"] == "Stk-FlaDerby" and p["finish_pos"] == "1":
            return 100
    return 50

def f_barn_pick(horse, trainer, jockey):
    """Cox triple: Velazquez ride on Further Ado is the barn-pick signal."""
    if trainer == "Brad Cox":
        if horse == "Further Ado" and "Velazquez" in jockey:
            return 90       # the tell
        return 60           # other Cox runners get a small discount
    return 60

# Weights — sum to 1.0
WEIGHTS = {
    "last_beyer":     0.18,
    "top3_beyer":     0.12,
    "pace_fit":       0.15,
    "class_preps":    0.12,
    "how_won":        0.07,
    "distance_fit":   0.10,
    "connections":    0.06,
    "equipment":      0.04,
    "post":           0.05,
    "florida_derby":  0.05,    # Nigel bias
    "barn_pick":      0.06,    # Cox-stable tell
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, sum(WEIGHTS.values())

# ----------------------------- DATA LOADING -----------------------------

def load():
    field = list(csv.DictReader(open(FIELD)))
    pps = list(csv.DictReader(open(PP)))
    by_horse = defaultdict(list)
    for p in pps:
        by_horse[p["horse"].strip()].append(p)
    # Merge live odds + scratches if file exists
    if LIVE_ODDS.exists():
        live = {row["horse"].strip(): row for row in csv.DictReader(open(LIVE_ODDS))}
        survivors = []
        for h in field:
            lo = live.get(h["horse"].strip())
            if lo and lo.get("scratched", "False").lower() == "true":
                continue   # drop scratched
            if lo:
                h["live_odds"] = lo.get("live_odds", "")
            survivors.append(h)
        field = survivors
    return field, by_horse

# ----------------------------- MAIN -----------------------------

def parse_ml(s):
    """'4-1' -> 4.0; 'N/A' -> None."""
    s = s.strip()
    if s in ("", "N/A"):
        return None
    if "-" in s:
        a, b = s.split("-")
        return float(a) / float(b)
    return float(s)

def implied_prob(decimal_odds):
    return 1.0 / (decimal_odds + 1.0)

def softmax(scores, temperature=0.07):
    """Convert scores in [0,100] to probabilities. Temperature controls spread."""
    exps = [math.exp(s * temperature) for s in scores]
    z = sum(exps)
    return [e / z for e in exps]

# Horses with declared first-time blinkers (per equipment notes at bottom of card)
FT_BLINKERS = {"Litmus Test", "Chief Wallabee"}

# Public-overbet factors. >1 means market prob will be inflated by name recognition,
# stable bias, owner cachet, etc. We scale market prob then renormalize, capturing
# "the live tote will be more skewed toward recognizable names than ML implies."
PUBLIC_OVERBET = {
    "Renegade":        1.20,    # ML fav + Repole + Pletcher + I.Ortiz + post 1
    "Litmus Test":     1.25,    # Baffert tax — biggest single effect
    "Further Ado":     1.15,    # Velazquez tax + Cox + Spendthrift
    "Chief Wallabee":  1.12,    # Wm Mott + name + FT-blinkers narrative
    "Commandment":     1.10,    # Cox + perfect form narrative
    "So Happy":        1.08,    # Mike Smith + cheerful name
    "Emerging Market": 1.05,    # Klaravich + Brown + Prat
    "Danon Bourbon":   1.05,    # Japan story horse
    "Wonder Dean":     1.05,    # Japan story horse (UAE Derby winner)
    "Corona de Oro":   1.03,    # Calumet silks
    "Robusta":         1.03,    # Calumet silks
}

def field_rank(values, higher_is_better=True):
    """Convert a list of values to percentile ranks in [0, 100]."""
    n = len(values)
    indexed = list(enumerate(values))
    indexed.sort(key=lambda x: x[1], reverse=higher_is_better)
    out = [0] * n
    for rank, (i, _) in enumerate(indexed):
        # rank 0 (best) -> 100, rank n-1 (worst) -> 0
        out[i] = 100 * (n - 1 - rank) / (n - 1) if n > 1 else 50
    return out

def compute_features(field, pps):
    """Build feature dict per horse."""
    rows = []
    for h in field:
        horse = h["horse"].strip().split(" (")[0]
        h_pps = pps.get(h["horse"], [])
        if not h_pps:
            for k, v in pps.items():
                if k.startswith(horse):
                    h_pps = v
                    break
        feats = {
            "last_beyer":    f_last_beyer(h_pps),
            "top3_beyer":    f_top3_beyer(h_pps),
            "pace_fit":      f_pace_fit(h_pps),
            "class_preps":   f_class_of_preps(h_pps),
            "how_won":       f_how_won(h_pps),
            "distance_fit":  f_distance_fit(h_pps, h.get("sire", "")),
            "connections":   f_connections(h["trainer"], h["jockey"]),
            "equipment":     f_equipment(horse, horse in FT_BLINKERS),
            "post":          f_post(h["pp"]),
            "florida_derby": f_florida_derby_bonus(h_pps),
            "barn_pick":     f_barn_pick(horse, h["trainer"], h["jockey"]),
        }
        for k, v in feats.items():
            if v is None:
                feats[k] = 50
        rows.append({
            "pp": h["pp"], "horse": h["horse"], "ml": h["ml_odds"],
            "live_odds": h.get("live_odds", ""),
            "feats": feats,
        })
    return rows

def score_cardinal(rows):
    for r in rows:
        r["score"] = sum(WEIGHTS[k] * r["feats"][k] for k in WEIGHTS)

def score_rank(rows):
    """Field-relative ranking variant. Each feature is rank-normalized within field."""
    feat_keys = list(WEIGHTS.keys())
    for k in feat_keys:
        vals = [r["feats"][k] for r in rows]
        ranks = field_rank(vals, higher_is_better=True)
        for r, rank_val in zip(rows, ranks):
            r.setdefault("ranks", {})[k] = rank_val
    for r in rows:
        r["score_rank"] = sum(WEIGHTS[k] * r["ranks"][k] for k in feat_keys)

def market_probs(rows, use_live=True):
    """
    Strip takeout from market odds.
    Prefer live odds when available (the price movement reveals public money).
    Fall back to ML if live not present, applying static public-overbet factors.
    """
    implied = []
    for r in rows:
        live = r.get("live_odds", "").strip() if use_live else ""
        if live and live not in ("", "N/A"):
            d = parse_ml(live)
            implied.append(implied_prob(d) if d else 0)
        else:
            d = parse_ml(r["ml"])
            ip = implied_prob(d) if d else 0
            # Only apply static overbet factors when we don't have live data
            horse = r["horse"].strip().split(" (")[0]
            ip *= PUBLIC_OVERBET.get(horse, 1.0)
            implied.append(ip)
    z = sum(implied)
    return [a / z if z else 0 for a in implied]

POST_ADJUST = {
    1:  0.60,    # rail death — 1 winner in 50 modern Derbies
    2:  0.90,    # rail-adjacent tax
    3:  0.90,
    4:  0.90,
    16: 0.90,    # wide-trip penalty starts
    17: 0.85,
    18: 0.85,
    19: 0.85,
    20: 0.85,
}
def post_multiplier(pp):
    try:
        n = int(str(pp).rstrip("A"))
    except ValueError:
        return 0.50
    if "A" in str(pp):
        return 0.50    # AE — won't run unless scratch
    return POST_ADJUST.get(n, 1.00)

def attach_probs(rows, score_key, mkt_probs, temp=0.075):
    """Softmax raw scores -> probs, apply post-position discount, renormalize."""
    scores = [r[score_key] for r in rows]
    probs = softmax(scores, temperature=temp)
    # Multiplicative post adjustment, then renormalize
    adj = [p * post_multiplier(r["pp"]) for r, p in zip(rows, probs)]
    z = sum(adj)
    probs = [a / z for a in adj] if z else probs
    for r, p, mp in zip(rows, probs, mkt_probs):
        r[f"{score_key}_prob"] = p
        r[f"{score_key}_odds"] = (1 - p) / p if p > 0 else float("inf")
        r[f"{score_key}_mkt"] = mp
        r[f"{score_key}_mkt_odds"] = (1 - mp) / mp if mp > 0 else float("inf")
        r[f"{score_key}_overlay"] = p / mp if mp > 0 else float("inf")
        r[f"{score_key}_bet"] = ("YES" if r[f"{score_key}_overlay"] >= 1.25
                                 and p >= 0.04 else "")

def print_table(rows, label, score_key):
    rows_sorted = sorted(rows, key=lambda r: r[f"{score_key}_prob"], reverse=True)
    print(f"\n{label}")
    print(f"{'PP':>3} {'Horse':<22} {'ML':>5} {'OurP':>6} {'OurOdds':>9} "
          f"{'MktP':>6} {'MktOdds':>9} {'Overlay':>7}  Bet")
    print("-" * 90)
    for r in rows_sorted:
        print(f"{r['pp']:>3} {r['horse'][:22]:<22} {r['ml']:>5} "
              f"{r[f'{score_key}_prob']*100:>5.1f}% "
              f"{r[f'{score_key}_odds']:>8.1f}-1 "
              f"{r[f'{score_key}_mkt']*100:>5.1f}% "
              f"{r[f'{score_key}_mkt_odds']:>8.1f}-1 "
              f"{r[f'{score_key}_overlay']:>6.2f}x  "
              f"{r[f'{score_key}_bet']}")

def main():
    field, pps = load()
    rows = compute_features(field, pps)
    score_cardinal(rows)
    score_rank(rows)
    mkt = market_probs(rows, use_live=True)
    attach_probs(rows, "score", mkt)
    attach_probs(rows, "score_rank", mkt)
    # Stash the displayed market odds string for the print table
    for r, m in zip(rows, mkt):
        r["mkt_display"] = r.get("live_odds") or r["ml"]

    # Display
    print_table(rows, "CARDINAL scoring (trip-adjusted Beyers, public-overbet on market)",
                "score")
    print_table(rows, "RANK-BASED scoring (field-relative, same market adjustment)",
                "score_rank")

    # Diff
    print("\nWhere the two methods disagree most (overlay shift):")
    diffs = sorted(rows, key=lambda r: abs(r["score_overlay"] - r["score_rank_overlay"]),
                   reverse=True)
    print(f"{'Horse':<22} {'CardOver':>9} {'RankOver':>9} {'Δ':>6}")
    for r in diffs[:8]:
        delta = r["score_rank_overlay"] - r["score_overlay"]
        print(f"{r['horse'][:22]:<22} {r['score_overlay']:>8.2f}x "
              f"{r['score_rank_overlay']:>8.2f}x {delta:>+6.2f}")

    # Bets
    print("\nCardinal overlays:")
    for r in sorted(rows, key=lambda r: r["score_prob"], reverse=True):
        if r["score_bet"] == "YES":
            print(f"  #{r['pp']:>3} {r['horse']:<22} fair "
                  f"{r['score_prob']*100:.1f}% vs mkt "
                  f"{r['score_mkt']*100:.1f}%  ({r['score_overlay']:.2f}x)")
    print("\nRank-based overlays:")
    for r in sorted(rows, key=lambda r: r["score_rank_prob"], reverse=True):
        if r["score_rank_bet"] == "YES":
            print(f"  #{r['pp']:>3} {r['horse']:<22} fair "
                  f"{r['score_rank_prob']*100:.1f}% vs mkt "
                  f"{r['score_rank_mkt']*100:.1f}%  ({r['score_rank_overlay']:.2f}x)")

    # Write CSVs
    cols = ["pp", "horse", "ml",
            "score", "score_prob", "score_odds", "score_mkt", "score_overlay", "score_bet",
            "score_rank", "score_rank_prob", "score_rank_odds", "score_rank_mkt",
            "score_rank_overlay", "score_rank_bet"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

if __name__ == "__main__":
    main()
