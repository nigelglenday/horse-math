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
OUT = ROOT / "data" / "parsed" / "overlays.csv"

# ----------------------------- FEATURE SCORERS -----------------------------
# Each scorer returns 0-100. Higher = better. None = unknown -> mean-impute later.

def f_last_beyer(pps):
    """Most recent Beyer figure (highest predictive single number)."""
    pps = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                 key=lambda p: p["pp_date"], reverse=True)
    if not pps:
        return None
    b = int(pps[0]["beyer"])
    # 110 -> 100, 70 -> 0, linear in [70, 110]
    return max(0, min(100, (b - 70) * 100 / 40))

def f_top3_beyer(pps):
    """Best of last 3 Beyers — filters one-off bounces."""
    pps_sorted = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                        key=lambda p: p["pp_date"], reverse=True)[:3]
    if not pps_sorted:
        return None
    b = max(int(p["beyer"]) for p in pps_sorted)
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

def main():
    field, pps = load()
    rows = []
    for h in field:
        horse = h["horse"].strip().split(" (")[0]   # strip "(JPN)" suffix for matching
        # Match PPs by horse name prefix
        h_pps = pps.get(h["horse"], [])
        if not h_pps:
            # Try without parenthetical suffix
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
        # Mean-impute None (Japan/UAE shippers with no Beyer)
        for k, v in feats.items():
            if v is None:
                feats[k] = 50  # neutral
        score = sum(WEIGHTS[k] * feats[k] for k in WEIGHTS)
        rows.append({
            "pp": h["pp"],
            "horse": h["horse"],
            "ml": h["ml_odds"],
            "score": score,
            **{f"f_{k}": round(v, 1) for k, v in feats.items()},
        })

    # Softmax scores -> probabilities
    scores = [r["score"] for r in rows]
    probs = softmax(scores, temperature=0.075)
    for r, p in zip(rows, probs):
        r["fair_prob"] = p
        r["fair_odds"] = (1 - p) / p if p > 0 else float("inf")

    # Strip ML takeout
    ml_implied = []
    for r in rows:
        d = parse_ml(r["ml"])
        ml_implied.append(implied_prob(d) if d else 0)
    z = sum(ml_implied)
    for r, ip in zip(rows, ml_implied):
        r["mkt_prob"] = ip / z if z else 0
        r["mkt_odds"] = (1 - r["mkt_prob"]) / r["mkt_prob"] if r["mkt_prob"] else float("inf")
        r["overlay"] = r["fair_prob"] / r["mkt_prob"] if r["mkt_prob"] else float("inf")
        r["bet"] = "YES" if r["overlay"] >= 1.25 and r["fair_prob"] >= 0.04 else ""

    rows.sort(key=lambda r: r["fair_prob"], reverse=True)

    # Write CSV
    cols = ["pp", "horse", "ml", "score", "fair_prob", "fair_odds",
            "mkt_prob", "mkt_odds", "overlay", "bet"] + [f"f_{k}" for k in WEIGHTS]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

    # Print summary
    print(f"\nDerby field — {len(rows)} horses, takeout-stripped & scored\n")
    print(f"{'PP':>3} {'Horse':<22} {'ML':>5} {'Score':>6} {'OurP':>6} {'OurOdds':>9} "
          f"{'MktP':>6} {'MktOdds':>9} {'Overlay':>7}  Bet")
    print("-" * 95)
    for r in rows:
        print(f"{r['pp']:>3} {r['horse'][:22]:<22} {r['ml']:>5} {r['score']:>6.1f} "
              f"{r['fair_prob']*100:>5.1f}% {r['fair_odds']:>8.1f}-1 "
              f"{r['mkt_prob']*100:>5.1f}% {r['mkt_odds']:>8.1f}-1 "
              f"{r['overlay']:>6.2f}x  {r['bet']}")
    print()
    bets = [r for r in rows if r["bet"] == "YES"]
    print(f"Suggested overlays ({len(bets)}):")
    for r in bets:
        edge = (r["fair_prob"] - r["mkt_prob"]) * 100
        print(f"  #{r['pp']} {r['horse']}  fair {r['fair_prob']*100:.1f}% vs mkt "
              f"{r['mkt_prob']*100:.1f}%  (+{edge:.1f}pp, {r['overlay']:.2f}x)")

if __name__ == "__main__":
    main()
