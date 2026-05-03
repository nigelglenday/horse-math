# horse-model

> **Derby Day 2026 result: the model picked #19 Golden Tempo. We hit. $85 → $520, net +$435 (6.1×).** Full case study at [`analysis/case-studies/2026-kentucky-derby/`](analysis/case-studies/2026-kentucky-derby/).

A generalized handicapping engine for thoroughbred racing. Started Derby Day 2026 as a five-hour public build with Claude Code. v2 is a config-driven model that runs on any race — drop in a race config + parsed PPs and run the same pipeline.

The premise: parse the past performance files, build a feature-scored model, strip the takeout out of the morning line, find horses where our number says the public is wrong. Bet the overlays. Document the whole thing live.

## Run on a race

```bash
python3 src/handicap.py    --race 2026-kentucky-derby
python3 src/sensitivity.py --race 2026-kentucky-derby
python3 src/exacta.py      --race 2026-kentucky-derby
python3 src/charts.py      --race 2026-kentucky-derby
```

`--race` defaults to `2026-kentucky-derby`. Stdlib + matplotlib only.

## Layout

```
src/
  handicap.py         Scoring engine. 11 weighted features → softmax → win prob → overlay.
  sensitivity.py      Weight-perturbation scan to find robust overlays.
  exacta.py           Harville-model exacta overlays from probables.
  charts.py           Visual readouts (4 PNGs per race).

data/
  races/
    2026-kentucky-derby/
      config.toml             Race-specific weights, post multipliers, prep scoring.
      field.csv               One row per starter.
      past_performances.csv   Prior race lines.
      live_odds.csv           Live tote snapshot + scratches.
      exacta_probables.txt    24×24 probable payoff grid.
      overlays.csv            Model output (cardinal + rank).
    2026-preakness/           (next: May 16, 2026)
    2026-belmont/             (next: June 6, 2026)

analysis/
  figures/<race-slug>/        Per-race PNGs.
  case-studies/<race-slug>/   Frozen artifacts of races we've analyzed and bet.

prompts/
  derby-day.md                The seed prompt that started everything.
```

Each race lives in its own directory under `data/races/`. The engine in `src/` is race-agnostic — race-specific things (weights, post biases, prep-race weighting, equipment changes) live in the race's `config.toml`.

## Method

**Speed.** Trip-adjusted Beyer figures (most recent + best of last three). Comments parsed for wide trips, trouble, "ridden out" wins.

**Pace.** Equibase free PPs don't include explicit pace ratings, so we approximate from running-line position calls and field size. Project today's pace shape, weight horses whose style matches.

**Class.** Which preps the horse won, and how cleanly. Per-race configurable: Florida Derby weighted highest for Kentucky Derby; Kentucky Derby itself most-important for Preakness; etc.

**Connections.** Trainer's record at this race + jockey big-race record + equipment changes (first-time blinkers) + barn-pick rules (e.g., "Cox runs three, his top jockey is on Further Ado").

**Value.** Live tote → strip takeout → market's true probability. Compare to ours. Bet only the overlays at >1.25×.

**Post-position multiplier.** Applied post-softmax. Configurable per race — e.g., post 1 at Churchill is the rail death (1 winner in 50 modern Derbies); Pimlico has different patterns.

**Sensitivity scan.** 200 trials, weights perturbed ±20%, see which overlays survive perturbation. Tags bets ROCK SOLID / Robust / Marginal / Fragile.

## Status

v1 (Derby Day, May 2 2026): single-race hardcoded. Picked the winner.
v2 (now): generalized, config-driven, same engine runs any race.
v3 (planned): edge-first portfolio construction (`src/portfolio.py`), historical-Derby weight fitting, story-feature surfacing, AE-penalty bug fix.

## License

MIT for the code. Equibase PP files are copyrighted — they're gitignored, get your own.
