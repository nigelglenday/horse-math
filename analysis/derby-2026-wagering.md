# 2026 Derby — Wagering Strategy ($100 Budget)

> **Result: $85 ticket cashed for $520.06. WIN #19 Golden Tempo ($241.20) + Exacta 19-1 ($278.86). Net +$435 (6.1×).** We missed a $5,625 trifecta because we never keyed #19 on top of a tri wheel — full lessons in [`derby-2026-postmortem.md`](derby-2026-postmortem.md).


This is the companion to [`derby-2026-readout.md`](derby-2026-readout.md). The first page does the handicap. This page does the betting math: market structure, exacta overlays, and the actual $100 ticket.

## The exacta math, briefly

For each (winner, placer) combo:

```
market_P  = (1 - takeout) / probable_payout       # CD exotic takeout ~22%
fair_P    = p_i × p_j / (1 - p_i)                 # Harville model from win probs
overlay   = fair_P / market_P
EV per $1 = fair_P × payout - 1
```

The Harville model assumes placement probabilities scale proportionally after the winner is removed. **It's a strong assumption** — it doesn't account for running-style × pace-fit interactions on placement. We'll come back to this.

Source code: [`src/exacta.py`](../src/exacta.py). Probable grid: [`data/races/2026-kentucky-derby/exacta_probables.txt`](../data/races/2026-kentucky-derby/exacta_probables.txt). Output: [`data/races/2026-kentucky-derby/exacta_overlays.csv`](../data/races/2026-kentucky-derby/exacta_overlays.csv).

## Where the public is wrong

Pool: $10.7M as of ~2.5h to post. Top exacta overlays by EV per $1 bet:

| Rank | Combo | Pays $1 | Market P | Our P | Overlay | EV/$1 |
|---|---|---|---|---|---|---|
| 1 | #4 Litmus Test → #18 Further Ado | $588 | 0.13% | 0.83% | **6.30x** | **+$3.91** |
| 2 | #18 Further Ado → #4 Litmus Test | $483 | 0.16% | 0.94% | 5.79x | +$3.52 |
| 3 | #1 Renegade → #4 Litmus Test | $219 | 0.36% | 2.03% | 5.71x | +$3.45 |
| 4 | #4 Litmus Test → #1 Renegade | $254 | 0.31% | 1.50% | 4.87x | +$2.80 |
| 5 | #1 Renegade → #3 Intrepido | $346 | 0.23% | 0.95% | 4.21x | +$2.28 |
| 6 | #1 Renegade → #18 Further Ado | $35 | 2.23% | 5.01% | 2.25x | +$0.75 |
| 7 | #18 Further Ado → #19 Golden Tempo | $192 | 0.41% | 0.77% | 1.90x | +$0.48 |

What the public is hammering (avoid):
- #6 Commandment → #1 Renegade ($23.05) — chalk-chalk, fair
- #1 Renegade → #6 Commandment ($23.03) — chalk-chalk, fair-ish
- **#18 Further Ado → #6 Commandment ($26.95)** — *negative* EV (-$0.42/$1)
- **#18 Further Ado → #12 Chief Wallabee ($39.09)** — also negative (-$0.62/$1)

The pattern: **the public is loaded on the favorites finishing 1-2 with each other.** Combos involving Litmus Test underneath, or Intrepido or Albus or Potente in the place spot, are dramatically underbet.

## Two big caveats before sizing the ticket

### 1. Post 1 is a rail death historically

Renegade drew the rail. Since the field expanded to 20 in 1975, **post 1 has produced exactly one Derby winner: Ferdinand in 1986.** That's 1 in 50 modern Derbies — a strike rate of 2% vs. the 5% random expectation. Post 1 underperforms by ~50-60%.

Why: at Churchill the first turn comes ~3/16 mile out, the rail can be dead by Derby Day from a meet's worth of training, and 18 horses fanning right while you're trapped inside is a lose-lose decision tree.

The ML→live drift on Renegade (4-1 → 6-1) is partially this fear, and the fear is justified. Our model penalizes post 1 by ~50% (40 vs 90 elsewhere). That may be light. **If we doubled the penalty, Renegade's overlay shrinks from 1.58x to ~1.20x** — still a bet, but thinner. This argues for *diversifying* off Renegade rather than going all-in.

### 2. Harville inflates Litmus-Test-underneath overlays

Litmus Test is a confirmed front-runner. With 4 confirmed E's in a 19-horse Derby, he likely doesn't get the lead. Without the lead, his form line says he flattens. **His true place probability is probably lower than Harville's proportional assumption** — maybe 30% lower.

Even at the discount, the Litmus-Test-underneath combos remain positive EV. But a $588 payout we estimate at $400 is still good — just smaller than the headline overlay number suggests.

