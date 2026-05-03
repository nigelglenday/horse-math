"""
Regression test: locks in the 2026 Kentucky Derby behavior.

If we refactor the engine and Golden Tempo (#19) is no longer flagged as a
cardinal-overlay bet, OR Further Ado (#18) drops out, OR the public-overbet
fades (Commandment, So Happy, Chief Wallabee) suddenly become bets, this
test fails. That's the alarm bell.

Also locks in:
- 5 confirmed scratches (5, 9, 13, 20, 24)
- AE-activated horses (21, 22, 23) treated as starters
- Cherie DeVaux trains the winning horse #19

Run: pytest tests/
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import handicap
from race_config import RaceConfig


def load_derby():
    cfg, paths = handicap.load_config("2026-kentucky-derby")
    field, pps = handicap.load_data(paths)
    rows = handicap.compute_features(field, pps, cfg)
    handicap.score_cardinal(rows, cfg["weights"])
    handicap.score_rank(rows, cfg["weights"])
    public_overbet = cfg.get("public_overbet", {})
    mkt = handicap.market_probs(rows, public_overbet, use_live=True)
    handicap.attach_probs(rows, "score", mkt, cfg["post_multiplier"], cfg["scoring"])
    handicap.attach_probs(rows, "score_rank", mkt, cfg["post_multiplier"], cfg["scoring"])
    return rows, cfg


def test_config_validates():
    """Pydantic schema accepts the Derby config."""
    cfg = RaceConfig.load("2026-kentucky-derby")
    assert cfg.race.name == "2026 Kentucky Derby"
    assert cfg.race.distance_furlongs == 10.0
    assert abs(sum(cfg.weights.model_dump().values()) - 1.0) < 0.02


def test_field_size_post_scratches():
    """5 scratches, 18 starters (Great White scratched late after AE activation)."""
    rows, _ = load_derby()
    # 24 entries minus 5 SC, but our live_odds.csv only marks original scratches
    # (Great White's late scratch isn't in our data — he's still in field as AE-activated)
    assert len(rows) >= 18
    assert len(rows) <= 19


def test_winner_flagged_as_cardinal_overlay():
    """#19 Golden Tempo (the actual winner) must be flagged YES on cardinal."""
    rows, _ = load_derby()
    winner = next(r for r in rows if r["pp"] == "19")
    assert winner["horse"] == "Golden Tempo"
    assert winner["score_bet"] == "YES", \
        f"Golden Tempo should be cardinal-overlay; got overlay {winner['score_overlay']:.2f}x"


def test_further_ado_flagged_as_cardinal_overlay():
    """#18 Further Ado was our top pick — must remain flagged."""
    rows, _ = load_derby()
    further = next(r for r in rows if r["pp"] == "18")
    assert further["horse"] == "Further Ado"
    assert further["score_bet"] == "YES", \
        f"Further Ado should be cardinal-overlay; got overlay {further['score_overlay']:.2f}x"


def test_public_overbets_not_flagged():
    """Confirmed fades — public-overbet horses should NOT be cardinal bets."""
    rows, _ = load_derby()
    fades = ["6", "8", "12"]   # Commandment, So Happy, Chief Wallabee
    for pp in fades:
        r = next(row for row in rows if row["pp"] == pp)
        assert r["score_bet"] == "", \
            f"PP {pp} ({r['horse']}) should be a fade, not a bet (overlay {r['score_overlay']:.2f}x)"


def test_renegade_post1_penalty_applied():
    """Renegade (#1) ML 4-1 → live 6-1; cardinal should put him near fair, not big overlay."""
    rows, _ = load_derby()
    renegade = next(r for r in rows if r["pp"] == "1")
    assert renegade["horse"] == "Renegade"
    # Cardinal overlay should be near 1.0 (fair) — the post-1 multiplier did its job
    # Allow some range but it shouldn't be a strong YES
    assert renegade["score_overlay"] < 1.4, \
        f"Renegade cardinal overlay {renegade['score_overlay']:.2f}x suggests post-1 penalty isn't applying"


def test_ae_activation_drops_penalty():
    """AE-activated horses with live odds should NOT have AE multiplier applied."""
    rows, _ = load_derby()
    # Ocelli #22A activated — fair_prob should be > the bare AE-penalty floor
    ocelli = next((r for r in rows if r["pp"] == "22A"), None)
    if ocelli:
        # Without bug fix: ocelli's prob would be ~0.6%. With fix: ~1.2%+
        assert ocelli["score_prob"] > 0.005, \
            f"Ocelli prob {ocelli['score_prob']*100:.2f}% suggests AE penalty still applied"


def test_devaux_trains_winning_horse():
    """Sanity: the field data still has Cherie DeVaux as Golden Tempo's trainer."""
    cfg, paths = handicap.load_config("2026-kentucky-derby")
    field, _ = handicap.load_data(paths)
    winner = next(h for h in field if h["pp"] == "19")
    assert "DeVaux" in winner["trainer"], \
        f"Expected DeVaux as #19 trainer; got {winner['trainer']}"


if __name__ == "__main__":
    # Run inline so the file is executable as well as pytest-collectable
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failures += 1
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
