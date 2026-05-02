"""
Exacta overlay analysis.

For each (winner, placer) combo:
  market_P  = (1 - takeout) / probable_payout      [takeout ~22% on CD exotics]
  fair_P    = p_i * p_j / (1 - p_i)                [Harville model from our win probs]
  overlay   = fair_P / market_P

Bet when overlay >= threshold AND fair_P high enough not to be lottery.

Run: python3 src/exacta.py
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBABLES = ROOT / "data" / "parsed" / "exacta_probables.txt"
OVERLAYS = ROOT / "data" / "parsed" / "overlays.csv"
OUT = ROOT / "data" / "parsed" / "exacta_overlays.csv"

EXOTIC_TAKEOUT = 0.22
NET_RETURN = 1 - EXOTIC_TAKEOUT     # 0.78

def load_probables():
    """Parse the 24x24 probables grid into dict: (winner, placer) -> payout."""
    probables = {}
    header = None
    with open(PROBABLES) as f:
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

def load_win_probs():
    """Read each horse's PP -> (horse name, cardinal fair prob, rank fair prob)."""
    out = {}
    for r in csv.DictReader(open(OVERLAYS)):
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
    """P(i 1st AND j 2nd) = p_i * p_j / (1 - p_i)."""
    if p_i >= 1.0:
        return 0.0
    return p_i * p_j / (1 - p_i)

def main():
    probables = load_probables()
    horses = load_win_probs()

    rows = []
    for (i, j), payout in probables.items():
        if i not in horses or j not in horses:
            continue
        p_i_card = horses[i]["p_card"]
        p_j_card = horses[j]["p_card"]
        p_i_rank = horses[i]["p_rank"]
        p_j_rank = horses[j]["p_rank"]
        market_p = NET_RETURN / payout
        fair_card = harville(p_i_card, p_j_card)
        fair_rank = harville(p_i_rank, p_j_rank)
        # Average the two methods for a single overlay number
        fair_avg = (fair_card + fair_rank) / 2
        rows.append({
            "winner_pp": i,
            "winner": horses[i]["horse"],
            "placer_pp": j,
            "placer": horses[j]["horse"],
            "payout": payout,
            "market_prob_pct": market_p * 100,
            "fair_card_pct": fair_card * 100,
            "fair_rank_pct": fair_rank * 100,
            "fair_avg_pct": fair_avg * 100,
            "overlay_card": fair_card / market_p if market_p else 0,
            "overlay_rank": fair_rank / market_p if market_p else 0,
            "overlay_avg": fair_avg / market_p if market_p else 0,
            # Expected return per $1 bet = fair_prob * payout - 1
            "ev_per_1": fair_avg * payout - 1,
        })

    # Sort by overlay_avg descending, but only keep those with fair_avg >= 0.5%
    # (anything less is lottery territory)
    bets = [r for r in rows if r["fair_avg_pct"] >= 0.5]
    bets.sort(key=lambda r: r["overlay_avg"], reverse=True)

    # Write full CSV
    cols = ["winner_pp", "winner", "placer_pp", "placer", "payout",
            "market_prob_pct", "fair_card_pct", "fair_rank_pct", "fair_avg_pct",
            "overlay_card", "overlay_rank", "overlay_avg", "ev_per_1"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["overlay_avg"], reverse=True):
            w.writerow({k: round(v, 3) if isinstance(v, float) else v
                        for k, v in r.items()})

    # Print summary
    print(f"\nExacta overlays — top 25 by avg overlay (cardinal+rank averaged)")
    print(f"Pool: $10.7M · Takeout: {EXOTIC_TAKEOUT:.0%} · Field of 19 (5 scratched)\n")
    print(f"{'Combo':<30} {'Pay$1':>8} {'MktP%':>7} {'FairP%':>7} "
          f"{'OvCard':>7} {'OvRank':>7} {'OvAvg':>7} {'EV/$1':>7}")
    print("-" * 95)
    for r in bets[:25]:
        combo = f"{r['winner_pp']:>2} {r['winner'][:11]:<12} > {r['placer_pp']:>2} {r['placer'][:8]:<10}"
        print(f"{combo:<30} {r['payout']:>8.2f} {r['market_prob_pct']:>6.2f}% "
              f"{r['fair_avg_pct']:>6.2f}% "
              f"{r['overlay_card']:>6.2f}x {r['overlay_rank']:>6.2f}x "
              f"{r['overlay_avg']:>6.2f}x {r['ev_per_1']:>+6.2f}")

    # Highlight: combos with our 4 overlay horses on top, plus best placers
    print("\n\nKey-win structures (our overlay horses on top):")
    OUR_OVERLAYS = [1, 4, 18, 19]   # Renegade, Litmus Test, Further Ado, Golden Tempo
    for top in OUR_OVERLAYS:
        if top not in horses:
            continue
        sub = [r for r in bets if r["winner_pp"] == top]
        sub.sort(key=lambda r: r["overlay_avg"], reverse=True)
        print(f"\n  #{top} {horses[top]['horse']} on top — best exactas:")
        for r in sub[:8]:
            print(f"    > #{r['placer_pp']:>2} {r['placer'][:18]:<20} "
                  f"pays ${r['payout']:>7.2f}  "
                  f"market {r['market_prob_pct']:>5.2f}%  "
                  f"our {r['fair_avg_pct']:>5.2f}%  "
                  f"overlay {r['overlay_avg']:>5.2f}x  "
                  f"EV/$1 {r['ev_per_1']:>+6.2f}")

    # Top-5 EV combos overall
    print("\n\nTop 10 EXPECTED VALUE per $1 bet (positive EV is the bar):")
    by_ev = sorted(bets, key=lambda r: r["ev_per_1"], reverse=True)[:10]
    for r in by_ev:
        combo = f"{r['winner_pp']:>2} {r['winner'][:14]:<15} > {r['placer_pp']:>2} {r['placer'][:14]:<15}"
        print(f"  {combo}  pays ${r['payout']:>7.2f}  EV/$1 {r['ev_per_1']:>+6.2f}  ovr {r['overlay_avg']:.2f}x")

if __name__ == "__main__":
    main()
