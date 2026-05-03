# Learnings — 2026 Kentucky Derby

The founding race. Built in five hours; picked the winner; net +$435 on $85.

For the full case study see [`analysis/case-studies/2026-kentucky-derby/`](../analysis/case-studies/2026-kentucky-derby/README.md). This file extracts the *wisdom* — the parts of the experience that don't fit cleanly into code or config and need to be carried forward as priors.

## What the model got right (and why we trust it)

- **Picked Golden Tempo at 25-1.** Sensitivity scan tagged him "ROCK SOLID" across 200 weight perturbations. The math worked.
- **Faded all three named overbets.** Mike Smith on So Happy (5-1), Cox-stable on Commandment (5-1), Mott on Chief Wallabee (7-1) — none hit the board. Public-overbet thesis vindicated.
- **Post-1 multiplier was right.** Renegade ran 2nd from the rail — exactly the model's fair-prob outcome (legitimate horse, can't win from there, places).

## What the model got wrong (and what to remember)

### Further Ado was our $20 top win bet. Out of the money.
Sensitivity said ROCK SOLID. He never showed up. Possible explanations: didn't break clean, didn't get a closer's trip, pace meltdown didn't fully materialize. We will *never* know exactly why, and that's the point. **Sensitivity scans are necessary, not sufficient.**

### Cox barn-pick rule misfired.
The hand-coded "Velazquez on Further Ado = the tell" rule contributed materially to over-staking #18. Cox went 0-for-2 on the day. The barn-pick *signal* is real (jockey assignment in a multi-entry stable IS information), but one race is one race. Audit the rule rather than removing it.

### AE penalty bit us twice.
Ocelli (#22A) ran 3rd at 70-1 with Tyler Gaffalione picking up an AE mount after his original ride scratched. Our model penalized Ocelli with a 0.50 AE multiplier. **Bug fixed:** AE-activated horses (those with live odds confirmed) lose the AE penalty.

### Story we missed.
Cherie DeVaux became the first female trainer to win the Derby in 152 runnings. Owner Daisy Phipps Pulito is also a woman. Both were already in `field.csv`. The model picked the historic horse for math reasons; the writeup didn't tell that story to the people who would have cared most. **Future writeups: surface biographical signal alongside numerical signal.**

## The methodological lesson — three layers

The single biggest mistake of the day was **constraint-first ticket construction.** We started with $85 and packed bets inside it. We should have:
1. Identified every positive-EV bet (Kelly core)
2. Filled remainder with high-EV/low-prob satellites
3. Reserved budget for top-pick wheel + longshot scan heuristics

Simulation (now possible because v2.1 supports all three layers): a 3-layer $85 ticket would have captured **96% of the actual hand-tuned upside** ($418 vs $435 actual). Pure quarter-Kelly would have captured 3% ($11). The 3-layer approach is dramatically more reliable than either pure Kelly or pure judgment.

**The trifecta we missed (19-1-22, $5,625):** even with full Kelly + actual probable payout, this combo had EV of only +$0.15 per $1. Kelly would have staked $0.001 — below any reasonable minimum. **Capturing this required the heuristic layer specifically** — `--top-pick-wheel 8` reserves $8 for `top-overlay-horse / top-3-other-fair-probs / ALL` wheels. With the new heuristic, $0.04 lands on 19-1-22 → $450 payout.

## Wagering rules to carry forward

- **Always run `--target-spend = bankroll`.** Treat bankroll as a scalar, deploy the full amount.
- **Always include `--include-tri` and `--top-pick-wheel <amount>`.** Reserve $5-10 for the top-pick wheel, no matter how the math says skip.
- **Always include `--longshot-scan <amount>`.** Reserves $5-10 for live-tote-undervalued horses as exacta placers under your top pick.
- **Sensitivity must agree with cardinal AND rank** for highest confidence. If only one method flags a horse as YES, treat as a contingent bet, not a primary stake.
- **Pull live odds at least twice** — early (T-3h, set initial baseline) and late (T-30min, capture last-minute movement). The drift between snapshots IS the public-overbet signal.

## Things to watch for in this kind of race

- **20-horse field, post 1**: 1 winner since 1975 (Ferdinand 1986). Multiplier 0.60.
- **Multi-entry stables**: jockey assignment is the tell, not the official barn statement.
- **First-time blinkers**: trainer's history matters (Mott 22% in last 365). Live odds will reveal whether the public has noticed.
- **AE horses**: when scratches activate them, they're live. Drop the AE penalty.
- **Recent Derby winner's offspring**: bloodline-narrative bets the public makes (Litmus Test sired by Nyquist). Real but variable signal.
- **Foreign shippers**: Japan + UAE + Europe runners need US-equivalent Beyer adjustment. Without that adjustment, they're effectively neutral imputed (50%).

## What this race teaches about the next one

- **Cherie DeVaux is now a Derby-winning trainer.** Her score in `[trainer_score]` should bump for Preakness/Belmont (was 55, should probably be 75+).
- **Velazquez/Cox barn-pick rule** misfired here — does NOT mean retire it, but DO weight it less aggressively than originally configured.
- **The Mott family** all underperformed (Wm Mott's Chief Wallabee 4th, Riley Mott's Albus and Incredibolt OOM and 6th). Watch the trainer scores — Riley Mott's 55 may be too generous given small sample.
- **Florida Derby winner (Commandment)** finished 7th. The FlaDerby = 100 score in the Derby config is HISTORICAL prior, not a hard rule. Worth examining whether to soften for next year.
- **The pace meltdown didn't fully materialize.** Confirmed E's were Pavlovian, Litmus Test, Six Speed, Robusta — all out of the money. The pace-fit logic correctly favored closers (Golden Tempo won), but Ocelli (3rd, 70-1) was a *closer-stalker* that the model also penalized via the AE bug. Pace logic was right; AE bug suppressed the signal on Ocelli.
