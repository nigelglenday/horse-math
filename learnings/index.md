# Learnings, cross-race

What we know after each race that doesn't fit cleanly in code. Per-race entries below; this index pulls out cross-race patterns.

The `src/` engine changes when a finding generalizes into a parameter or feature. Most findings stay here as priors a human carries into the next race.

## Three layers of wagering

1. **Kelly core** (`src/portfolio.py`). Variance-optimal, conservative, under-deploys capital with our edge sizes.
2. **Heuristics** (`--top-pick-wheel`, `--longshot-scan`, satellite). Catches lottery upside Kelly says is too small to bet.
3. **Human judgment**. Story features, live-day context, risk tolerance. Always overrides.

Derby check: a 3-layer ticket caught 96% of the hand-tuned result. Pure Kelly caught 3%.

## Patterns

### 1. Live-tote drift on the favorite is signal

ML 4-1 to live 6-1 isn't noise. The public sees something the linemaker missed (often a post draw or a soft prep). Weight live-odds movement as a third signal alongside our model and ML.

### 2. Named connections inflate prices more than the model captures

Mike Smith took So Happy from 15-1 to 5-1. Baffert took Litmus Test from 50-1 to 26-1. For known names (Velazquez, Smith, Baffert, Pletcher, Castellano), expect 1.15-1.5x public-money inflation. Read it off live odds; don't estimate it from static factors.

### 3. AE-activated horses are starters

When scratches activate an AE, drop the AE penalty. Live odds presence is the activation signal. Cost us third position in the Derby trifecta (Ocelli, 70-1, AE, ran 3rd) before we fixed the bug.

### 4. Sensitivity ROCK SOLID is not the same as right

Sensitivity tells you the answer holds under weight perturbation. It does not tell you the weights are right. Further Ado was 100% bet-rate across 200 trials and finished off the board.

### 5. Top overlay belongs on top of trifectas

If a horse is a top overlay to win, key it on top of trifectas. Not just exactas. Skipping the trifecta wheel "to save budget" left $5,625 on the table at the Derby.

### 6. Bankroll is a scalar

The portfolio shape is set by edge analysis. Bankroll sets stake size, not which bets to include. Build the shape first; scale to bankroll second.

### 7. Story matters. Surface it.

First-female-trainer, returning-from-suspension, 60-year-old Hall-of-Famer. These signals predict where public money goes and make the bet memorable. Cherie DeVaux was already in `field.csv` for the Derby. We didn't surface her until the result.

### 8. The model is not the race

The Beyer is an estimate of speed. Plackett-Luce is an approximation of ordering. The sensitivity scan is a robustness check, not truth. The map keeps being useful exactly as long as you remember it isn't the territory.

## Per-race entries

- [`2026-kentucky-derby.md`](2026-kentucky-derby.md), founding instance, 6.12x return
- `2026-preakness.md`, post-race May 16
- `2026-belmont.md`, post-race June 6
