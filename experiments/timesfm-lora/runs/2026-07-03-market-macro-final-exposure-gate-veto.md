# Final-Exposure Logistic Veto Gate

Date: 2026-07-03

## Problem Framing

The previous time-bin logistic run exposed a promotion-hole: the include-series
robust diagnostic produced a tiny positive final metric delta, but it changed
only 1 final holdout window.

That should not count as useful evidence. A router can look good by touching
too few cases.

This run adds a final holdout exposure gate:

```text
min_final_changed_windows = 20
```

The validation exposure gate already protects model selection. This new gate
protects final promotion.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--min-final-changed-windows 20
```

Default behavior remains compatible:

```text
default min_final_changed_windows = 1
```

Final reports now include:

```text
min_final_changed_windows
final_exposure_pass
promotion_verdict
```

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-final-exposure-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
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
  --output reports/router-logistic-veto-final-exposure-gate-time-bin-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
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
  --output reports/router-logistic-veto-final-exposure-gate-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series diagnostics:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --include-series \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
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
  --output reports/router-logistic-veto-final-exposure-gate-time-bin-strict-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --include-series \
  --training-weighting time-bin-label-balanced \
  --training-time-bins 3 \
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
  --output reports/router-logistic-veto-final-exposure-gate-time-bin-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Candidate count | Robust-pass | Strict-positive | Final changed | Final exposure pass | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---|---:|---|
| default smoke | strict | 28 | 5 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | 200 | 4 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 200 | 4 | 0 | 54 | true | -0.0000143517 | not_promotable |
| include-series | strict | 200 | 2 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | 200 | 2 | 0 | 1 | false | +0.0000001652 | not_validated_final_underexposed |

## Selected No-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.55
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
training_time_bins: 3
```

Validation:

```text
combined_metric_delta: +0.0003225530
combined_changed_windows: 107
fold_metric_deltas: -0.0000673672, -0.0000484484, +0.0010834746
fold_changed_windows: 59, 18, 30
fold_metric_regressions: 2
```

Final holdout:

```text
changed_windows: 54
final_exposure_pass: true
metric_delta: -0.0000143517
relative_lift_vs_fallback: -0.0015932175
promotion_verdict: not_promotable
```

## Selected Include-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.65
false_positive_weight: 2.0
training_weighting: time-bin-label-balanced
training_time_bins: 3
```

Validation:

```text
combined_metric_delta: +0.0002947096
combined_changed_windows: 23
fold_metric_deltas: -0.0000653468, -0.0004099246, +0.0013594001
fold_changed_windows: 2, 7, 14
fold_metric_regressions: 2
```

Final holdout:

```text
changed_windows: 1
final_exposure_pass: false
metric_delta: +0.0000001652
relative_lift_vs_fallback: -0.0014398426
split_verdict: rule_improves_split
promotion_verdict: not_validated_final_underexposed
```

## Interpretation

Fact: The no-series robust candidate has enough final exposure but hurts final
holdout.

Fact: The include-series robust candidate has a tiny positive final split delta
but changes only 1 final holdout window.

Inference: The include-series positive is not a transferable finance router
signal. It is a sparse intervention that happened to help once.

Recommendation: Keep the final-exposure gate. The next useful lever is not
relaxing validation. It should either improve training labels so fold
regressions disappear, or switch to a policy class that can create enough final
exposure without hurting the final holdout.
