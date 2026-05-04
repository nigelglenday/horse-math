"""
Two-panel chart for the Golden Tempo case-study sub-page.
Left: Beyer trajectory across his last 3 prep races.
Right: Position-call trajectory showing closer style.

Run: python3 scripts/make_gt_chart.py
"""
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "analysis" / "figures" / "2026-kentucky-derby"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": ":",
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

# Panel 1: Beyer trajectory
races = ["Lecomte G3\n(Jan)", "Risen Star G2\n(Feb)", "Louisiana Derby G2\n(Mar)"]
beyers = [85, 90, 95]
adjusted = [85, 90, 98]   # +3 trip adj on LaDerby
ax1.plot(races, beyers, marker="o", color="#666", lw=2, ms=10, label="Raw Beyer")
ax1.plot(races, adjusted, marker="s", color="#D4AF37", lw=2, ms=10,
         label="Trip-adjusted Beyer", linestyle="--")
ax1.set_ylabel("Beyer Speed Figure")
ax1.set_title("Rising Beyers across three prep races", loc="left", fontsize=12)
ax1.set_ylim(75, 105)
ax1.axhline(100, color="#999", lw=0.7, ls=":", label="100 line")
ax1.legend(loc="lower right", framealpha=0.9)
for r, b in zip(races, beyers):
    ax1.annotate(str(b), (r, b), textcoords="offset points",
                 xytext=(0, 12), ha="center", fontsize=10, color="#333")

# Panel 2: position-call trajectory (last 3 races)
calls = ["1st call", "2nd call", "Stretch", "Finish"]
lecomte = [9, 9, 4, 1]
risen   = [7, 7, 5, 3]
laderby = [8, 8, 7, 3]
ax2.plot(calls, lecomte, marker="o", color="#1b9e77", lw=2, ms=8, label="Lecomte (won)")
ax2.plot(calls, risen,   marker="o", color="#7570b3", lw=2, ms=8, label="Risen Star (3rd)")
ax2.plot(calls, laderby, marker="o", color="#d95f02", lw=2, ms=8, label="LaDerby (3rd)")
ax2.invert_yaxis()
ax2.set_ylabel("Field position (1 = leading)")
ax2.set_title("Same pattern every race: way back, closes hard", loc="left", fontsize=12)
ax2.set_yticks([1, 3, 5, 7, 9, 11])
ax2.legend(loc="upper right", framealpha=0.9)

plt.tight_layout()
out = OUT_DIR / "05_golden_tempo.png"
plt.savefig(out, bbox_inches="tight")
plt.close()
print(f"Wrote {out.relative_to(ROOT)}")
