"""
Weight-sensitivity scan. Perturb each feature weight by ±20% (Gaussian-ish),
re-score, see which overlays are robust vs fragile.

Run: python3 src/sensitivity.py [--race 2026-kentucky-derby]
"""
from __future__ import annotations
import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap

N_TRIALS = 200
PERTURB_PCT = 0.20

def perturb(weights):
    new = {k: max(0.005, w * random.uniform(1 - PERTURB_PCT, 1 + PERTURB_PCT))
           for k, w in weights.items()}
    z = sum(new.values())
    return {k: v / z for k, v in new.items()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    args = parser.parse_args()

    random.seed(42)
    cfg, paths = handicap.load_config(args.race)
    field, pps = handicap.load_data(paths)
    rows = handicap.compute_features(field, pps, cfg)
    public_overbet = cfg.get("public_overbet", {})
    mkt = handicap.market_probs(rows, public_overbet, use_live=True)
    base_w = cfg["weights"]
    temp = cfg["scoring"].get("temperature", 0.075)
    overlay_threshold = cfg["scoring"].get("overlay_threshold", 1.25)
    fair_prob_threshold = cfg["scoring"].get("fair_prob_threshold", 0.04)
    post_cfg = cfg["post_multiplier"]

    horses = [r["horse"] for r in rows]
    posts = [r["pp"] for r in rows]
    overlay_samples = {h: [] for h in horses}
    bet_count = {h: 0 for h in horses}

    for _ in range(N_TRIALS):
        w = perturb(base_w)
        for r in rows:
            r["score_t"] = sum(w[k] * r["feats"][k] for k in w)
        scores = [r["score_t"] for r in rows]
        probs = handicap.softmax(scores, temperature=temp)
        adj = [p * handicap.post_multiplier(r["pp"], post_cfg) for r, p in zip(rows, probs)]
        z = sum(adj)
        probs = [a / z for a in adj] if z else probs
        for r, p, mp in zip(rows, probs, mkt):
            overlay = p / mp if mp > 0 else float("inf")
            is_bet = overlay >= overlay_threshold and p >= fair_prob_threshold
            overlay_samples[r["horse"]].append(overlay)
            if is_bet:
                bet_count[r["horse"]] += 1

    print(f"\n{cfg['race']['name']} — Sensitivity scan")
    print(f"{N_TRIALS} trials · weights perturbed ±{int(PERTURB_PCT*100)}% · post mult applied")
    print(f"\n{'PP':>3} {'Horse':<22} {'Bet %':>7} {'MeanOvr':>9} {'MinOvr':>9} {'MaxOvr':>9}  Robustness")
    print("-" * 95)

    pp_lookup = {h: p for h, p in zip(horses, posts)}
    rows_summary = []
    for h, samples in overlay_samples.items():
        rows_summary.append({
            "horse": h, "pp": pp_lookup[h],
            "bet_pct": 100 * bet_count[h] / N_TRIALS,
            "mean": sum(samples) / len(samples),
            "min": min(samples), "max": max(samples),
        })
    rows_summary.sort(key=lambda r: r["bet_pct"], reverse=True)
    for r in rows_summary:
        if r["bet_pct"] > 0 or r["mean"] > 0.8:
            tag = ("ROCK SOLID" if r["bet_pct"] >= 95
                   else "Robust"  if r["bet_pct"] >= 75
                   else "Marginal" if r["bet_pct"] >= 40
                   else "Fragile"  if r["bet_pct"] > 0
                   else "")
            print(f"{r['pp']:>3} {r['horse'][:22]:<22} {r['bet_pct']:>6.1f}% "
                  f"{r['mean']:>8.2f}x {r['min']:>8.2f}x {r['max']:>8.2f}x  {tag}")

if __name__ == "__main__":
    main()
