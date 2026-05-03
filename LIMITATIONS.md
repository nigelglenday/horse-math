# Limitations

Honest disclaimers about what this project does and does not establish. Read first if you're considering applying the methodology in production or evaluating its rigor.

## The headline result is N=1

The model picked the 2026 Kentucky Derby winner (Golden Tempo) and the $85 ticket cashed for $520. **One race is one observation.** It could be skill. It could be luck. There is no way to distinguish those from a single result.

Claims of "the model picked the winner" are descriptive of one outcome, not evidence of measurable edge. To claim measurable edge you would need:

- A held-out test set of historical races, with a model fit on a separate training set
- Walk-forward validation across many years and tracks
- Statistical comparison of in-sample vs out-of-sample performance
- Confidence intervals on win probability and P&L

None of those exist here yet.

## Weights are hand-set priors, not MLE-fit

The 11 feature weights in each `config.toml` are subjective priors based on horseplaying lore (Beyer figures matter most, Florida Derby is a strong prep, post 1 is a graveyard at CD). They are not estimated from data. They have not been fit to historical race outcomes via maximum likelihood, ridge regression, or any other principled procedure.

A real Bayesian model would put priors on each weight, fit a posterior on historical data, and produce credibility intervals on win probability. That is the v3 project. Until then, the weights are *arguments*, not *measurements*.

## The sensitivity scan is self-consistency, not validation

`src/sensitivity.py` perturbs each weight by 20% across 200 trials and tags overlays as ROCK SOLID, Robust, Marginal, or Fragile. This is a robustness check on the *output stability under weight perturbation*. It is not:

- Cross-validation against held-out data
- A test of whether the weights are correct
- Statistical validation of the model's predictive accuracy

The 2026 Derby itself proved the limit of this approach. Further Ado was tagged ROCK SOLID across 200 perturbations and finished out of the money. The label means "the answer is stable to which weights you pick"; it does not mean "the answer is right."

## `src/fit_weights.py` is scaffolding, not a working module

The file exists to scaffold the v3 historical-fitting workflow. It imports scikit-learn and outlines the data flow. It does nothing actionable yet because there is no `data/races/*/result.csv` corpus of historical Derbies in the same schema. When such a corpus exists, the choice of `sklearn.LogisticRegression` would also need revisiting; for race-conditional choice modeling with race fixed effects, `statsmodels.MNLogit` or `pylogit` is more appropriate than vanilla logistic regression.

## "Three-layer wagering" is design pragmatism, not epistemology

The Kelly + satellite + heuristics structure works empirically. It captured 96% of the hand-tuned Derby ticket's upside in a *retrospective* simulation built after seeing the result. That number is suggestive, not predictive. The framing in the docs uses words like "epistemological status" and "Misplaced Concreteness" that are rhetorically dressed up. Treat the structure as a useful organizing pattern, not a philosophical claim.

## Trip adjustment is heuristic

`trip_adj_from_comment()` parses chart-caller comments for keywords ("4w", "steadied", "ridden out") and adds integer adjustments to the raw Beyer figure. The adjustment magnitudes (+1 per path wide, +2 for trouble, +2 for "in hand") are heuristic. They reflect a reading of Beyer's *Picking Winners* but have not been calibrated against actual subsequent performance.

## Plackett-Luce assumes IIA

The exacta and trifecta probabilities use Harville (Plackett-Luce) which assumes Independence of Irrelevant Alternatives: P(j places | i wins) = p_j / (1 - p_i), proportionally. This ignores running-style and pace-fit interactions on placement specifically. A confirmed front-runner whose only win conditions involve getting the lead has a different placement profile than the win pool implies. The 2026 Derby caveat about Litmus Test underneath everything is a real-world example of where this assumption breaks.

## Public-overbet detection comes from live odds

When live odds are available, public-overbet biases are revealed directly by the takeout-stripped market probabilities. The static `[public_overbet]` factors in the config are fallbacks for when live data is missing; they are estimates of how much the public will pay extra for star-jockey/star-trainer pairings, not measurements.

## Pari-mutuel pools self-correct

Even if everything else were rigorous, the basic dynamic of pari-mutuel betting is that as a model becomes popular, its picks shorten in price and the edge erodes. This is not a critique of methodology but a constraint on scale. Edge that exists because the model is unread does not survive being widely read.

## What would change this document

- Building a corpus of 50+ historical Derby PPs in the same schema, fitting weights via conditional logit, and reporting out-of-sample performance: removes the "weights are hand-set" caveat
- Doing the same exercise for Preakness and Belmont: removes the N=1 caveat for those races specifically
- Cross-validating the trip-adjustment magnitudes against subsequent-race performance: removes the "trip adjustment is heuristic" caveat
- Real-world betting performance over 50+ races with consistent methodology: provides outcome data, though selection bias and survivorship will still apply

## Net read

The methodology is **shaped correctly**. The math is right. The engineering is clean. What's missing is the *empirical grounding* that turns a defensible architecture into a measured edge. Until that grounding exists, treat the project as a public R&D log of a horseplayer's analytical method, not as a validated quantitative system.
