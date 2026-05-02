"""
Visual readouts for the Derby 2026 model. Outputs four PNGs into analysis/figures/.

Run: python3 src/charts.py
"""
from __future__ import annotations
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

OVERLAYS = ROOT / "data" / "parsed" / "overlays.csv"
LIVE = ROOT / "data" / "parsed" / "live_odds.csv"
PP = ROOT / "data" / "parsed" / "past_performances.csv"
FIELD = ROOT / "data" / "parsed" / "field.csv"

# Style — clean and tight, no flashy stuff
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


# ---------- Chart 1: Overlay barbell — cardinal vs rank per horse ----------
def chart_overlays():
    rows = list(csv.DictReader(open(OVERLAYS)))
    # Sort by max overlay descending
    def maxoverlay(r):
        c = float(r["score_overlay"])
        rk = float(r["score_rank_overlay"])
        return max(c, rk)
    rows = sorted(rows, key=maxoverlay, reverse=True)

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

    ax.set_yticks(ys)
    ax.set_yticklabels(horses)
    ax.invert_yaxis()
    ax.set_xlim(0, 3.5)
    ax.set_xlabel("Overlay (our prob ÷ market prob)")
    ax.set_title("2026 Derby — Overlay by horse (cardinal vs rank-based)\n"
                 "live odds, post-scratch (5 horses out, field of 19)",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(OUT / "01_overlays.png", bbox_inches="tight")
    plt.close()


# ---------- Chart 2: Probability stacks — market vs our cardinal vs our rank ----------
def chart_probabilities():
    rows = list(csv.DictReader(open(OVERLAYS)))
    rows = sorted(rows, key=lambda r: float(r["score_mkt"]), reverse=True)

    horses = [r["horse"][:18] for r in rows]
    mkt = [float(r["score_mkt"]) * 100 for r in rows]
    card = [float(r["score_prob"]) * 100 for r in rows]
    rank = [float(r["score_rank_prob"]) * 100 for r in rows]
    ys = list(range(len(horses)))
    h = 0.27

    fig, ax = plt.subplots(figsize=(9, 7.5))
    ax.barh([y - h for y in ys], mkt, h, color="#444", label="Market (live tote, takeout-stripped)")
    ax.barh(ys, card, h, color="#d95f02", label="Cardinal model")
    ax.barh([y + h for y in ys], rank, h, color="#7570b3", label="Rank-based model")

    ax.set_yticks(ys)
    ax.set_yticklabels(horses)
    ax.invert_yaxis()
    ax.set_xlabel("Win probability (%)")
    ax.set_title("2026 Derby — Win probability: market vs our two models\n"
                 "where bars stick OUT to the right of the market = overlay",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(OUT / "02_probabilities.png", bbox_inches="tight")
    plt.close()


# ---------- Chart 3: Odds movement — ML vs live ----------
def chart_movement():
    rows = list(csv.DictReader(open(LIVE)))
    rows = [r for r in rows if r["scratched"].lower() != "true"]

    # Implied probs for both
    def hand_implied(s):
        d = parse_odds(s)
        return implied(d) * 100 if d else None

    horses = []
    ml_imp = []
    live_imp = []
    for r in rows:
        ml = hand_implied(r["ml_odds"])
        lv = hand_implied(r["live_odds"])
        if ml is None or lv is None:
            continue
        horses.append(r["horse"][:18])
        ml_imp.append(ml)
        live_imp.append(lv)

    # Sort by live implied descending (most-bet at top)
    idx = sorted(range(len(horses)), key=lambda i: live_imp[i], reverse=True)
    horses = [horses[i] for i in idx]
    ml_imp = [ml_imp[i] for i in idx]
    live_imp = [live_imp[i] for i in idx]
    ys = list(range(len(horses)))

    fig, ax = plt.subplots(figsize=(9, 7.5))
    for y, m, l in zip(ys, ml_imp, live_imp):
        color = "#1b9e77" if l > m else "#d95f02"
        ax.annotate("", xy=(l, y), xytext=(m, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6))
    ax.scatter(ml_imp, ys, s=45, color="#888", zorder=3, label="Morning Line implied %")
    ax.scatter(live_imp, ys, s=80, color="#222", zorder=4,
               edgecolors="white", lw=0.8, label="Live tote implied %")

    ax.set_yticks(ys)
    ax.set_yticklabels(horses)
    ax.invert_yaxis()
    ax.set_xlabel("Implied win probability (%) — raw, not takeout-stripped")
    ax.set_title("2026 Derby — Where the public money went (ML → live)\n"
                 "green arrows = taking money (price shortened) · "
                 "orange = drifting (price lengthened)",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(OUT / "03_odds_movement.png", bbox_inches="tight")
    plt.close()


# ---------- Chart 4: Beyer trajectory for top contenders ----------
def chart_beyer_trajectory():
    pps = list(csv.DictReader(open(PP)))
    overlay_rows = list(csv.DictReader(open(OVERLAYS)))

    # Top 6 by cardinal fair prob
    top = sorted(overlay_rows, key=lambda r: float(r["score_prob"]), reverse=True)[:6]
    contenders = [r["horse"] for r in top]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    palette = ["#d95f02", "#1b9e77", "#7570b3", "#e7298a", "#666666", "#a6761d"]
    for c, color in zip(contenders, palette):
        horse_pps = [p for p in pps if p["horse"] == c]
        # Sort chronologically and keep the most recent 5
        horse_pps = sorted(horse_pps, key=lambda p: p["pp_date"])[-5:]
        beyers = [int(p["beyer"]) for p in horse_pps if p["beyer"] not in ("N/A", "")]
        if not beyers:
            continue
        x = list(range(-len(beyers) + 1, 1))   # most recent on the right (x=0)
        ax.plot(x, beyers, marker="o", color=color, label=c[:18], lw=1.7, ms=7)

    ax.axhline(100, color="#888", lw=0.8, ls=":", label="100 Beyer line (Derby contender bar)")
    ax.set_xlabel("Race position (rightmost = most recent)")
    ax.set_ylabel("Beyer Speed Figure")
    ax.set_title("2026 Derby — Beyer trajectory for top 6 contenders (last 5 starts)\n"
                 "form trend matters: rising > flat > declining",
                 loc="left", fontsize=11)
    ax.legend(loc="lower right", framealpha=0.9, ncol=2)
    plt.tight_layout()
    plt.savefig(OUT / "04_beyer_trajectory.png", bbox_inches="tight")
    plt.close()


def main():
    chart_overlays()
    chart_probabilities()
    chart_movement()
    chart_beyer_trajectory()
    print(f"Wrote 4 charts to {OUT.relative_to(ROOT)}/")
    for p in sorted(OUT.glob("*.png")):
        print(f"  {p.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
