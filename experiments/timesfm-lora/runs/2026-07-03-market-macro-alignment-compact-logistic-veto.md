# Compact-Alignment Logistic Veto Surface

Date: 2026-07-03

## Problem Framing

The previous fold-utility run showed that selection-only repair cannot solve
the router tradeoff. It reduced validation fold regressions but lost final
exposure and hurt final holdout.

This run changes the logistic veto feature surface instead. The candidate gets
extra no-leak prediction/context alignment features already present in the
router rows:

```text
feature_surface = alignment-compact
```

The goal was to help the model recognize why cut3750 and cut4000 regress
without just reordering existing base-surface candidates.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--feature-surface base
--feature-surface alignment-compact
--feature-surface alignment-risk
```

The tested surface was:

```text
alignment-compact
```

The feature is no-leak because it uses runtime prediction/context alignment
features available before the routing decision. It does not use validation or
final labels.

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-feature-surface-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

No-series compact alignment:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --feature-surface alignment-compact \
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
  --output reports/router-logistic-veto-alignment-compact-abstention-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

No-series compact alignment with fold utility:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective fold-utility \
  --feature-surface alignment-compact \
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
  --output reports/router-logistic-veto-alignment-compact-fold-utility-abstention-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series compact alignment:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --include-series \
  --feature-surface alignment-compact \
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
  --output reports/router-logistic-veto-alignment-compact-abstention-time-bin-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Feature surface | Objective | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---|
| no-series previous | base | combined | 10 | 0 | 81 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | alignment-compact | combined | 7 | 0 | 33 | -0.0000297337 | not_promotable |
| no-series | alignment-compact | fold-utility | 7 | 0 | 33 | -0.0000297337 | not_promotable |
| include-series | alignment-compact | combined | 0 | 0 | 0 | 0.0 | not_validated_no_future_exposure |

## Selected No-Series Compact Candidate

```text
l2: 0.1
probability_threshold: 0.6
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
feature_surface: alignment-compact
abstention_mode: positive-quantile
positive_probability_quantile: 0.5
```

Validation:

```text
combined_metric_delta: +0.0003324972
combined_changed_windows: 81
fold_metric_deltas: -0.0000452110, -0.0000121337, +0.0010548362
fold_changed_windows: 44, 9, 28
fold_metric_regressions: 2
training_brier: 0.2202695484
```

Final holdout:

```text
changed_windows: 33
benefit_signal_windows: 33
confidence_abstained_windows: 0
metric_delta: -0.0000297337
negative_series: 2 -> 2
promotion_verdict: not_promotable
```

## Interpretation

Fact: Compact alignment reduces no-series robust-pass candidates from 10 to 7.

Fact: The selected compact candidate has a slightly better training Brier than
the previous base candidate, but worse final holdout transfer.

Fact: Final exposure drops from 81 to 33 changed windows and final metric delta
turns negative.

Fact: Include-series compact alignment has no robust-pass candidates and zero
final exposure.

Inference: Compact alignment features help fit the training/validation surface
slightly, but the added feature surface does not transfer to final holdout in
the logistic abstention router.

Recommendation: Keep the base no-series positive-quantile candidate as the
current best diagnostic checkpoint. Do not continue expanding alignment
features in this logistic-veto path unless a new training target changes the
weak-fold behavior.
