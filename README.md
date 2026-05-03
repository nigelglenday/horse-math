# horse-model

> **Derby Day 2026 result: the model picked #19 Golden Tempo. We hit. $85 → $520, net +$435 (6.1×).** Full case study at [`analysis/case-studies/2026-kentucky-derby/`](analysis/case-studies/2026-kentucky-derby/).

A generalized handicapping engine for thoroughbred racing. Started Derby Day 2026 as a five-hour public build with Claude Code. v2 is a config-driven model that runs on any race — drop in a race config + parsed PPs and run the same pipeline.

The premise: parse the past performance files, build a feature-scored model, strip the takeout out of the morning line, find horses where our number says the public is wrong. Bet the overlays, sized via fractional Kelly.

## Run on a race

```bash
python3 src/handicap.py    --race 2026-kentucky-derby
python3 src/sensitivity.py --race 2026-kentucky-derby
python3 src/exacta.py      --race 2026-kentucky-derby
python3 src/trifecta.py    --race 2026-kentucky-derby
python3 src/portfolio.py   --race 2026-kentucky-derby --bankroll 100
python3 src/charts.py      --race 2026-kentucky-derby
python3 src/fetch_odds.py  --race 2026-kentucky-derby   # tells you where to pull from
```

`--race` defaults to `2026-kentucky-derby`. Stdlib + matplotlib only.

## Layout

```
src/
  handicap.py         Scoring engine. 11 weighted features → softmax → win prob → overlay.
  sensitivity.py      Weight-perturbation scan to find robust overlays.
  exacta.py           Harville-model exacta overlays from probables.
  trifecta.py         Plackett-Luce trifecta overlays. Uses actual probables if
                      available, else synthesizes from the win pool.
  portfolio.py        Edge-first Kelly portfolio construction. Sizes every
                      positive-EV bet, scales to bankroll.
  charts.py           Visual readouts (4 PNGs per race).
  fetch_odds.py       Live-odds source helper. Reads race config, tells you
                      where to fetch from and how (most major sites are
                      JS-rendered → use WebFetch via Claude or paste manually).

data/
  races/
    2026-kentucky-derby/
      config.toml             Race-specific weights, post multipliers,
                              prep-race scoring, source URLs, etc.
      field.csv               One row per starter.
      past_performances.csv   Prior race lines.
      live_odds.csv           Live tote snapshot + scratches.
      exacta_probables.txt    24×24 probable payoff grid.
      trifecta_probables.txt  Optional. Format: "i-j-k payout" per line.
      overlays.csv            Model output (cardinal + rank).
      portfolio.csv           Kelly-sized bet recommendations.
    2026-preakness/           SCAFFOLD — Pimlico config, awaiting May 14 entries
    2026-belmont/             (next: June 6, 2026)

analysis/
  figures/<race-slug>/        Per-race PNGs.
  case-studies/<race-slug>/   Frozen artifacts of races we've analyzed and bet.
  case-studies/2026-kentucky-derby/readout.md          Pre-race handicap writeup.
  case-studies/2026-kentucky-derby/wagering.md        Pre-race wagering math + ticket structure.
  case-studies/2026-kentucky-derby/postmortem.md    Post-race analysis + lessons for v2/v3.
  case-studies/2026-kentucky-derby/cheatsheet.md    Printable race-day one-pager.

prompts/
  derby-day.md                The seed prompt that started everything.
```

Each race lives in its own directory under `data/races/`. The engine in `src/` is race-agnostic — race-specific things (weights, post biases, prep-race weighting, equipment changes, source URLs) live in the race's `config.toml`.

## Live-odds workflow

Live odds change everything (post-1 fade, public-overbet detection, exotic pricing). The model is *source-agnostic* — it just needs `live_odds.csv` to exist with the right columns. The race config declares where to pull from:

```toml
[live_odds_source]
url = "https://www.kentuckyderby.com/wager/live-odds/"
format = "js_rendered_html"
notes = "Use WebFetch via Claude (static scrape can't see JS-rendered odds)"
```

```toml
[exacta_probables_source]
url = "https://www.xpressbet.com/wagering/probables"
format = "manual_paste"
notes = "Xpressbet shows full grid for Triple Crown races. Paste into exacta_probables.txt."
```

`python3 src/fetch_odds.py --race <slug>` reads these and tells you the workflow. We don't hardwire scrapers because every site is different and tote pages break frequently.

## Method

