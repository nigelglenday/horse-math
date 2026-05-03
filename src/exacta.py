"""
Exacta overlay analysis (Harville model).

For each (winner, placer) combo:
  market_P  = (1 - takeout) / probable_payout
  fair_P    = p_i * p_j / (1 - p_i)
  overlay   = fair_P / market_P
  EV per $1 = fair_P * payout - 1

Run: python3 src/exacta.py [--race 2026-kentucky-derby]
"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap

ROOT = Path(__file__).resolve().parent.parent

def load_probables(path):
    probables = {}
    header = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cells = [c.strip() for c in line.split(",")]
            if header is None:
                header = [int(c) for c in cells[1:]]
                continue
            try:
                winner = int(cells[0])
            except ValueError:
                continue
            for placer, val in zip(header, cells[1:]):
                if val in ("-", "SC", ""):
                    continue
                try:
                    probables[(winner, placer)] = float(val)
                except ValueError:
                    pass
    return probables

def load_win_probs(overlays_path):
    out = {}
    for r in csv.DictReader(open(overlays_path)):
        try:
            pp = int(str(r["pp"]).rstrip("A"))
        except ValueError:
            continue
        out[pp] = {
            "horse": r["horse"],
            "p_card": float(r["score_prob"]),
            "p_rank": float(r["score_rank_prob"]),
        }
    return out

def harville(p_i, p_j):
    if p_i >= 1.0:
        return 0.0
    return p_i * p_j / (1 - p_i)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    args = parser.parse_args()

    cfg, paths = handicap.load_config(args.race)
    takeout = cfg["race"].get("exotic_takeout", 0.22)
    net_return = 1 - takeout

    probables = load_probables(paths["exacta_probables"])
    horses = load_win_probs(paths["overlays_out"])

    rows = []
    for (i, j), payout in probables.items():
        if i not in horses or j not in horses:
            continue
        p_i_card, p_j_card = horses[i]["p_card"], horses[j]["p_card"]
        p_i_rank, p_j_rank = horses[i]["p_rank"], horses[j]["p_rank"]
        market_p = net_return / payout
        fair_card = harville(p_i_card, p_j_card)
        fair_rank = harville(p_i_rank, p_j_rank)
        fair_avg = (fair_card + fair_rank) / 2
        rows.append({
            "winner_pp": i, "winner": horses[i]["horse"],
            "placer_pp": j, "placer": horses[j]["horse"],
            "payout": payout,
            "market_prob_pct": market_p * 100,
            "fair_card_pct": fair_card * 100,
            "fair_rank_pct": fair_rank * 100,
            "fair_avg_pct": fair_avg * 100,
            "overlay_card": fair_card / market_p if market_p else 0,
            "overlay_rank": fair_rank / market_p if market_p else 0,
            "overlay_avg":  fair_avg  / market_p if market_p else 0,
            "ev_per_1":     fair_avg * payout - 1,
        })

    bets = [r for r in rows if r["fair_avg_pct"] >= 0.5]
    bets.sort(key=lambda r: r["overlay_avg"], reverse=True)

    out_path = paths["overlays_out"].parent / "exacta_overlays.csv"
    cols = ["winner_pp", "winner", "placer_pp", "placer", "payout",
            "market_prob_pct", "fair_card_pct", "fair_rank_pct", "fair_avg_pct",
            "overlay_card", "overlay_rank", "overlay_avg", "ev_per_1"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["overlay_avg"], reverse=True):
            w.writerow({k: round(v, 3) if isinstance(v, float) else v
                        for k, v in r.items()})

    print(f"\n{cfg['race']['name']} — Exacta overlays (top 25 by avg overlay)")
    print(f"Takeout: {takeout:.0%}\n")
    print(f"{'Combo':<32} {'Pay$1':>8} {'MktP%':>7} {'FairP%':>7} "
          f"{'OvCard':>7} {'OvRank':>7} {'OvAvg':>7} {'EV/$1':>7}")
    print("-" * 95)
    for r in bets[:25]:
        combo = f"{r['winner_pp']:>2} {r['winner'][:11]:<12} > {r['placer_pp']:>2} {r['placer'][:8]:<10}"
        print(f"{combo:<32} {r['payout']:>8.2f} {r['market_prob_pct']:>6.2f}% "
              f"{r['fair_avg_pct']:>6.2f}% "
              f"{r['overlay_card']:>6.2f}x {r['overlay_rank']:>6.2f}x "
              f"{r['overlay_avg']:>6.2f}x {r['ev_per_1']:>+6.2f}")

    print(f"\nWrote exacta overlays to {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
