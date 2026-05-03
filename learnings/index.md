# Learnings — cross-race wisdom

> "We must beware of what Whitehead called the Fallacy of Misplaced Concreteness — surreptitiously substituting an abstraction for the concrete reality it abstracts. The model is a map. The race is the territory. The map is useful exactly to the extent that we remain alert to where it diverges from the territory."

This directory holds wisdom that doesn't fit in code or config. Each race adds an entry; this index distills cross-race patterns. The model in `src/` is updated only when a learning generalizes cleanly into a parameter, weight, or feature. Most learnings live here, as priors a human must carry forward.

## Three layers of wagering, by design

We bet using **three layers operating in parallel**, never one collapsing into another:

1. **Kelly-derived (variance-optimal)** — `src/portfolio.py` core. Mathematically rigorous, conservative, optimal for long-run growth. Under-deploys capital because it correctly recognizes most positive-EV bets are too small to risk meaningfully.
2. **Rule-of-thumb heuristics** — `--top-pick-wheel`, `--longshot-scan`, satellite layer. Captures lottery upside (rare, high-payout combos) that Kelly's variance-aversion correctly says shouldn't be sized large but pragmatically should be in the ticket at minimum stake.
3. **Human judgment** — what the operator brings. Story features (first female trainer, comeback narratives), live-day context (track bias, weather, paddock observation), risk tolerance unique to the day. The model can surface the data; only a human integrates it with the texture of the moment.

The Derby validated this: a 3-layer ticket would have captured 96% of the hand-tuned result systematically. Pure Kelly would have captured 3%.

## Cross-race patterns (compounding wisdom)

These are patterns observed across our races, abstracted into priors that should be brought into every future race:

### 1. Live-tote drift on the favorite is signal, not noise
When ML chalk drifts (e.g., 4-1 → 6-1), the public has identified something the linemaker missed. Often it's a structural concern (post-1 in a 20-horse field, soft prep, equipment doubt). **Priors should weight live-odds movement as a 3rd signal, alongside our model and ML.**

### 2. Star-jockey/star-trainer overbet exists and is bigger than the model alone captures
Mike Smith on a 15-1 took it to 5-1 (Derby 2026). Bob Baffert tax took a 50-1 to 26-1. **For known-name pairings (Velazquez, Smith, Castellano, Baffert, Pletcher), expect public-money inflation of 1.15–1.5×.** The live-odds layer reveals this directly; don't try to estimate it ex ante from static factors.

### 3. AE-activated horses are real starters
When scratches activate an AE, drop the AE penalty multiplier. Live odds presence is the activation signal. Failing to do this cost us the show position in the Derby trifecta (Ocelli, 70-1, AE-activated, ran 3rd). Bug fixed, principle preserved.

### 4. "Sensitivity scan ROCK SOLID" ≠ "model is right"
Sensitivity tells you the answer is *stable under weight perturbation*. It doesn't tell you the weights are *correct*. Further Ado was tagged 100% bet rate across 200 perturbations and finished out of the money. **Treat sensitivity as a NECESSARY but not SUFFICIENT condition for a high-confidence pick.**

### 5. Top-overlay horses deserve to be top-of-trifecta
Asymmetry rule: if a horse is one of your top cardinal/rank overlays (model says bet to win), key it on top of trifectas too. Not just exactas. The constraint-first thinking that says "tri budget is small, skip" leaves $5,625 on the table.

### 6. Bankroll is a scalar, not a structural constraint
The right portfolio shape is determined by edge analysis. Bankroll determines stake size, not which bets are in. Optimize first; scale second.

### 7. Story matters; surface it
Biographical features (first-female-trainer, returning suspended trainer, Hall-of-Fame jockey at age 60) predict public-money flow AND make the bet a memorable story. Cherie DeVaux's first was already in `field.csv` — we just didn't surface it in the writeup. Future races: lead with the story, not just the math.

### 8. Beware Whitehead's Misplaced Concreteness
The Beyer figure is an *abstraction* of speed, not speed itself. Plackett-Luce is an *abstraction* of the ordering process, not the actual race. Sensitivity scan is an *abstraction* of robustness, not truth. Each abstraction is useful exactly to the extent we remember it's an abstraction. **Always ask: what is the model not seeing?**

## Per-race entries

- [`2026-kentucky-derby.md`](2026-kentucky-derby.md) — the founding instance. Picked the winner. 6.12× return.
- `2026-preakness.md` — TBD post-race May 16
- `2026-belmont.md` — TBD post-race June 6