**Speed.** Trip-adjusted Beyer figures (most recent + best of last three). Comments parsed for wide trips, trouble, "ridden out" wins.

**Pace.** Equibase free PPs don't include explicit pace ratings, so we approximate from running-line position calls and field size. Project today's pace shape, weight horses whose style matches.

**Class.** Which preps the horse won, and how cleanly. Per-race configurable: Florida Derby weighted highest for Kentucky Derby; Kentucky Derby itself most-important for Preakness; etc.

**Connections.** Trainer's record at this race + jockey big-race record + equipment changes (first-time blinkers) + barn-pick rules.

**Value.** Live tote → strip takeout → market's true probability. Compare to ours. Bet only the overlays at >1.25×.

**Post-position multiplier.** Applied post-softmax. Configurable per race — e.g., post 1 at Churchill is the rail death (1 winner in 50 modern Derbies); Pimlico has different patterns. AE-flagged horses lose the AE penalty when live odds confirm they activated.

**Sensitivity scan.** 200 trials, weights perturbed ±20%, see which overlays survive perturbation. Tags bets ROCK SOLID / Robust / Marginal / Fragile.

**Three layers of wagering, by design.** Bets are constructed via three coexisting layers, never collapsing one into another:

1. **Kelly-derived (variance-optimal)** — `src/portfolio.py` core. Mathematically rigorous, conservative.
2. **Heuristic rules** — `--top-pick-wheel` (reserves stake for top-overlay-horse trifecta wheels), `--longshot-scan` (live-tote-undervalued exacta placers), satellite layer (minimum-stake spread on high-EV combos Kelly individually says are too small).
3. **Human judgment** — what the operator brings: live-day context, story features, risk tolerance.

Validation on Derby 2026: 3-layer ticket would have captured 96% of the actual hand-tuned upside ($418 of $435), systematically. Pure quarter-Kelly would have captured 3%.

**Compounding learnings.** [`learnings/`](learnings/) holds wisdom that doesn't fit cleanly in code or config — cross-race patterns ([`learnings/index.md`](learnings/index.md)) and per-race extracts ([`learnings/2026-kentucky-derby.md`](learnings/2026-kentucky-derby.md)). The principle: every race teaches something. The model in `src/` only changes when a learning generalizes cleanly into a parameter or feature; most wisdom lives in the learnings files as priors a human carries forward.

A reminder, etched in: the model is an abstraction of the race, never the race itself. Beware Whitehead's Misplaced Concreteness — the surreptitious substitution of a model for the reality it abstracts. Always ask: what is the model not seeing?

## Status

| Phase | What | Status |
|---|---|---|
| v1 | Single-race hardcoded build | ✅ Derby Day 2026 — picked the winner |
| v2 | Generalized config-driven engine | ✅ Done |
| v2 | Edge-first Kelly portfolio (`src/portfolio.py`) | ✅ Done |
| v2 | Trifecta module with synth + actual payouts | ✅ Done |
| v2 | AE-penalty bug fix (live odds = activation signal) | ✅ Done |
| v2 | Live-odds source helper (`src/fetch_odds.py`) | ✅ Done |
| v2 | Preakness 2026 scaffold | ✅ Config stub written |
| v3 | Story features (owner gender, trainer firsts) | TODO |
| v3 | Historical-Derbies weight fitting (real Bayesian) | TODO |
| v3 | Live-odds reactive bet sizing | TODO |

## For new Claude Code sessions on this repo

[`CLAUDE.md`](CLAUDE.md) is the orientation file — auto-loaded by Claude Code, intended as the entry point for any new AI assistant session. It carries the project context, common workflows, accumulated wisdom, and a replaceable user-context section. The Derby-Day seed prompt stays frozen at [`prompts/derby-day.md`](prompts/derby-day.md) as the historical artifact.

## Data attribution

Past performance source data is from Equibase Company LLC, copyright 2026, all rights reserved. Raw PP files (`data/races/*/raw/*.pdf` and intermediate text dumps) are gitignored — get your own. The structured CSVs in `data/races/<slug>/` are derivative analytical extracts: factual fields (dates, distances, Beyer figures, finish positions) reorganized into our schema for non-commercial analytical and educational purposes. Beyer Speed Figures are a registered analytical product of Daily Racing Form / Equibase. This repository is fair-use academic-style analysis; not a substitute for a paid PP subscription, not a republication of Equibase's compiled data, not commercial.

## License

MIT for the code.
