"""
Generalized horse-handicap scoring engine.

Method:
  - Score each horse on weighted features (config-driven)
  - Softmax -> our win probability
  - Apply post-position multiplier, renormalize
  - Strip takeout from market odds -> market's true probability
  - Overlay = our_prob / market_prob

Run: python3 src/handicap.py [--race 2026-kentucky-derby]
"""
from __future__ import annotations
import argparse
import csv
import math
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ----------------------------- CONFIG LOADING -----------------------------

def load_config(race_slug):
    """Load the race-specific TOML config and return paths + config dict."""
    base = ROOT / "data" / "races" / race_slug
    config_path = base / "config.toml"
    if not config_path.exists():
        sys.exit(f"No config at {config_path}")
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    paths = {
        "field":            base / "field.csv",
        "pp":               base / "past_performances.csv",
        "live_odds":        base / "live_odds.csv",
        "exacta_probables": base / "exacta_probables.txt",
        "overlays_out":     base / "overlays.csv",
    }
    return cfg, paths

# ----------------------------- FEATURE SCORERS -----------------------------
# Each scorer returns 0-100. Higher = better. None = unknown -> mean-impute later.

def trip_adj_from_comment(comment):
    """Derive a trip adjustment from the chart-caller's comment."""
    if not comment:
        return 0
    c = comment.lower()
    adj = 0
    for m in re.finditer(r"(\d)\s*[wp](?:ide)?\b", c):
        try:
            n = int(m.group(1))
            if n >= 4:
                adj += (n - 3)
        except ValueError:
            pass
    adj = min(adj, 4)
    for kw in ("wsteadied", "steadied", "checked", "bumped", "bobbled",
              "slip brk", "slipped", "wbpd", "shuffled", "squeezed", "wsqzd"):
        if kw in c:
            adj += 2
            break
    for kw in ("ridden out", "rddn out", "handily", "in hand"):
        if kw in c:
            adj += 2
            break
    if "dq" in c:
        adj += 2
    for kw in ("ins,", " ins ", "rail", "saved ground"):
        if kw in c:
            adj -= 1
            break
    for kw in ("yielded", "weakened", "folded", "no match", "outgamed", "no bid", "weaknd"):
        if kw in c:
            adj -= 1
            break
    return max(-3, min(5, adj))

def adjusted_beyer(pp):
    if pp["beyer"] in ("N/A", ""):
        return None
    return int(pp["beyer"]) + trip_adj_from_comment(pp.get("comment", ""))

def f_last_beyer(pps):
    pps = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                 key=lambda p: p["pp_date"], reverse=True)
    if not pps:
        return None
    b = adjusted_beyer(pps[0])
    return max(0, min(100, (b - 70) * 100 / 40))

def f_top3_beyer(pps):
    pps_sorted = sorted([p for p in pps if p["beyer"] not in ("N/A", "")],
                        key=lambda p: p["pp_date"], reverse=True)[:3]
    if not pps_sorted:
        return None
    b = max(adjusted_beyer(p) for p in pps_sorted)
    return max(0, min(100, (b - 70) * 100 / 40))

def f_pace_fit(pps, meltdown_likely):
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
        rel = ec / fs
        if rel <= 0.25:
            style_scores.append("E")
        elif rel <= 0.5:
            style_scores.append("EP")
        elif rel <= 0.7:
            style_scores.append("P")
        else:
            style_scores.append("S")
    if not style_scores:
        return 50
    mode = max(set(style_scores), key=style_scores.count)
    if meltdown_likely:
        return {"E": 30, "EP": 50, "P": 75, "S": 90}[mode]
    return {"E": 80, "EP": 75, "P": 70, "S": 55}[mode]

def f_class_of_preps(pps, prep_scores, default):
    best = 0
    for p in pps:
        if p["finish_pos"] not in ("1", "2"):
            continue
        cls = p["race_class"]
        score = prep_scores.get(cls, default)
        if p["finish_pos"] != "1":
            score = score * 0.65
        try:
            d = float(p["dist_f"])
            if d < 8.0:
                score *= 0.7
        except ValueError:
            pass
        best = max(best, score)
    return min(100, best)

