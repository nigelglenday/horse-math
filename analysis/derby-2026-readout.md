# 2026 Kentucky Derby — Pre-Race Readout

**Race 12, Churchill Downs · Saturday May 2, 2026 · post 6:57 PM ET · 1¼ miles · $5M Grade I**

This is the readout the model produced ~2 hours before post. Built live with Claude Code as part of the [horse-model](../README.md) public build. Bets and reasoning recorded *before* the race, so the post-mortem can be honest.

## What changed during the day

5 horses scratched (Right to Party, The Puma, Silent Tactic, Fulleffort, Corona de Oro) — field down to **19 starters**, the sixth time in eight years the Derby has gone with under 20.

Two of those scratches (Silent Tactic and Fulleffort) were our top overlays under morning line. They evaporated. The math had to be re-run with live tote odds replacing ML.

## Where the public money went

![odds movement](figures/03_odds_movement.png)

Reading this chart:
- **Green arrows = took money** (price shortened, more public confidence)
- **Orange arrows = drifted** (price lengthened, public abandoned)

The biggest signals:
- **So Happy 15-1 → 5-1.** Mike Smith name premium. Likely overbet past fair.
- **Litmus Test 50-1 → 26-1.** Baffert tax. The morning line was wrong; the public arbitraged it.
- **Chief Wallabee 8-1 → 6-1.** Wm Mott + first-time-blinkers narrative drew money.
- **Renegade 4-1 → 6-1.** ⚠️ The favorite *drifted*. The public is avoiding the chalk.
- **Commandment 6-1 → 5-1.** Cox + perfect form took money.

The Renegade drift is the single most actionable piece of information on the day. The model still rates him near the top; the market lost faith.

## The model's read on win probability

![probabilities](figures/02_probabilities.png)

Three bars per horse: live tote (after takeout strip), our cardinal model, our rank-based model. **Where our bars stick out to the right of the market bar = overlay.**

The Renegade rank-bar (purple) is the most extreme — the model thinks he's a 35% horse and the market priced him at 11%. Cardinal model agrees less aggressively but still has him as an overlay.

The flip side: **Chief Wallabee, So Happy, and Commandment all show the market bar dominating both model bars** — those are confirmed overbets.

## Where to bet

![overlays](figures/01_overlays.png)

The bet zone is overlay ≥ 1.25x. Both methods agree on:

| Horse | Live odds | Cardinal overlay | Rank overlay | Read |
|---|---|---|---|---|
| **#1 Renegade** | 6-1 | 1.58x | **3.18x** | The drift created the bet. Both methods agree, rank is screaming. |
| **#4 Litmus Test** | 26-1 | 1.85x | 1.90x | Longshot value with first-time blinkers, Baffert overlay still real after the price move. |
| **#18 Further Ado** | 6-1 | 1.63x | 1.04x | Cardinal-only. 107 Beyer last out, Cox barn-pick (Velazquez ride). |
| **#19 Golden Tempo** | 25-1 | 1.98x | 0.66x | Cardinal-only. Public never found him. |

Confirmed fades (do NOT bet to win, candidates to bet AGAINST in exotics):
- **#8 So Happy** — public hammered him to 5-1 on Mike Smith name + cheerful name + recent SADerby
- **#12 Chief Wallabee** — heaviest single overbet on the board
- **#6 Commandment** — slight overbet, though "perfect form" narrative is real

## Form

![beyer trajectory](figures/04_beyer_trajectory.png)

The trajectory chart shows last-five-Beyers per top contender. The story: Renegade and Further Ado have ascended together to a 107 ceiling — the two clear top figs in the field. Chief Wallabee's 99 ceiling is below them. Commandment is steady but capped near 99. So Happy bounces between 90 and 100.

After trip adjustment from comments (4-wide trips, "ridden out" finishes, slipped breaks), Further Ado pushes to 109 and Renegade to 108 — still the clear top two.

## Method, in one sentence

Score each horse on 11 weighted features (trip-adjusted Beyers, projected pace fit under a meltdown thesis, class of preps won with a Florida Derby bias, manner of finish, distance fit, connections, equipment changes, post position, plus a Cox-stable barn-pick signal), softmax across the field, compare to live tote prices stripped of takeout. Bet only the overlays.

The detailed walkthrough is in [`src/handicap.py`](../src/handicap.py).

## Status

Mid-race-day. This file is the snapshot of what we're betting and why. Post-race, this writeup gets the result appended — what landed, what we got right, what we got wrong, what we'd change.

If the token spend doesn't clear the net winnings, the loss has at least been honestly logged in public.
