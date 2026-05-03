"""
Edge-first portfolio construction (fractional Kelly).

For every candidate bet (win + exactas) the model identifies:
  edge          = fair_P × payout - 1
  full_kelly    = edge / (payout - 1)        # fraction of bankroll
  stake_pct     = full_kelly × kelly_fraction # fractional Kelly (default 0.25)

Sum stakes. If they exceed bankroll, scale all bets by bankroll / total.
This preserves the *shape* of the optimal portfolio — every positive-edge bet
gets its rightful seat. Bankroll is a scalar, not a structural constraint.

Run: python3 src/portfolio.py [--race 2026-kentucky-derby] [--bankroll 100]
                              [--kelly-fraction 0.25]
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
    return p_i * (p_j / (1 - p_i)) * (p_k / (1 - p_i - p_j))

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

def harville(p_i, p_j):
    if p_i >= 1.0:
        return 0.0
    return p_i * p_j / (1 - p_i)

def parse_odds(s):
    s = (s or "").strip()
    if s in ("", "N/A"):
        return None
    if "-" in s:
        a, b = s.split("-")
        return float(a) / float(b)
    return float(s)

def kelly_fraction(p, gross_payout):
    """
    p: our probability of winning the bet
    gross_payout: total return per $1 (e.g., 6-1 = 7.0; $100 exacta = 100.0)
    Returns full Kelly fraction. Negative if no edge.
    """
    if gross_payout <= 1:
        return 0.0
    edge = p * gross_payout - 1
    if edge <= 0:
        return 0.0
    return edge / (gross_payout - 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    parser.add_argument("--bankroll", type=float, default=100.0)
    parser.add_argument("--kelly-fraction", type=float, default=0.25,
                        help="Fractional Kelly multiplier (0.25 = quarter-Kelly)")
    parser.add_argument("--prob-source", choices=["cardinal", "rank", "avg"],
                        default="cardinal", help="Which model probability to use")
    parser.add_argument("--min-stake", type=float, default=0.50,
                        help="Drop bets below this minimum stake")
    parser.add_argument("--include-tri", action="store_true",
                        help="Include trifecta combos in the portfolio")
    parser.add_argument("--tri-min-prob", type=float, default=0.0001,
                        help="Skip tri combos below this fair prob (lottery filter)")
    parser.add_argument("--target-spend", type=float, default=None,
                        help="Allocate exactly this much (instead of just Kelly). "
                             "Leftover after Kelly core fills satellite lottery layer.")
    parser.add_argument("--satellite-stake", type=float, default=0.50,
                        help="Per-bet stake for the satellite lottery layer")
    parser.add_argument("--satellite-min-ev", type=float, default=0.20,
                        help="Min EV/$1 for satellite layer inclusion")
    # ---- Heuristic Layer 3: rules of thumb that operate alongside Kelly+satellite ----
    parser.add_argument("--top-pick-wheel", type=float, default=0.0,
                        help="Reserve this dollar amount for a top-pick trifecta wheel: "
                             "model's top win pick / 1-of-top-3 placers / ALL. "
                             "Captures lottery upside Kelly says is too small to stake. "
                             "0 = disabled.")
    parser.add_argument("--longshot-scan", type=float, default=0.0,
                        help="Reserve this dollar amount for live-tote longshot exacta "
                             "wheels: any horse with our_prob > market_prob × 1.5 AND "
                             "market_prob < 3%% becomes an exacta-placer key under the "
                             "model's top win pick. 0 = disabled.")
    args = parser.parse_args()

    cfg, paths = handicap.load_config(args.race)
    takeout = cfg["race"].get("exotic_takeout", 0.22)
    net_return = 1 - takeout

    # Load model probabilities + live odds
    overlays_rows = list(csv.DictReader(open(paths["overlays_out"])))
    probs = {}
    live_odds = {}
    for r in overlays_rows:
        try:
            pp = int(str(r["pp"]).rstrip("A"))
        except ValueError:
            continue
        if args.prob_source == "cardinal":
            probs[pp] = float(r["score_prob"])
        elif args.prob_source == "rank":
            probs[pp] = float(r["score_rank_prob"])
        else:
            probs[pp] = (float(r["score_prob"]) + float(r["score_rank_prob"])) / 2
        live_odds[pp] = {
            "horse": r["horse"],
            "mkt": float(r["score_mkt"]),
            "decimal_odds": (1 - float(r["score_mkt"])) / float(r["score_mkt"])
                            if float(r["score_mkt"]) > 0 else 0,
        }

    # Build candidate bets
    bets = []   # each: {kind, label, fair_p, gross_payout, full_kelly, stake_pct}

    # --- Win pool ---
    for pp, p in probs.items():
        if pp not in live_odds:
            continue
        # Live odds gives decimal odds (e.g., 6-1 -> 6.0). Gross payout = decimal + 1.
        decimal = live_odds[pp]["decimal_odds"]
        gross = decimal + 1
        fk = kelly_fraction(p, gross)
        if fk <= 0:
            continue
        bets.append({
            "kind": "WIN",
            "label": f"WIN #{pp} {live_odds[pp]['horse']}",
            "winner_pp": pp, "placer_pp": None,
            "fair_p": p,
            "gross_payout": gross,
            "full_kelly": fk,
            "stake_pct": fk * args.kelly_fraction,
        })

    # --- Exacta pool ---
    if paths["exacta_probables"].exists():
        probables = load_probables(paths["exacta_probables"])
        for (i, j), payout in probables.items():
            if i not in probs or j not in probs:
                continue
            fair = harville(probs[i], probs[j])
            if fair <= 0:
                continue
            # Exacta probable is the gross payout per $1 (after takeout)
            # Use net_return / payout = market implied prob; payout itself = gross per $1
            fk = kelly_fraction(fair, payout)
            if fk <= 0:
                continue
            bets.append({
                "kind": "EXA",
                "label": f"EXA #{i}-{j} ({live_odds[i]['horse'][:10]} > {live_odds[j]['horse'][:10]})",
                "winner_pp": i, "placer_pp": j,
                "fair_p": fair,
                "gross_payout": payout,
                "full_kelly": fk,
                "stake_pct": fk * args.kelly_fraction,
            })

    # --- Trifecta pool ---
    if args.include_tri:
        tri_path = paths["overlays_out"].parent / "trifecta_probables.txt"
        actual_tri = {}
        if tri_path.exists():
            with open(tri_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    try:
                        combo = tuple(int(x) for x in parts[0].split("-"))
                        actual_tri[combo] = float(parts[1])
                    except ValueError:
                        pass
        for i, j, k in permutations(probs.keys(), 3):
            our_p = plackett_luce_3(probs[i], probs[j], probs[k])
            if our_p < args.tri_min_prob:
                continue
            if (i, j, k) in actual_tri:
                payout = actual_tri[(i, j, k)]
            else:
                # Synthesized payout from win-pool implied probs
                mkt_p = plackett_luce_3(live_odds[i]["mkt"], live_odds[j]["mkt"],
                                        live_odds[k]["mkt"])
                if mkt_p <= 0:
                    continue
                payout = net_return / mkt_p
            fk = kelly_fraction(our_p, payout)
            if fk <= 0:
                continue
            bets.append({
                "kind": "TRI",
                "label": f"TRI #{i}-{j}-{k}",
                "winner_pp": i, "placer_pp": j,
                "fair_p": our_p,
                "gross_payout": payout,
                "full_kelly": fk,
                "stake_pct": fk * args.kelly_fraction,
            })

    if not bets:
        sys.exit("No positive-EV bets found.")

    # Sort by stake_pct descending
    bets.sort(key=lambda b: b["stake_pct"], reverse=True)

    # Total stake at full fractional Kelly
    total_kelly_pct = sum(b["stake_pct"] for b in bets)
    ideal_cost = total_kelly_pct * args.bankroll

    # Scale to bankroll if needed
    if ideal_cost > args.bankroll:
        scale = args.bankroll / ideal_cost
        scaling_note = f"Ideal cost ${ideal_cost:.2f} > bankroll ${args.bankroll:.2f}; scaling all bets by {scale:.3f}"
    else:
        scale = 1.0
        scaling_note = f"Ideal cost ${ideal_cost:.2f} ≤ bankroll ${args.bankroll:.2f}; no scaling needed"

    for b in bets:
        b["stake"] = b["stake_pct"] * args.bankroll * scale
        b["ev_per_dollar"] = b["fair_p"] * b["gross_payout"] - 1
        b["potential_payout"] = b["stake"] * b["gross_payout"]

    # Drop sub-min-stake bets
    kept = [b for b in bets if b["stake"] >= args.min_stake]
    dropped = [b for b in bets if b["stake"] < args.min_stake]
    kelly_cost = sum(b["stake"] for b in kept)

    # Two-layer allocation: if target_spend > Kelly cost, fill the rest with
    # satellite lottery bets. Each is a minimum-stake bet on a high-EV combo
    # that Kelly individually didn't size large enough.
    satellite = []
    if args.target_spend is not None and args.target_spend > kelly_cost:
        leftover = args.target_spend - kelly_cost
        # Candidate satellites: dropped bets with EV/$1 above threshold,
        # not already in kept, sorted by EV descending
        kept_keys = {(b["kind"], b.get("winner_pp"), b.get("placer_pp")) for b in kept}
        candidates = [b for b in dropped
                      if b["fair_p"] * b["gross_payout"] - 1 >= args.satellite_min_ev
                      and (b["kind"], b.get("winner_pp"), b.get("placer_pp")) not in kept_keys]
        candidates.sort(key=lambda b: b["fair_p"] * b["gross_payout"] - 1, reverse=True)
        for c in candidates:
            if leftover < args.satellite_stake:
                break
            c2 = dict(c)
            c2["stake"] = args.satellite_stake
            c2["potential_payout"] = c2["stake"] * c2["gross_payout"]
            c2["kind"] = c2["kind"] + "*"   # mark as satellite
            satellite.append(c2)
            leftover -= args.satellite_stake

    # ---- Heuristic Layer 3: rule-of-thumb additions ----
    heuristics = []

    if args.top_pick_wheel > 0:
        # Iterate over EACH cardinal-overlay horse as the wheel-top (not just one)
        # Each gets a wheel: HORSE / top-3-OTHER-fair-prob / ALL_OTHERS
        # This captures the case where any of our overlays wins, with any of the
        # other top probability horses placing, with literally any horse showing.
        # Why ALL on the show: our model can't predict the third-place longshot
        # well (e.g., AE-activated horses like Ocelli at 70-1).
        overlay_horses = []
        for r in overlays_rows:
            if r.get("score_bet") == "YES":
                try:
                    overlay_horses.append(int(str(r["pp"]).rstrip("A")))
                except ValueError:
                    pass
        if not overlay_horses:
            # Fallback to top-3 by fair_p
            overlay_horses = sorted(probs.keys(), key=lambda pp: probs[pp], reverse=True)[:3]

        sorted_by_p = sorted(probs.keys(), key=lambda pp: probs[pp], reverse=True)
        tri_path = paths["overlays_out"].parent / "trifecta_probables.txt"
        actual_tri = {}
        if tri_path.exists():
            for line in open(tri_path):
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split()
                if len(parts) < 2: continue
                try:
                    combo = tuple(int(x) for x in parts[0].split("-"))
                    actual_tri[combo] = float(parts[1])
                except ValueError: pass

        wheel_combos = []
        for top in overlay_horses:
            # Top-3 OTHER horses by fair_p
            placers = [p for p in sorted_by_p if p != top][:3]
            others = [k for k in probs.keys() if k != top]
            for j in placers:
                for k in others:
                    if k == j: continue
                    wheel_combos.append((top, j, k))
        if wheel_combos:
            per_combo_stake = args.top_pick_wheel / len(wheel_combos)
            for (i, j, k) in wheel_combos:
                if (i, j, k) in actual_tri:
                    pay = actual_tri[(i, j, k)]
                else:
                    mkt_p = plackett_luce_3(live_odds[i]["mkt"], live_odds[j]["mkt"],
                                            live_odds[k]["mkt"])
                    pay = (net_return / mkt_p) if mkt_p > 0 else 0
                fair = plackett_luce_3(probs[i], probs[j], probs[k])
                heuristics.append({
                    "kind": "TRI_HEUR",
                    "label": f"WHEEL #{i}-{j}-{k}",
                    "winner_pp": i, "placer_pp": j,
                    "fair_p": fair,
                    "gross_payout": pay,
                    "full_kelly": 0,
                    "stake_pct": 0,
                    "stake": per_combo_stake,
                    "ev_per_dollar": fair * pay - 1 if pay > 0 else 0,
                    "potential_payout": per_combo_stake * pay,
                })

    if args.longshot_scan > 0:
        # Find horses where our model loves them and market doesn't
        longshot_placers = []
        for pp, p in probs.items():
            if pp not in live_odds: continue
            mp = live_odds[pp]["mkt"]
            if mp > 0 and p > mp * 1.5 and mp < 0.03:
                longshot_placers.append(pp)
        sorted_pps = sorted(probs.keys(), key=lambda pp: probs[pp], reverse=True)
        top = sorted_pps[0] if sorted_pps else None
        if top and longshot_placers:
            per_combo_stake = args.longshot_scan / len(longshot_placers)
            for j in longshot_placers:
                if j == top: continue
                # Top → longshot exacta
                # Use exacta probables if available
                payout = 0
                if paths["exacta_probables"].exists():
                    for ((wi, wj), pay) in load_probables(paths["exacta_probables"]).items():
                        if (wi, wj) == (top, j):
                            payout = pay; break
                if payout == 0:
                    payout = net_return / (probs[top] * probs[j] / (1 - probs[top]) + 1e-9)
                fair = probs[top] * probs[j] / (1 - probs[top])
                heuristics.append({
                    "kind": "EXA_HEUR",
                    "label": f"LONGSHOT #{top}-{j}",
                    "winner_pp": top, "placer_pp": j,
                    "fair_p": fair,
                    "gross_payout": payout,
                    "full_kelly": 0,
                    "stake_pct": 0,
                    "stake": per_combo_stake,
                    "ev_per_dollar": fair * payout - 1 if payout > 0 else 0,
                    "potential_payout": per_combo_stake * payout,
                })

    final = kept + satellite + heuristics
    actual_cost = sum(b["stake"] for b in final)

    # Print
    print(f"\n=== {cfg['race']['name']} — Edge-First Portfolio ===")
    print(f"Bankroll: ${args.bankroll:.2f} · Fractional Kelly: {args.kelly_fraction} · "
          f"Prob source: {args.prob_source}")
    print(f"{scaling_note}")
    if args.target_spend:
        print(f"Target spend: ${args.target_spend:.2f} | Kelly core: ${kelly_cost:.2f} | "
              f"Satellite layer: {len(satellite)} bets, ${sum(b['stake'] for b in satellite):.2f}")
    print(f"Final ticket: {len(final)} bets, total ${actual_cost:.2f}\n")

    print(f"{'Stake':>7} {'Bet':<48} {'FairP':>7} {'Pays':>8} {'EV/$':>6} {'Type':>6}")
    print("-" * 95)
    for b in sorted(final, key=lambda b: b["stake"], reverse=True):
        print(f"${b['stake']:>6.2f} {b['label'][:48]:<48} {b['fair_p']*100:>6.3f}% "
              f"{b['gross_payout']:>7.2f} {b['ev_per_dollar']:>+5.2f} "
              f"{b['kind']:>6}")

    if dropped:
        print(f"\nDropped {len(dropped)} bets below min stake ${args.min_stake}:")
        for b in dropped[:10]:
            print(f"  ${b['stake']:.3f} {b['label'][:60]}")
        if len(dropped) > 10:
            print(f"  ...and {len(dropped) - 10} more")

    # Summary by pool
    by_pool = {"WIN": [], "EXA": []}
    for b in kept:
        by_pool[b["kind"]].append(b)
    print(f"\n{'Pool':<10} {'Bets':>5} {'Stake':>9} {'Max payout':>12}")
    for pool, bs in by_pool.items():
        if not bs:
            continue
        max_pay = max(b["potential_payout"] for b in bs) if bs else 0
        print(f"{pool:<10} {len(bs):>5} ${sum(b['stake'] for b in bs):>8.2f} ${max_pay:>10.2f}")

    # Write CSV
    out_path = paths["overlays_out"].parent / "portfolio.csv"
    cols = ["kind", "label", "winner_pp", "placer_pp", "fair_p", "gross_payout",
            "ev_per_dollar", "full_kelly", "stake_pct", "stake", "potential_payout"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for b in kept:
            w.writerow({k: round(v, 4) if isinstance(v, float) else v
                        for k, v in b.items() if k in cols})
    print(f"\nWrote portfolio to {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
