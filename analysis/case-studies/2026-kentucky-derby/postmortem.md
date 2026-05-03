# 2026 Kentucky Derby, Post-Mortem

**Race winner: #19 Golden Tempo · trained by Cherie DeVaux · ridden by Jose Ortiz · paid $48.24 to win.**

**The model picked it. We bet it. We hit.**

---

## The Result

| Finish | # | Horse | Jockey | Trainer | Final Odds |
|---|---|---|---|---|---|
| **1** | **19** | **Golden Tempo** | **Jose Ortiz** | **Cherie DeVaux** | **23/1** |
| 2 | 1 | Renegade | Irad Ortiz Jr. | Todd Pletcher | 5/1 |
| 3 | 22 | Ocelli | Tyler Gaffalione | D. Whitworth Beckman | 70/1 |
| 4 | 12 | Chief Wallabee | Junior Alvarado | William Mott | 7/1 |
| 5 | 7 | Danon Bourbon (JPN) | Atsuya Nishimura | Manabu Ikezoe | 12/1 |
| 6 | 11 | Incredibolt | Jaime Torres | Riley Mott | 23/1 |
| 7 | 6 | Commandment | Luis Saez | Brad Cox | 6/1 |
| 8 | 10 | Wonder Dean (JPN) | Ryusei Sakai | Daisuke Takayanagi | 26/1 |
| OOM | 18 | **Further Ado** | John Velazquez | Brad Cox | 6/1 |
| OOM | 4 | Litmus Test | Martin Garcia | Bob Baffert | 27/1 |
| OOM | 8 | So Happy | Mike Smith | Mark Glatt | 5/1 |
| OOM | 15 | Emerging Market | Flavien Prat | Chad Brown | 8/1 |
| ... | | (others out of money) | | | |
| SCR | 5, 9, 13, 20, 21, 24 | (six scratches total) | | | |

