"""
Visual readouts. Outputs four PNGs into analysis/figures/<race-slug>/.

Run: python3 src/charts.py [--race 2026-kentucky-derby]
"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap

ROOT = Path(__file__).resolve().parent.parent

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "font.size": 10,
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": ":",
})

def parse_odds(s):
    s = (s or "").strip()
    if s in ("", "N/A"):
        return None
    if "-" in s:
        a, b = s.split("-")
        return float(a) / float(b)
    return float(s)

def implied(o):
    return 1.0 / (o + 1) if o is not None else None


def chart_overlays(rows, race_name, out_dir):
    rows = sorted(rows, key=lambda r: max(float(r["score_overlay"]),
                                          float(r["score_rank_overlay"])), reverse=True)
    horses = [r["horse"][:18] for r in rows]
    card = [float(r["score_overlay"]) for r in rows]
    rank = [float(r["score_rank_overlay"]) for r in rows]
    ys = list(range(len(horses)))

    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.axvline(1.0, color="#888", lw=1, ls="--", label="Fair (overlay = 1)")
    ax.axvspan(1.25, 5, alpha=0.08, color="#1b9e77", label="Bet zone (≥1.25x)")
    ax.scatter(card, ys, s=70, color="#d95f02", label="Cardinal", zorder=3)
    ax.scatter(rank, ys, s=70, color="#7570b3", label="Rank-based", zorder=3)
    for y, c, r in zip(ys, card, rank):
        ax.plot([min(c, r), max(c, r)], [y, y], color="#bbb", lw=1.5, zorder=2)
    ax.set_yticks(ys); ax.set_yticklabels(horses); ax.invert_yaxis()
    ax.set_xlim(0, max(3.5, max(card + rank) + 0.3))
    ax.set_xlabel("Overlay (our prob ÷ market prob)")
    ax.set_title(f"{race_name} — Overlay by horse (cardinal vs rank-based)",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(out_dir / "01_overlays.png", bbox_inches="tight"); plt.close()


def chart_probabilities(rows, race_name, out_dir):
    rows = sorted(rows, key=lambda r: float(r["score_mkt"]), reverse=True)
    horses = [r["horse"][:18] for r in rows]
    mkt  = [float(r["score_mkt"]) * 100 for r in rows]
    card = [float(r["score_prob"]) * 100 for r in rows]
    rank = [float(r["score_rank_prob"]) * 100 for r in rows]
    ys = list(range(len(horses))); h = 0.27
    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.barh([y - h for y in ys], mkt, h, color="#444", label="Market (live tote)")
    ax.barh(ys, card, h, color="#d95f02", label="Cardinal model")
    ax.barh([y + h for y in ys], rank, h, color="#7570b3", label="Rank-based")
    ax.set_yticks(ys); ax.set_yticklabels(horses); ax.invert_yaxis()
    ax.set_xlabel("Win probability (%)")
    ax.set_title(f"{race_name} — Win probability: market vs our two models",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(out_dir / "02_probabilities.png", bbox_inches="tight"); plt.close()


def chart_movement(live_path, race_name, out_dir):
    rows = list(csv.DictReader(open(live_path)))
    rows = [r for r in rows if r["scratched"].lower() != "true"]
    horses, ml_imp, live_imp = [], [], []
    for r in rows:
        d_ml, d_live = parse_odds(r["ml_odds"]), parse_odds(r["live_odds"])
        if d_ml is None or d_live is None:
            continue
        horses.append(r["horse"][:18])
        ml_imp.append(implied(d_ml) * 100)
        live_imp.append(implied(d_live) * 100)
    idx = sorted(range(len(horses)), key=lambda i: live_imp[i], reverse=True)
    horses = [horses[i] for i in idx]
    ml_imp = [ml_imp[i] for i in idx]; live_imp = [live_imp[i] for i in idx]
    ys = list(range(len(horses)))
    fig, ax = plt.subplots(figsize=(9, 7.5))
    for y, m, l in zip(ys, ml_imp, live_imp):
        color = "#1b9e77" if l > m else "#d95f02"
        ax.annotate("", xy=(l, y), xytext=(m, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6))
    ax.scatter(ml_imp, ys, s=45, color="#888", zorder=3, label="Morning Line implied %")
    ax.scatter(live_imp, ys, s=80, color="#222", zorder=4,
               edgecolors="white", lw=0.8, label="Live tote implied %")
    ax.set_yticks(ys); ax.set_yticklabels(horses); ax.invert_yaxis()
    ax.set_xlabel("Implied win probability (%) — raw, not takeout-stripped")
    ax.set_title(f"{race_name} — Where the public money went (ML → live)\n"
                 "green = took money · orange = drifted",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(out_dir / "03_odds_movement.png", bbox_inches="tight"); plt.close()


def chart_beyer_trajectory(pp_path, overlays_path, race_name, out_dir):
    pps = list(csv.DictReader(open(pp_path)))
    overlay_rows = list(csv.DictReader(open(overlays_path)))
    top = sorted(overlay_rows, key=lambda r: float(r["score_prob"]), reverse=True)[:6]
    contenders = [r["horse"] for r in top]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    palette = ["#d95f02", "#1b9e77", "#7570b3", "#e7298a", "#666666", "#a6761d"]
    for c, color in zip(contenders, palette):
        horse_pps = [p for p in pps if p["horse"] == c]
        horse_pps = sorted(horse_pps, key=lambda p: p["pp_date"])[-5:]
        beyers = [int(p["beyer"]) for p in horse_pps if p["beyer"] not in ("N/A", "")]
        if not beyers:
            continue
        x = list(range(-len(beyers) + 1, 1))
        ax.plot(x, beyers, marker="o", color=color, label=c[:18], lw=1.7, ms=7)
    ax.axhline(100, color="#888", lw=0.8, ls=":", label="100 Beyer line")
    ax.set_xlabel("Race position (rightmost = most recent)")
    ax.set_ylabel("Beyer Speed Figure")
    ax.set_title(f"{race_name} — Beyer trajectory for top 6 contenders (last 5 starts)",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9, ncol=2)
    plt.tight_layout()
    plt.savefig(out_dir / "04_beyer_trajectory.png", bbox_inches="tight"); plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    args = parser.parse_args()

    cfg, paths = handicap.load_config(args.race)
    race_name = cfg["race"]["name"]
    out_dir = ROOT / "analysis" / "figures" / args.race
    out_dir.mkdir(parents=True, exist_ok=True)

    overlay_rows = list(csv.DictReader(open(paths["overlays_out"])))

    chart_overlays(overlay_rows, race_name, out_dir)
    chart_probabilities(overlay_rows, race_name, out_dir)
    chart_movement(paths["live_odds"], race_name, out_dir)
    chart_beyer_trajectory(paths["pp"], paths["overlays_out"], race_name, out_dir)

    print(f"Wrote 4 charts to {out_dir.relative_to(ROOT)}/")
    for p in sorted(out_dir.glob("*.png")):
        print(f"  {p.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
