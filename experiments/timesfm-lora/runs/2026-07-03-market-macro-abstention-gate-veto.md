# Positive-Quantile Abstention Gate

Date: 2026-07-03

## Problem Framing

The margin-weighting run showed that scalar sample weights can make the router
more conservative, but they can also collapse final holdout exposure to zero.

This run changes the router interface instead of adding another loss weight.
It separates two decisions:

```text
1. Does the logistic model predict fallback benefit?
2. Is the probability confident enough to act?
```

The second decision is calibrated only from training-split positive examples.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--abstention-mode positive-quantile
--positive-probability-quantile 0.5
--positive-probability-quantile 0.75
--positive-probability-quantile 0.9
```

The action rule becomes:

```text
probability >= probability_threshold
and
probability >= training_positive_probability_quantile
```

Reports now split action counts into:

```text
benefit_signal_windows
confidence_abstained_windows
changed_windows
```

This distinguishes "the model saw possible fallback benefit" from "the router
actually changed the selected adapter."

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-abstention-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
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
  --output reports/router-logistic-veto-abstention-gate-time-bin-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
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
  --output reports/router-logistic-veto-abstention-gate-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Worst-fold no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective worst-fold \
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
  --output reports/router-logistic-veto-abstention-gate-time-bin-worst-fold-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series diagnostics:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
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
  --output reports/router-logistic-veto-abstention-gate-time-bin-strict-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
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
  --output reports/router-logistic-veto-abstention-gate-time-bin-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Objective | Candidate count | Robust-pass | Strict-positive | Quantile | Final changed | Benefit signals | Abstained | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| default smoke | strict | combined | 28 | 5 | 0 | n/a | n/a | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | combined | 600 | 10 | 0 | n/a | n/a | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 600 | 10 | 0 | 0.50 | 81 | 82 | 1 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | robust | worst-fold | 600 | 10 | 0 | 0.75 | 43 | 82 | 39 | -0.0000162348 | not_promotable |
| include-series | strict | combined | 600 | 4 | 0 | n/a | n/a | n/a | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 600 | 4 | 0 | 0.50 | 1 | 1 | 0 | +0.0000001652 | not_validated_final_underexposed |

## Best No-Series Diagnostic

```text
l2: 0.1
probability_threshold: 0.5
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
abstention_mode: positive-quantile
positive_probability_quantile: 0.5
```

Validation:

```text
combined_metric_delta: +0.0003628808
combined_changed_windows: 144
fold_metric_deltas: -0.0000463270, -0.0000596526, +0.0011946219
fold_changed_windows: 76, 35, 33
fold_metric_regressions: 2
benefit_signal_windows: 189
confidence_abstained_windows: 45
```

Training probability summary:

```text
positive_p50_probability: 0.5284044747
positive_p75_probability: 0.6214999260
positive_p90_probability: 0.7001317452
negative_p90_probability: 0.6118839743
```

Final holdout:

```text
changed_windows: 81
benefit_signal_windows: 82
confidence_abstained_windows: 1
abstention_probability_gate: 0.5045429922
metric_delta: +0.0000115310
negative_series: 2 -> 2
promotion_verdict: incremental_positive_but_below_fallback
```

## Interpretation

Fact: Positive-quantile abstention gives the strongest no-series robust final
diagnostic in the recent logistic-veto sequence: 81 final changed windows and
positive final metric delta.

Fact: Strict validation still rejects every candidate because fold metric
regressions remain.

Fact: Worst-fold selection chooses a stricter quantile and fails final holdout.

Fact: Include-series still collapses to 1 final changed window and remains
underexposed.

Inference: Separating fallback-benefit prediction from confidence gating is a
better router interface than scalar sample-weight tweaks, but the current gate
still does not satisfy promotion criteria.

Recommendation: Continue from the no-series positive-quantile path, but do not
publish it. The next step should target the two weak validation folds directly,
not add more include-series identity features.
