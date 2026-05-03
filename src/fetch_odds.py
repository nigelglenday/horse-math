"""
Live-odds helper.

The model is source-agnostic — it just needs `data/races/<slug>/live_odds.csv`
to exist with the columns: pp, horse, ml_odds, live_odds, scratched, as_of.

This script:
  1. Reads the race config's [live_odds_source] section
  2. For static HTML sources: tries to fetch and parse
  3. For JS-rendered sources: prints instructions to use WebFetch via Claude
  4. For manual sources: opens the URL and tells you what to paste

Run: python3 src/fetch_odds.py [--race 2026-kentucky-derby]
"""
from __future__ import annotations
import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap

ROOT = Path(__file__).resolve().parent.parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", default="2026-kentucky-derby")
    parser.add_argument("--open", action="store_true",
                        help="Open the source URL in default browser")
    args = parser.parse_args()

    cfg, paths = handicap.load_config(args.race)
    src = cfg.get("live_odds_source", {})
    if not src:
        sys.exit(f"No [live_odds_source] in {args.race} config")

    url = src.get("url", "")
    fmt = src.get("format", "")
    notes = src.get("notes", "")
    target = paths["live_odds"]

    print(f"\n=== Live odds for {cfg['race']['name']} ===")
    print(f"Source URL: {url}")
    print(f"Format:     {fmt}")
    if notes:
        print(f"Notes:      {notes}")
    print(f"Target:     {target.relative_to(ROOT)}")
    print()

    if fmt == "static_html":
        # Best-effort static scrape
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            sys.exit("Need requests + bs4 for static scrape: pip install requests beautifulsoup4")
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            tables = soup.find_all("table")
            print(f"Fetched {len(r.content)} bytes, found {len(tables)} tables.")
            print("Per-source parsing not implemented yet; inspect manually:")
            print(f"  curl -A 'Mozilla/5.0' {url} | less")
        except Exception as e:
            sys.exit(f"Fetch failed: {e}")
    elif fmt == "js_rendered_html":
        print("⚠️  This source is JS-rendered. Static scrape will not see the odds.")
        print("\nHow to fetch:")
        print(f"  1. In Claude conversation: WebFetch tool → {url}")
        print(f"     Prompt: 'list every horse in this race with current win odds'")
        print(f"  2. Paste the result into {target.relative_to(ROOT)}")
        print(f"     (matching the existing CSV columns: pp,horse,ml_odds,live_odds,scratched,as_of)")
        if args.open:
            webbrowser.open(url)
    elif fmt == "manual_paste":
        print("Manual-paste source. Open the URL, copy the data, paste into the target file.")
        if args.open:
            webbrowser.open(url)
    else:
        print(f"Unknown format '{fmt}'. Open URL manually.")
        if args.open:
            webbrowser.open(url)

if __name__ == "__main__":
    main()
