# Fold-Utility Selection

Date: 2026-07-03

## Problem Framing

The positive-quantile abstention run produced the strongest recent no-series
diagnostic:

```text
final changed windows: 81
final metric delta: +0.0000115310
```

But strict validation still failed because the selected candidate had two
negative validation folds. This run tests whether the existing candidate pool
already contains a better fold-stability tradeoff.

The change is selection-only:

```text
selection_objective = fold-utility
```

No training labels, validation folds, or final holdout data changed.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--selection-objective fold-utility
```

Each validation score now records:

```text
negative_fold_metric_delta
fold_utility_score
```

The score is:

```text
fold_utility_score = combined_metric_delta + sum(negative fold metric deltas)
```

The ranking also prefers fewer fold metric regressions before aggregate lift.

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-fold-utility-selection-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

No-series fold-utility:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective fold-utility \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
  --abstention-mode positive-quantile \
  --positive-probability-quantile 0.5 \
  --positive-probability-quantile 0.75 \
  --positive-probability-quantile 0.9 \
  --false-positive-weight 1 \
  --false-positive-weight 2 \
  --false-positive-weight 4 \
  --false-positive-weight 8 \
  --false-positive-weight 16 \
  --probability-threshold 0.5 \
  --probability-threshold 0.55 \
  --probability-threshold 0.6 \
  --probability-threshold 0.65 \
  --probability-threshold 0.7 \
  --probability-threshold 0.75 \
  --probability-threshold 0.8 \
  --probability-threshold 0.85 \
  --probability-threshold 0.9 \
  --probability-threshold 0.95 \
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --min-final-changed-windows 20 \
  --output reports/router-logistic-veto-fold-utility-abstention-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series fold-utility:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective fold-utility \
  --include-series \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
  --abstention-mode positive-quantile \
  --positive-probability-quantile 0.5 \
  --positive-probability-quantile 0.75 \
  --positive-probability-quantile 0.9 \
  --false-positive-weight 1 \
  --false-positive-weight 2 \
  --false-positive-weight 4 \
  --false-positive-weight 8 \
  --false-positive-weight 16 \
  --probability-threshold 0.5 \
  --probability-threshold 0.55 \
  --probability-threshold 0.6 \
  --probability-threshold 0.65 \
  --probability-threshold 0.7 \
  --probability-threshold 0.75 \
  --probability-threshold 0.8 \
  --probability-threshold 0.85 \
  --probability-threshold 0.9 \
  --probability-threshold 0.95 \
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --min-final-changed-windows 20 \
  --output reports/router-logistic-veto-fold-utility-abstention-time-bin-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Objective | Robust-pass | Strict-positive | Fold regressions | Fold utility | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| no-series previous | combined | 10 | 0 | 2 | n/a | 81 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | fold-utility | 10 | 0 | 1 | +0.0001601650 | 16 | -0.0000119835 | not_validated_final_underexposed |
| include-series | fold-utility | 4 | 0 | 2 | -0.0001805617 | 1 | +0.0000001652 | not_validated_final_underexposed |

## Selected No-Series Fold-Utility Candidate

```text
l2: 0.1
probability_threshold: 0.65
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
abstention_mode: positive-quantile
positive_probability_quantile: 0.5
```

Validation:

```text
combined_metric_delta: +0.0002618032
negative_fold_metric_delta: -0.0001016381
fold_utility_score: +0.0001601650
fold_metric_deltas: -0.0001016381, +0.0000008841, +0.0008861635
fold_changed_windows: 23, 4, 23
fold_metric_regressions: 1
```

Final holdout:

```text
changed_windows: 16
benefit_signal_windows: 16
confidence_abstained_windows: 0
metric_delta: -0.0000119835
final_exposure_pass: false
promotion_verdict: not_validated_final_underexposed
```

## Interpretation

Fact: Fold-utility selection reduced validation fold metric regressions from 2
to 1 on the no-series surface.

Fact: The selected no-series candidate lost final exposure, dropping from 81
changed windows to 16.

Fact: The selected no-series candidate also flipped final metric delta from
positive to negative.

Inference: The fold-regression repair was achieved by selecting a more
conservative candidate that does not transfer to final holdout.

Recommendation: Stop selection-only fold repair for this candidate pool. The
next useful lever should modify the training target or features for the weak
folds, not just reorder existing candidates.
