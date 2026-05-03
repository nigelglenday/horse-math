# Architecture

How the system fits together. Read this if you want to understand how a race goes from PDF to ticket.

## System diagram

```mermaid
flowchart TD
    subgraph Inputs["Per-race inputs (data/races/&lt;slug&gt;/)"]
        CFG[config.toml<br/>weights, post bias,<br/>prep scoring, sources]
        FIELD[field.csv<br/>one row per starter]
        PP[past_performances.csv<br/>prior race lines]
        LIVE[live_odds.csv<br/>tote snapshot + scratches]
        EXAP[exacta_probables.txt<br/>24x24 grid from Xpressbet]
        TRIP[trifecta_probables.txt<br/>optional, format: i-j-k payout]
    end

    subgraph Engine["Race-agnostic engine (src/)"]
        H[handicap.py<br/>11-feature softmax<br/>+ post multiplier]
        S[sensitivity.py<br/>200-trial weight perturbation]
        EX[exacta.py<br/>Harville fair vs probables]
        TR[trifecta.py<br/>Plackett-Luce<br/>actual or synthesized payouts]
        P[portfolio.py<br/>Kelly + satellite + heuristics]
        CH[charts.py<br/>4 PNGs per race]
        FO[fetch_odds.py<br/>source helper]
    end

    subgraph Outputs["Per-race outputs (data/races/&lt;slug&gt;/)"]
        OV[overlays.csv<br/>cardinal + rank fair odds]
        EXO[exacta_overlays.csv]
        TRO[trifecta_overlays.csv]
        PO[portfolio.csv<br/>final sized ticket]
        FIG[figures/&lt;slug&gt;/*.png]
    end

    CFG --> H
    FIELD --> H
    PP --> H
    LIVE --> H

    H --> OV
    OV --> S
    OV --> EX
    OV --> TR
    OV --> P
    OV --> CH

    EXAP --> EX
    EXAP --> P
    TRIP --> TR
    TRIP --> P
    LIVE --> CH

    EX --> EXO
    TR --> TRO
    P --> PO
    CH --> FIG

    Human[👤 Human judgment] -.->|reads + adjusts| PO
    Wisdom[learnings/index.md] -.->|priors| Human
```

## Three layers of wagering

The portfolio module composes three layers in parallel. Each has a different epistemological status — none collapses into another.

```mermaid
flowchart LR
    Bankroll(["💵 Bankroll"]) --> L1
    Bankroll --> L2
    Bankroll --> L3

    L1["**Layer 1: Kelly Core**<br/>variance-optimal stakes<br/>full Kelly × kelly_fraction<br/>per positive-EV bet"]
    L2["**Layer 2: Satellite**<br/>minimum-stake spread<br/>across high-EV combos<br/>Kelly says skip"]
    L3["**Layer 3: Heuristics**<br/>--top-pick-wheel<br/>--longshot-scan<br/>captures lottery upside"]

    L1 --> T(["🎫 Final Ticket"])
    L2 --> T
    L3 --> T

    H["👤 Human Judgment<br/>story / live context /<br/>risk tolerance"] -.->|overrides| T
    W["📚 learnings/index.md<br/>cross-race priors"] -.->|informs| H
```

### Why three layers, not one

- **Kelly alone** is variance-optimal but under-deploys capital. With our edge sizes on a Derby, quarter-Kelly suggests $3 of $85 — leaving 96% of the bankroll idle. Wrong question for a one-day-per-year race.
- **Satellite alone** spreads thin across high-EV-low-prob combos. Lots of $0.50 bets on synthesized-EV combos that are mostly false positives.
- **Heuristics alone** are unprincipled — they capture lottery upside but ignore variance. Cargo-culting if not anchored in math.
- **All three together**: Kelly variance-manages the core, satellite captures positive-EV combos individually too small for Kelly, heuristics enforce specific structural rules (top-pick wheel, longshot scan) that operationalize human pattern recognition.

Validated on Derby 2026: the 3-layer ticket would have captured **96% of the actual hand-tuned upside** ($418 of $435), entirely systematically.

### Why human judgment as a fourth implicit layer