**Final field: 18 starters** (one more late scratch, #21 Great White, than we had in our last odds pull, which had it as 19).

## The History

**Cherie DeVaux became the first female trainer to win the Kentucky Derby in 152 runnings.** Owner Daisy Phipps Pulito (Phipps Stable, co-owner with St. Elias Stable) is also a woman. The first woman-trained Derby winner is also a woman-owned Derby winner.

The model picked it for the math reasons, Golden Tempo's 95 Beyer in the LaDerby with a wide trip, closer style fit for the projected meltdown pace, J. Ortiz upgrade in the irons, public hadn't found him at 25-1. The model didn't know the *story* it was backing, and that's a real miss, see lessons below.

## Tally

| Bet | Stake | Payout | Win |
|---|---|---|---|
| **WIN #19 Golden Tempo** ($48.24/$2) | $10 | $24.12 × 10 | **$241.20** |
| **EXACTA 19-1** ($139.43/$1, we had $2) | $2 | $139.43 × 2 | **$278.86** |
| WIN #18 Further Ado | $20 |, | $0 |
| WIN #1 Renegade | $10 |, | $0 |
| 18 KEY 4, 19, 1 ($3 each) | $9 |, | $0 |
| 4 KEY 1, 6, 8 ($2 each) | $6 |, | $0 |
| 1 KEY 3, 4, 8, 14, 18, 19 ($1 each) | $6 |, | $0 |
| 19 KEY 18 ($2), ran 19-1, not 19-18 | $2 |, | $0 |
| BOX 18-19 | $4 |, | $0 |
| BOX 4-18 ($5 boost) | $10 |, | $0 |
| Trifectas (1 / X / X and 4 / X / X) | $6 |, | $0 |

**Gross: $520.06 · Cost: $85 · Net: +$435.06 · Return: 6.1×**

The token cost question from the morning post: net winnings clear it by orders of magnitude.

## What the model got right

1. **Picked Golden Tempo as a top overlay.** Sensitivity scan tagged him ROCK SOLID, 100% bet rate across 200 weight perturbations, overlay range 1.85–2.21x. Won the race at 25-1 with a fair price our model put near 6%. Cleanest call of the day.

2. **Renegade in the place spot, post-1 risk priced correctly.** The post-1 multiplier (Renegade 0.60×) we added mid-build dropped his cardinal overlay below the bet threshold for win. We kept him in the exacta picture as a placer. He ran a courageous 2nd from the rail, exactly what the math said: not the winner, but in the money. The 19-1 exacta only existed because we keyed Golden Tempo over Renegade.

3. **Faded the chalk and they died.** All three of our "confirmed fades", #6 Commandment (7th), #8 So Happy (out of money entirely), #12 Chief Wallabee (4th), failed to win, and So Happy was the heaviest single overbet on the board at 5-1 live. The public-overbet methodology was vindicated cleanly.

4. **Ortiz vs Ortiz exacta.** Jose Ortiz on Golden Tempo, big brother Irad Ortiz Jr on Renegade. The model didn't predict this *as a story* but the math caught the right brothers in the right slots.

## What the model got wrong

1. **#18 Further Ado as our $20 top win bet, out of the money entirely.** This was the largest single mistake of the day. The cardinal model loved him for the 109 trip-adjusted Beyer and the Cox barn-pick rule (Velazquez ride). The sensitivity scan tagged him ROCK SOLID. He didn't show up. Possible explanations: he never broke clean, he didn't get a closer's trip, or the pace meltdown didn't fully materialize for the closing kick. Either way, "rock solid in sensitivity" doesn't mean "rock solid in reality", sensitivity scans tell you about robustness to weight choice, not about whether the weights themselves are right.

2. **The trifecta structure missed by one key.** Tri came in **19-1-22** paying **$5,625 on $0.50.** We had two trifecta wheels: `1 / 4-18-19 / 4-18-19` and `4 / 1-18-19 / 1-18-19`. Neither had #19 *on top.* If we'd added a single `$0.50 tri 19 / 1 / ALL` wheel for $7, we'd have caught $5,625. The asymmetric upside of keying our biggest overlay on top of trifectas was right there and we missed it.

3. **The AE penalty bit us twice.** Our model applies a 0.50 multiplier to AE horses on the assumption they "won't run unless a starter scratches." When five starters scratched, four AEs *did* run, and one of them (#22 Ocelli, 70-1, with Tyler Gaffalione picking up the mount after his original ride Fulleffort scratched) finished 3rd. We had Ocelli at 0.7% fair prob. He should have been treated as a regular starter once his AE status activated. **This is a clean bug to fix in `f_post()`.**

4. **The Litmus Test home-run combos** ($588 and $483 boosted exactas) were the single biggest dollar lines on the ticket and Litmus Test never threatened. The Baffert tax we tried to exploit was real but didn't manifest in performance. Both Baffert horses (#4 Litmus Test, #14 Potente) finished off the board. **Bob Baffert's first Derby back from suspension was a flop.**

5. **Cox barn-pick rule misfired.** The hand-coded "Velazquez on Further Ado = the tell" rule contributed materially to over-staking #18. The barn went 0-for-2 on the day (Commandment 7th, Further Ado way back). One race is one race, but the rule deserves audit.

## The story we missed

When Nigel's wife asked this morning about "a filly or a lady jockey," I gave her a flat "no" instead of surfacing **Cherie DeVaux as a potential first-female-trainer Derby winner.** Cherie was already in `field.csv`. I had the data and I treated it as just another row. The model picked the historic horse for math reasons; the writeup didn't tell that story to the people who would have cared most.

**Action item for the next build:** add a "barrier-breaking" / "story" tag to the field schema. Surface human-interest signals alongside numerical ones. The model can be right about the math and still flunk the storytelling.

## Lessons for v2

1. **Optimize the portfolio first, scale to bankroll second.** This is the biggest methodological mistake of the day, and it explains the asymmetry in #2 below. We started with `$85` and packed bets inside it. We should have:
   1. Listed every positive-EV bet the model identified (every win, exacta, trifecta combo where `our_P × payout > 1`).
   2. Sized each at fractional Kelly (~0.25× full Kelly to dampen variance and absorb estimation error).
   3. Summed the stakes, call it the *ideal portfolio cost*.
   4. If ideal cost ≤ bankroll, place at Kelly stakes and hold the rest in cash.
   5. **If ideal cost > bankroll, scale every bet proportionally by `bankroll / ideal_cost`.**

   This preserves the *shape* of the optimal portfolio (relative weights between bets) while letting bankroll act as a pure scalar. Bankroll is a multiplier, not a structural constraint.

   Applied to today: a `19 / X / X` trifecta wheel would have been included by construction because Golden Tempo had a robust positive Kelly fraction in the win pool, and the corresponding tri combos had positive Kelly given Harville place probabilities × the wide tri payouts. Even at $0.50 per combo, the bet would have had its rightful seat. Instead, constraint-first thinking treated "small positive Kelly bet" as "skip if budget tight" and we missed $5,625.

   v2 needs `src/portfolio.py` that computes Kelly for every candidate bet and scales to bankroll.

2. **If a horse is a top cardinal overlay, key it on top of trifectas, not just exactas.** We protected #1 and #4 with tri wheels; we didn't protect #19 the same way despite it being our second-strongest overlay. This was the constraint-first thinking from #1 manifesting as structural inconsistency in our bet shape.

3. **AE-activated horses should lose the AE penalty.** Treat them as regular starters once they're confirmed to run. Live odds are the signal. Clean bug to fix in `f_post()`.

4. **"Sensitivity scan robust" ≠ "model right."** Sensitivity tells you the answer is stable under weight perturbation. It doesn't tell you the weights are correct. Need separate validation against historical Derbies. Further Ado was tagged ROCK SOLID and finished out of the money.

5. **Story features matter.** Add owner gender, trainer firsts, jockey age/longevity, pedigree narratives to the data layer. The model's job is to score, but the *bet's* job is to be one we'd be proud to talk about either way. Missing the DeVaux first was an analytical miss as much as a wife-asking miss, those biographical features also predict things like late tote action ("the casual money chases stories").

6. **Bigger picks deserve bigger asymmetric coverage.** The exacta boost on 4-18 ($5) was sized like a bet on belief in Litmus Test. The win bet on #19 ($10) was sized lower than a "rock solid" sensitivity result deserved. Symptom of constraint-first sizing, fixed by Lesson 1.

## Bottom line

The model picked the right horse for the right reasons and we made $435 on $85. We also missed a $5,625 trifecta that was sitting right there and over-staked our worst pick. **Net: 6.1× on bankroll. Token cost cleared with comfort.**

More importantly, the public build worked, every decision is in git history, every chart on `main`, every overlay number reproducible. Nigel's wife knows the model called the historic horse. The next iteration of this builds on a real data point instead of a thought experiment.

🐎🐎🐎