## The $100 ticket

### Sensitivity scan (added late afternoon)

Before finalizing, ran 200 trials with each weight perturbed ±20% (random Gaussian, renormalized to sum to 1). The model with post-1 multiplier applied. Results:

| Horse | Bet % across 200 trials | Mean overlay | Range | Verdict |
|---|---|---|---|---|
| **#18 Further Ado** | 100% | 1.66x | 1.52–1.77x | **ROCK SOLID** |
| **#19 Golden Tempo** | 100% | 2.02x | 1.85–2.21x | **ROCK SOLID** |
| #14 Potente | 32% | 1.22x | 1.11–1.36x | Fragile |
| #1 Renegade | 0% | 1.14x | 1.01–1.25x | Cardinal says no |
| #4 Litmus Test | 0% | 1.27x | 1.18–1.39x | Marginal |
| #16 Pavlovian | 0% | 1.91x | 1.81–2.01x | Lottery (low fair P) |

The honest read: **only Further Ado and Golden Tempo are robust cardinal overlays.** Renegade is a rank-only play. Litmus Test is marginal but kept in exotics for asymmetric place upside.

### WIN ($40)

| Stake | Horse | Live | If wins |
|---|---|---|---|
| **$20** | #18 Further Ado | 6-1 | $140 |
| $10 | #1 Renegade | 6-1 | $70 |
| $10 | #19 Golden Tempo | 25-1 | $260 |

Further Ado is now the top win bet (rock-solid cardinal, Cox barn-pick signal). Renegade gets a smaller stake — rank says yes, cardinal-with-post-1-penalty says no, sensitivity says fragile. Golden Tempo is the rock-solid mid-priced overlay. **Litmus Test dropped from the win pool** (fair prob too low to clear 4% threshold reliably across perturbations) but kept in exotics where his Harville place upside is asymmetric.

### EXACTAS ($54)

Key #18 Further Ado over (×$3 each = $9):
- 18-4 ($483), 18-19 ($192), 18-1 ($34)

Key #1 Renegade over (×$2 each = $12):
- 1-4 ($219), 1-3 ($346), 1-18 ($35), 1-19 ($118), 1-14 ($159), 1-8 ($47.78)

Key #19 Golden Tempo over (×$2 each = $4):
- 19-1 ($133), 19-18 ($241)

Key #4 Litmus Test over (×$2 each = $8):
- 4-1 ($253), 4-18 ($588), 4-6 ($335), 4-8 ($429)

**Top-2 cardinal-overlay box (×$3 each = $6):** 18-19, 19-18

Boosts on top three single-combo overlays (×$5 each = $15):
- 1-4 (boost), 4-18 (boost), 18-4 (boost)

### TRIFECTAS ($6)

Two part-wheels keying our overlay box (1, 4, 18, 19):
- `1 / 4-18-19 / 4-18-19` — 6 combos × $0.50 = $3
- `4 / 1-18-19 / 1-18-19` — 6 combos × $0.50 = $3

### Summary

| Pool | Spend | Coverage |
|---|---|---|
| WIN | $40 | 3 horses (1, 4, 18) |
| EXACTA | $54 | 13 distinct combos, 3 boosted |
| TRIFECTA | $6 | 12 part-wheel combos |
| **Total** | **$100** | |

### Outcome scenarios

| Outcome | Win pool | Best exacta | Trifecta |
|---|---|---|---|
| 1 wins, 4 places | $175 | $1758 (boosted 1-4) | $32 |
| 1 wins, 18 places | $175 | $280 (1-18) | $32 |
| 4 wins, 18 places | $270 | $4118 (boosted 4-18) | possible |
| 18 wins, 4 places | $35 | $3864 (boosted 18-4) | possible |
| 1 wins, 3 places | $175 | $1039 (1-3) | — |
| 4 wins, 1 places | $270 | $1521 (4-1) | possible |
| 18 wins, 19 places | $35 | $576 (18-19) | possible |
| 1 wins, anyone else covered | $175 | $0–$300 | $0–$32 |
| Renegade DOESN'T win | $0–$270 | $0–$4118 | $0 |

**Best-case home runs:** Litmus Test → Further Ado or vice versa (both pay $4K+ on the boosted ticket).
**Realistic base case:** Renegade wins, decent exacta hit if any of {3, 4, 8, 14, 18, 19} places.

### Pre-bet checklist

- [ ] Re-pull live odds within 30 min of post — they'll move
- [ ] Re-pull exacta probables (the ones above are from ~16:00, will shift)
- [ ] Track-bias check: has the rail been working today, or has speed been cooked?
- [ ] Confirm no late scratches
- [ ] Bet through TwinSpires or track windows