def f_how_won(pps):
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
        s = 40 + min(40, margin * 8)
        comment = w.get("comment", "").lower()
        if any(k in comment for k in ("drove clear", "drew off", "kicked clear",
                                      "ridden out", "drwclr", "drove past")):
            s += 15
        if any(k in comment for k in ("driving", "all out", "gamely", "nailed", "missed")):
            s += 5
        score = max(score, s)
    return min(100, score)

def f_distance_fit(pps, sire, sire_bias):
    score = 30
    long_starts = [p for p in pps if float(p.get("dist_f") or 0) >= 9.0]
    if long_starts:
        beyers = [int(p["beyer"]) for p in long_starts if p["beyer"] not in ("N/A", "")]
        if beyers:
            top = max(beyers)
            score = max(0, min(100, (top - 70) * 100 / 40))
    stamina = sire_bias.get("stamina", {})
    speed = sire_bias.get("speed", {})
    if sire in stamina.get("sires", []):
        score += stamina.get("bonus", 0)
    elif sire in speed.get("sires", []):
        score -= speed.get("penalty", 0)
    return max(0, min(100, score))

def f_connections(trainer, jockey, trainer_scores, t_default, jockey_scores, j_default):
    t = trainer_scores.get(trainer, t_default)
    j = jockey_scores.get(jockey, j_default)
    return 0.5 * t + 0.5 * j

def f_equipment(horse, ft_blinkers):
    if horse in ft_blinkers:
        return 80
    return 50

def f_post(pp):
    """Post position score (used in feature scoring; multiplier applied separately)."""
    try:
        p = int(str(pp).rstrip("A"))
    except ValueError:
        return 50
    if p == 1:
        return 40
    if 2 <= p <= 4:
        return 65
    if 5 <= p <= 15:
        return 90
    if 16 <= p <= 20:
        return 70
    return 30

def f_preferred_prep(pps, race_class, winner_score, default_score):
    for p in pps:
        if p["race_class"] == race_class and p["finish_pos"] == "1":
            return winner_score
    return default_score

def f_barn_pick(horse, trainer, jockey, rules, default_score):
    for rule in rules:
        if rule.get("trainer") and trainer != rule["trainer"]:
            continue
        if rule.get("horse") and horse != rule["horse"]:
            continue
        if rule.get("jockey_contains") and rule["jockey_contains"] not in jockey:
            continue
        return rule.get("match_score", default_score)
    # If trainer matches some rule but horse/jockey didn't match → use trainer_other
    for rule in rules:
        if rule.get("trainer") == trainer:
            return rule.get("trainer_other_score", default_score)
    return default_score

# ----------------------------- POST MULTIPLIER -----------------------------

def post_multiplier(pp, post_cfg, has_live_odds=False):
    """
    Post-position multiplier. AE-flagged horses default to a penalty BUT if they
    have live odds (meaning they activated to fill the field after a scratch),
    treat them as regular starters. This was a bug exposed by the 2026 Derby —
    Ocelli (#22A) ran 3rd at 70-1 after his AE activated, but the model
    suppressed his probability. Live-odds presence is the activation signal.
    """
    overrides = post_cfg.get("overrides", {})
    default = post_cfg.get("default", 1.0)
    ae_default = post_cfg.get("ae_default", 0.5)
    s = str(pp)
    is_ae = "A" in s
    if is_ae and not has_live_odds:
        return ae_default
    try:
        n = int(s.rstrip("A"))
    except ValueError:
        return default
    return overrides.get(str(n), default)

# ----------------------------- DATA LOADING -----------------------------

def load_data(paths):
    field = list(csv.DictReader(open(paths["field"])))
    pps_raw = list(csv.DictReader(open(paths["pp"])))
    by_horse = defaultdict(list)
    for p in pps_raw:
        by_horse[p["horse"].strip()].append(p)
    if paths["live_odds"].exists():
        live = {row["horse"].strip(): row for row in csv.DictReader(open(paths["live_odds"]))}
        survivors = []
        for h in field:
            lo = live.get(h["horse"].strip())
            if lo and lo.get("scratched", "False").lower() == "true":
                continue
            if lo:
                h["live_odds"] = lo.get("live_odds", "")
            survivors.append(h)
        field = survivors
    return field, by_horse

# ----------------------------- SCORING / SOFTMAX -----------------------------

