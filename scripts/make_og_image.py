"""
Generate the Open Graph card image at assets/og-image.png.
Renders a 1200×630 social card that Slack/LinkedIn/Twitter display when
math.horse links are shared.

Run: python3 scripts/make_og_image.py
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath
import matplotlib as mpl

# Disable LaTeX math-mode interpretation of dollar signs in regular text
mpl.rcParams["text.usetex"] = False
mpl.rcParams["mathtext.default"] = "regular"

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "og-image.png"

# 1200×630 is the canonical OG image size
fig = plt.figure(figsize=(12, 6.30), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])   # axes fills full figure, no padding
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.30)
ax.axis("off")

# Black background
ax.add_patch(patches.Rectangle((0, 0), 12, 6.30, color="#000"))

# Gold accent bar at top
ax.add_patch(patches.Rectangle((0, 6.00), 12, 0.30, color="#D4AF37"))

# Title
ax.text(0.6, 4.5, "math.horse", fontsize=80, color="white",
        fontweight="bold", family="sans-serif")

# Tagline
ax.text(0.6, 3.5, "A generalized handicapping engine for thoroughbred racing.",
        fontsize=26, color="#cccccc", family="sans-serif")

# Result line — escape $ to avoid mathmode
ax.text(0.6, 2.2,
        r"Derby Day 2026 · picked Golden Tempo (25-1) · net +\$435 on \$85",
        fontsize=24, color="#D4AF37", family="sans-serif", style="italic")

# Tech stack
ax.text(0.6, 1.0,
        "Python · Pydantic · matplotlib · Kelly portfolio · Plackett-Luce exotics",
        fontsize=18, color="#888", family="sans-serif")

# URL bottom-right
ax.text(11.4, 0.45, "math.horse", fontsize=22, color="#666",
        family="monospace", ha="right")

plt.savefig(OUT, dpi=100, facecolor="black", edgecolor="none",
            bbox_inches=None, pad_inches=0)
plt.close()
print(f"Wrote {OUT.relative_to(ROOT)} — {OUT.stat().st_size // 1024}KB")
