# horse-model

Handicapping models, PP parsers, and pace/speed analysis for thoroughbred racing. Started Derby Day 2026 as a public build with Claude Code, in the hours before post time at Churchill.

The premise: parse the past performance files, build a feature-scored model, strip the takeout out of the morning line, and find horses where our number says the public is wrong. Bet the overlays. Document the whole thing live.

Open question: whether the token spend clears the net winnings.

## What's here

| | |
|---|---|
| [`prompts/derby-day.md`](prompts/derby-day.md) | The seed prompt. Where it started. |
| [`src/handicap.py`](src/handicap.py) | Scoring engine. 11 weighted features → softmax → win prob → overlay. |
| [`data/parsed/field.csv`](data/parsed/field.csv) | 2026 Derby field. 24 horses, connections, top Beyers. |
| [`data/parsed/past_performances.csv`](data/parsed/past_performances.csv) | 94 prior race lines, hand-transcribed from the Equibase PP. |
| [`data/parsed/overlays.csv`](data/parsed/overlays.csv) | Model output: fair odds, market odds, overlay, bets. |
| `analysis/` | _(in progress)_ the writeup, including the actual pace-rating lesson. |

## Run it

```bash
python3 src/handicap.py
```

Stdlib only, no dependencies. Prints the scoring table and writes `overlays.csv`.

## Method

**Speed.** Beyer figures, most recent and best of last three. Filters bouncing horses.

**Pace.** Equibase's free PP doesn't ship explicit pace figures, so we approximate from running-line position calls and field size. Project today's pace shape, weight horses whose style matches. Today's read: meltdown — closers favored.

**Class.** Which preps the horse won and how cleanly. Florida Derby gets the highest weight (operator bias, historically defensible). Distance fit on top of that — sire stamina, prior 9F+ Beyers.

**Connections.** Trainer's Derby record, jockey's big-race record, equipment changes (first-time blinkers got a bump today — two horses qualify), and a "barn-pick" signal that fires when a stable runs multiple horses and the top jockey lands on one of them.

**Value.** Morning line → strip the ~16% takeout → market's true probability. Compare to ours. Bet only the overlays at >1.25x.

## Status

Mid-build. Race is at 6:57 PM ET, May 2, 2026. This README will get updated post-race with what we actually bet and how it landed.

Not a finished system. The PP "parser" is hand-transcription — a real PDF parser is tomorrow's project. The model is calibrated on priors and conversation, not historical fits. XGBoost on 24 rows is malpractice.

## License

MIT for the code. The Equibase PP files in `data/raw/` are copyrighted — they're gitignored, get your own.