def parse_odds(s):
    s = s.strip()
    if s in ("", "N/A"):
        return None
    if "-" in s:
        a, b = s.split("-")
        return float(a) / float(b)
    return float(s)

def implied_prob(decimal_odds):
    return 1.0 / (decimal_odds + 1.0)

def softmax(scores, temperature):
    exps = [math.exp(s * temperature) for s in scores]
    z = sum(exps)
    return [e / z for e in exps]

def field_rank(values, higher_is_better=True):
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=higher_is_better)
    out = [0] * n
    for rank, (i, _) in enumerate(indexed):
        out[i] = 100 * (n - 1 - rank) / (n - 1) if n > 1 else 50
    return out

def compute_features(field, pps, cfg):
    rows = []
    ft_blinkers = set(cfg.get("equipment", {}).get("ft_blinkers", []))
    prep_scores = cfg["prep_class_score"].get("scores", {})
    prep_default = cfg["prep_class_score"].get("default", 35)
    sire_bias = cfg.get("sire_bias", {})
    trainer_scores = cfg.get("trainer_score", {}).get("scores", {})
    t_default = cfg.get("trainer_score", {}).get("default", 50)
    jockey_scores = cfg.get("jockey_score", {}).get("scores", {})
    j_default = cfg.get("jockey_score", {}).get("default", 55)
    pref = cfg["preferred_prep"]
    barn = cfg["barn_pick"]
    meltdown = cfg["pace"].get("meltdown_likely", False)

    for h in field:
        horse = h["horse"].strip().split(" (")[0]
        h_pps = pps.get(h["horse"], [])
        if not h_pps:
            for k, v in pps.items():
                if k.startswith(horse):
                    h_pps = v
                    break
        feats = {
            "last_beyer":     f_last_beyer(h_pps),
            "top3_beyer":     f_top3_beyer(h_pps),
            "pace_fit":       f_pace_fit(h_pps, meltdown),
            "class_preps":    f_class_of_preps(h_pps, prep_scores, prep_default),
            "how_won":        f_how_won(h_pps),
            "distance_fit":   f_distance_fit(h_pps, h.get("sire", ""), sire_bias),
            "connections":    f_connections(h["trainer"], h["jockey"],
                                            trainer_scores, t_default,
                                            jockey_scores, j_default),
            "equipment":      f_equipment(horse, ft_blinkers),
            "post":           f_post(h["pp"]),
            "preferred_prep": f_preferred_prep(h_pps, pref["race_class"],
                                               pref["winner_score"], pref["default_score"]),
            "barn_pick":      f_barn_pick(horse, h["trainer"], h["jockey"],
                                          barn.get("rules", []),
                                          barn.get("default_score", 60)),
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

def score_cardinal(rows, weights):
    for r in rows:
        r["score"] = sum(weights[k] * r["feats"][k] for k in weights)

def score_rank(rows, weights):
    feat_keys = list(weights.keys())
    for k in feat_keys:
        vals = [r["feats"][k] for r in rows]
        ranks = field_rank(vals, higher_is_better=True)
        for r, rank_val in zip(rows, ranks):
            r.setdefault("ranks", {})[k] = rank_val
    for r in rows:
        r["score_rank"] = sum(weights[k] * r["ranks"][k] for k in feat_keys)

def market_probs(rows, public_overbet, use_live=True):
    implied = []
    for r in rows:
        live = r.get("live_odds", "").strip() if use_live else ""
        if live and live not in ("", "N/A"):
            d = parse_odds(live)
            implied.append(implied_prob(d) if d else 0)
        else:
            d = parse_odds(r["ml"])
            ip = implied_prob(d) if d else 0
            horse = r["horse"].strip().split(" (")[0]
            ip *= public_overbet.get(horse, 1.0)
            implied.append(ip)
    z = sum(implied)
    return [a / z if z else 0 for a in implied]

def attach_probs(rows, score_key, mkt_probs, post_cfg, scoring_cfg):
    temp = scoring_cfg.get("temperature", 0.075)
    overlay_threshold = scoring_cfg.get("overlay_threshold", 1.25)
    fair_prob_threshold = scoring_cfg.get("fair_prob_threshold", 0.04)
    scores = [r[score_key] for r in rows]
    probs = softmax(scores, temperature=temp)
    # AE bug fix: live odds presence means horse activated to fill scratched slot —
    # treat as regular starter, drop the AE penalty
    adj = [p * post_multiplier(r["pp"], post_cfg,
                               has_live_odds=bool(r.get("live_odds", "").strip()))
           for r, p in zip(rows, probs)]
    z = sum(adj)
    probs = [a / z for a in adj] if z else probs
    for r, p, mp in zip(rows, probs, mkt_probs):
        r[f"{score_key}_prob"] = p
        r[f"{score_key}_odds"] = (1 - p) / p if p > 0 else float("inf")
        r[f"{score_key}_mkt"] = mp
        r[f"{score_key}_mkt_odds"] = (1 - mp) / mp if mp > 0 else float("inf")
        r[f"{score_key}_overlay"] = p / mp if mp > 0 else float("inf")
        r[f"{score_key}_bet"] = ("YES" if r[f"{score_key}_overlay"] >= overlay_threshold
                                 and p >= fair_prob_threshold else "")

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
    parser = argparse.ArgumentParser(description="Run handicap on a race.")
    parser.add_argument("--race", default="2026-kentucky-derby",
                        help="Race slug (subdirectory under data/races/)")
    args = parser.parse_args()

    cfg, paths = load_config(args.race)
    print(f"\n=== {cfg['race']['name']} — {cfg['race']['date']} ===")
    print(f"Track: {cfg['race']['track']} · Distance: {cfg['race']['distance_furlongs']}F · "
          f"Surface: {cfg['race']['surface']}")

    field, pps = load_data(paths)
    rows = compute_features(field, pps, cfg)

    weights = cfg["weights"]
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        print(f"WARNING: weights sum to {weight_sum:.3f}, not 1.0")

    score_cardinal(rows, weights)
    score_rank(rows, weights)
    public_overbet = cfg.get("public_overbet", {})
    mkt = market_probs(rows, public_overbet, use_live=True)
    attach_probs(rows, "score", mkt, cfg["post_multiplier"], cfg["scoring"])
    attach_probs(rows, "score_rank", mkt, cfg["post_multiplier"], cfg["scoring"])

    print_table(rows, "CARDINAL scoring (trip-adjusted Beyers, post-1 mult, live odds)", "score")
    print_table(rows, "RANK-BASED scoring (field-relative, same market adjustment)", "score_rank")

    print("\nWhere the two methods disagree most (overlay shift):")
    diffs = sorted(rows, key=lambda r: abs(r["score_overlay"] - r["score_rank_overlay"]),
                   reverse=True)
    print(f"{'Horse':<22} {'CardOver':>9} {'RankOver':>9} {'Δ':>6}")
    for r in diffs[:8]:
        delta = r["score_rank_overlay"] - r["score_overlay"]
        print(f"{r['horse'][:22]:<22} {r['score_overlay']:>8.2f}x "
              f"{r['score_rank_overlay']:>8.2f}x {delta:>+6.2f}")

    print("\nCardinal overlays:")
    for r in sorted(rows, key=lambda r: r["score_prob"], reverse=True):
        if r["score_bet"] == "YES":
            print(f"  #{r['pp']:>3} {r['horse']:<22} fair {r['score_prob']*100:.1f}% vs mkt "
                  f"{r['score_mkt']*100:.1f}%  ({r['score_overlay']:.2f}x)")
    print("\nRank-based overlays:")
    for r in sorted(rows, key=lambda r: r["score_rank_prob"], reverse=True):
        if r["score_rank_bet"] == "YES":
            print(f"  #{r['pp']:>3} {r['horse']:<22} fair {r['score_rank_prob']*100:.1f}% vs mkt "
                  f"{r['score_rank_mkt']*100:.1f}%  ({r['score_rank_overlay']:.2f}x)")

    cols = ["pp", "horse", "ml",
            "score", "score_prob", "score_odds", "score_mkt", "score_overlay", "score_bet",
            "score_rank", "score_rank_prob", "score_rank_odds", "score_rank_mkt",
            "score_rank_overlay", "score_rank_bet"]
    with open(paths["overlays_out"], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"\nWrote overlays to {paths['overlays_out'].relative_to(ROOT)}")

if __name__ == "__main__":
    main()
