"""
Trifecta overlay analysis (Plackett-Luce).

Math:
  P(i 1st, j 2nd, k 3rd) = p_i × (p_j / (1 - p_i)) × (p_k / (1 - p_i - p_j))

Two paths:
  1. If `data/races/<slug>/trifecta_probables.txt` exists: compute overlay vs
     actual probable payouts (same pattern as exacta)
  2. Otherwise: synthesize market probability via Plackett-Luce on the
     takeout-stripped win pool. Estimate payout = (1 - takeout) / market_prob.
     Less precise — public bets exotics differently than win pool — but
     always available and a useful starting filter.

Run: python3 src/trifecta.py [--race 2026-kentucky-derby] [--top 20]
                              [--min-our-prob 0.0005]
"""
from __future__ import annotations
import argparse
import csv
import sys
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap

ROOT = Path(__file__).resolve().parent.parent

def plackett_luce_3(p_i, p_j, p_k):
    if p_i >= 1.0 or p_i + p_j >= 1.0:
        return 0.0
    return (p_i) * (p_j / (1 - p_i)) * (p_k / (1 - p_i - p_j))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--min-our-prob", type=float, default=0.0005,
                        help="Skip combos below this fair prob (lottery filter)")
    parser.add_argument("--prob-source", choices=["cardinal", "rank", "avg"],
                        default="cardinal")
    args = parser.parse_args()

    cfg, paths = handicap.load_config(args.race)
    takeout = cfg["race"].get("exotic_takeout", 0.22)
    net_return = 1 - takeout

    overlays_rows = list(csv.DictReader(open(paths["overlays_out"])))

    # Build {pp -> {horse, our_p, mkt_p}}
    horses = {}
    for r in overlays_rows:
        try:
            pp = int(str(r["pp"]).rstrip("A"))
        except ValueError:
            continue
        if args.prob_source == "cardinal":
            our_p = float(r["score_prob"])
        elif args.prob_source == "rank":
            our_p = float(r["score_rank_prob"])
        else:
            our_p = (float(r["score_prob"]) + float(r["score_rank_prob"])) / 2
        horses[pp] = {
            "horse": r["horse"],
            "our_p": our_p,
            "mkt_p": float(r["score_mkt"]),
        }

    pps = list(horses.keys())

    # Optional: load actual trifecta probables if file exists
    tri_path = paths["overlays_out"].parent / "trifecta_probables.txt"
    actual_probables = {}
    if tri_path.exists():
        with open(tri_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Expected format: "i-j-k payout" e.g., "19-1-22 5625.39"
                parts = line.split()
                if len(parts) < 2:
                    continue
                try:
                    combo = tuple(int(x) for x in parts[0].split("-"))
                    payout = float(parts[1])
                    actual_probables[combo] = payout
                except ValueError:
                    pass

    # Compute fair + market for every ordered (i,j,k)
    rows = []
    for i, j, k in permutations(pps, 3):
        h_i, h_j, h_k = horses[i], horses[j], horses[k]
        our_p = plackett_luce_3(h_i["our_p"], h_j["our_p"], h_k["our_p"])
        if our_p < args.min_our_prob:
            continue
        mkt_p_synth = plackett_luce_3(h_i["mkt_p"], h_j["mkt_p"], h_k["mkt_p"])
        # Payout: actual if available, else synthesized
        if (i, j, k) in actual_probables:
            payout = actual_probables[(i, j, k)]
            mkt_p_actual = net_return / payout if payout > 0 else 0
            payout_source = "actual"
        else:
            payout = net_return / mkt_p_synth if mkt_p_synth > 0 else 0
            mkt_p_actual = mkt_p_synth
            payout_source = "synth"
        overlay = our_p / mkt_p_actual if mkt_p_actual > 0 else 0
        ev = our_p * payout - 1
        rows.append({
            "winner_pp": i, "placer_pp": j, "show_pp": k,
            "winner": h_i["horse"], "placer": h_j["horse"], "show": h_k["horse"],
            "our_prob_pct": our_p * 100,
            "mkt_prob_pct": mkt_p_actual * 100,
            "payout_per_1": payout,
            "payout_source": payout_source,
            "overlay": overlay,
            "ev_per_1": ev,
        })

    # Sort by EV descending
    rows.sort(key=lambda r: r["ev_per_1"], reverse=True)
    out_path = paths["overlays_out"].parent / "trifecta_overlays.csv"
    cols = ["winner_pp", "placer_pp", "show_pp", "winner", "placer", "show",
            "our_prob_pct", "mkt_prob_pct", "payout_per_1", "payout_source",
            "overlay", "ev_per_1"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: round(v, 4) if isinstance(v, float) else v
                        for k, v in r.items()})

    print(f"\n=== {cfg['race']['name']} — Trifecta overlays ===")
    if actual_probables:
        print(f"Using actual probables for {len(actual_probables)} combos, synth for rest.")
    else:
        print("No trifecta_probables.txt found — using synthesized payouts (Plackett-Luce on win pool).")
        print("Reality check: payouts are estimates, not actual board prices.")
    print(f"\nTop {args.top} by EV per $1 bet:\n")
    print(f"{'Combo':<40} {'OurP%':>7} {'MktP%':>7} {'PayEst$':>9} {'Ovr':>5} {'EV/$1':>7} {'Src':>5}")
    print("-" * 95)
    for r in rows[:args.top]:
        combo = (f"{r['winner_pp']:>2}-{r['placer_pp']:>2}-{r['show_pp']:>2} "
                 f"{r['winner'][:8]:<9}>{r['placer'][:6]:<7}>{r['show'][:6]:<7}")
        print(f"{combo:<40} {r['our_prob_pct']:>6.3f}% {r['mkt_prob_pct']:>6.3f}% "
              f"{r['payout_per_1']:>8.2f} {r['overlay']:>4.2f}x "
              f"{r['ev_per_1']:>+6.2f} {r['payout_source']:>5}")

    # Also: top combos by raw "key" structures the user might bet
    # For each pp with our_p >= 4%, show the best wheel underneath
    keys_of_interest = [pp for pp, h in horses.items() if h["our_p"] >= 0.04]
    if keys_of_interest:
        print(f"\n\nKey-wheel suggestions (top combos with each high-prob horse on top):")
        for top_pp in sorted(keys_of_interest,
                             key=lambda pp: horses[pp]["our_p"], reverse=True):
            sub = [r for r in rows if r["winner_pp"] == top_pp][:5]
            if not sub:
                continue
            print(f"\n  Key #{top_pp} {horses[top_pp]['horse']} on top:")
            for r in sub:
                print(f"    > {r['placer_pp']:>2} {r['placer'][:14]:<15}/ "
                      f"{r['show_pp']:>2} {r['show'][:14]:<15}  "
                      f"our {r['our_prob_pct']:>5.3f}%  "
                      f"pay~${r['payout_per_1']:>7.2f}  "
                      f"EV {r['ev_per_1']:>+6.2f}")

    print(f"\nWrote trifecta overlays to {out_path.relative_to(ROOT)}")
    print(f"To use actual probable payouts when available, create "
          f"{tri_path.relative_to(ROOT)} with one combo per line: '19-1-22 5625.39'")

if __name__ == "__main__":
    main()