The human reads the texture of the day:
- Story features (first-female-trainer, comeback narrative) the model surfaces but doesn't weight
- Track bias on the day (rail dead, closers cooked) that becomes obvious in earlier races
- Risk tolerance specific to the day ("I want exposure to a lottery hit on this one")
- Errors the model is making *right now* that haven't been generalized into config yet

The model produces a high-quality default ticket. The human owns the final decision. **Always.**

## Module reference

| Module | Reads | Writes | Purpose |
|---|---|---|---|
| `handicap.py` | config.toml, field.csv, past_performances.csv, live_odds.csv | overlays.csv | 11-feature softmax → cardinal & rank win probs, with post-1 multiplier and AE-fix |
| `sensitivity.py` | overlays.csv (via handicap functions) | stdout table | 200 trials with weights perturbed ±20%; tags overlays ROCK SOLID / Robust / Marginal / Fragile |
| `exacta.py` | overlays.csv, exacta_probables.txt | exacta_overlays.csv | Harville fair P(i,j) vs market; EV per $1; key-wheel suggestions |
| `trifecta.py` | overlays.csv, optional trifecta_probables.txt | trifecta_overlays.csv | Plackett-Luce fair P(i,j,k); actual payouts if available, else synthesized |
| `portfolio.py` | overlays.csv, exacta_probables.txt, optional trifecta_probables.txt | portfolio.csv | Three-layer ticket: Kelly core + satellite + heuristic wheels/scans, scaled to bankroll |
| `charts.py` | overlays.csv, live_odds.csv, past_performances.csv | analysis/figures/&lt;slug&gt;/*.png | 4 PNGs: overlay scatter, three-way prob bars, odds movement, Beyer trajectory |
| `fetch_odds.py` | config.toml | stdout instructions | Reads [live_odds_source]; for JS-rendered, prints WebFetch instructions; for static, attempts fetch |

## Race-day workflow

```mermaid
sequenceDiagram
    autonumber
    participant Human
    participant Equibase as Equibase PP
    participant Tote as Tote board
    participant Engine as Engine (src/)
    participant Repo

    Note over Human,Equibase: Tuesday before race (entries published)
    Human->>Equibase: Pull PP PDF
    Human->>Repo: parse → field.csv + past_performances.csv
    Human->>Repo: populate config.toml ft_blinkers + barn_pick rules

    Note over Human,Tote: Race day, T-3h
    Human->>Tote: Pull live odds (1st snapshot)
    Human->>Repo: paste → live_odds.csv
    Human->>Engine: handicap → sensitivity → exacta → charts
    Engine->>Human: overlay table, sensitivity flags

    Note over Human,Tote: Race day, T-30min
    Human->>Tote: Pull live odds (2nd snapshot, capture late drift)
    Human->>Tote: Pull exacta probables from Xpressbet
    Human->>Repo: update live_odds.csv + exacta_probables.txt
    Human->>Engine: portfolio --target-spend $X --top-pick-wheel $Y --longshot-scan $Z
    Engine->>Human: sized ticket

    Human->>Human: review against learnings/index.md priors
    Human->>Tote: place bets

    Note over Human,Repo: Post-race
    Human->>Repo: append result section to readouts
    Human->>Repo: write learnings/&lt;slug&gt;.md (extracted wisdom)
    Human->>Repo: freeze case study at analysis/case-studies/&lt;slug&gt;/
```

## What's race-specific vs race-agnostic

| Lives in race config (per-race tunable) | Lives in src/ (race-agnostic) |
|---|---|
| Distance, surface, field cap | Beyer scoring formula |
| Post-position multipliers (CD ≠ Pimlico ≠ Belmont) | Trip adjustment from comments |
| Prep-race weighting (FlaDerby for KD, KD for Preak) | Softmax + Harville + Plackett-Luce math |
| Equipment changes list (FT blinkers per draw) | Sensitivity scan |
| Barn-pick rules (specific to entries) | Charts framework |
| "Story" bonuses (DeVaux first, etc) | Trainer/jockey lookup tables (in config; race-specific values) |
| Feature weights (tuned per race type) | Portfolio construction (Kelly + satellite + heuristics) |
| Live-odds and probables source URLs | Source-agnostic CSV ingestion |
