"""
Historical-Derbies weight fitting (v3 project).

Replaces the hand-set feature weights in config.toml with maximum-likelihood
estimates fit on historical race outcomes. Uses scikit-learn's
LogisticRegression in multinomial mode — equivalent to the conditional logit /
discrete-choice model that's the formal statistical underpinning of the
softmax handicap.

This is a SCAFFOLD. The fit needs a corpus of historical races in the same
schema as data/races/<slug>/{field.csv, past_performances.csv} with known
outcomes. Building that corpus is the main blocker — Equibase publishes the
data but it requires manual extraction or paid API access.

Run: python3 src/fit_weights.py --history-glob 'data/races/*/'

Once fit, weights can be written back into a race's config.toml and the
hand-set priors retired in favor of MLE estimates.
"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handicap
from race_config import RaceConfig

ROOT = Path(__file__).resolve().parent.parent


def collect_training_data(history_paths):
    """
    For each historical race, compute the feature vectors for every horse and
    flag the actual winner. Returns (X, y, race_ids) where:
      X: ndarray shape (n_horses_total, n_features)
      y: ndarray shape (n_horses_total,) — 1 if won, 0 otherwise
      race_ids: list of race slugs aligned with rows
    """
    try:
        import numpy as np
    except ImportError:
        sys.exit("Need numpy: pip install numpy (comes with scikit-learn)")

    rows_X, rows_y, rows_race = [], [], []
    feat_keys = None

    for race_dir in history_paths:
        race_slug = race_dir.name
        result_path = race_dir / "result.csv"
        if not result_path.exists():
            print(f"  skip {race_slug}: no result.csv")
            continue
        try:
            cfg, paths = handicap.load_config(race_slug)
        except SystemExit:
            print(f"  skip {race_slug}: config invalid")
            continue
        winners = set()
        for r in csv.DictReader(open(result_path)):
            if r.get("finish_pos") == "1":
                winners.add(r["pp"])
        field, pps = handicap.load_data(paths)
        scored_rows = handicap.compute_features(field, pps, cfg)
        if feat_keys is None:
            feat_keys = list(scored_rows[0]["feats"].keys())
        for r in scored_rows:
            rows_X.append([r["feats"][k] for k in feat_keys])
            rows_y.append(1 if str(r["pp"]) in winners else 0)
            rows_race.append(race_slug)

    if not rows_X:
        sys.exit("No training data found. Need data/races/*/result.csv with finish positions.")

    return np.array(rows_X), np.array(rows_y), rows_race, feat_keys


def fit(X, y, race_ids, feat_keys):
    """
    Fit conditional logistic regression — race-conditional multinomial logit.
    With one observation per (race, horse) pair, sklearn's LogisticRegression
    with class_weight='balanced' is a reasonable approximation. For true
    conditional logit with race fixed effects, use statsmodels' MNLogit or
    pylogit.
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        sys.exit("Need scikit-learn: pip install 'horse-math[fit]'")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=2000,
        solver="lbfgs",
    )
    model.fit(X_scaled, y)

    coefs = model.coef_[0]
    print("\nFitted feature coefficients (standardized):")
    for k, c in sorted(zip(feat_keys, coefs), key=lambda x: -abs(x[1])):
        print(f"  {k:<20} {c:>+8.3f}")

    # Convert standardized coefs to weights summing to 1.0 for use in config.toml
    abs_coefs = [abs(c) for c in coefs]
    total = sum(abs_coefs)
    weights = {k: float(abs(c) / total) for k, c in zip(feat_keys, coefs)}
    print("\nNormalized weights (drop into config.toml [weights]):")
    for k, w in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} = {w:.3f}")
    return weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-glob", default="data/races/*/",
                        help="Glob pattern matching historical race directories")
    args = parser.parse_args()

    history_paths = sorted(ROOT.glob(args.history_glob))
    print(f"Found {len(history_paths)} race directories:")
    for p in history_paths:
        print(f"  {p.relative_to(ROOT)}")

    X, y, race_ids, feat_keys = collect_training_data(history_paths)
    print(f"\nTraining set: {X.shape[0]} horses across {len(set(race_ids))} races, "
          f"{int(y.sum())} winners")

    if X.shape[0] < 50:
        print("\nWARNING: Small training set. Fitted weights will be unstable. "
              "Need ~20+ historical Derbies for stable estimates.")

    fit(X, y, race_ids, feat_keys)


if __name__ == "__main__":
    main()
