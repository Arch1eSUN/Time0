# Time-Bin Logistic Veto Training

Date: 2026-07-03

## Problem Framing

The cut-balanced training run showed a structural limit: validation selection
trained only on cut3500, so balancing by cut had no leverage during candidate
selection.

This run creates no-leak temporal groups inside each available training cut:

```text
training_weighting = time-bin-label-balanced
training_time_bins = 3
```

For discovery selection, that means cut3500 is split into early, middle, and
late start-index bins before validation folds are touched.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--training-weighting time-bin-label-balanced
--training-time-bins 3
```

The report now records:

```text
discovery_example_time_bin_summary
final_train_example_time_bin_summary
```

The bin assignment is based on `start_index` inside each cut, so it remains
chronological and does not use validation outcomes.

## Discovery Time Bins

| Cut | Bin | Start index | Fallback better | Selected better |
|---:|---:|---|---:|---:|
| 3500 | 0 | 350-366 | 47 | 105 |
| 3500 | 1 | 367-383 | 73 | 72 |
| 3500 | 2 | 384-399 | 90 | 55 |

This confirms the new weighting has leverage during validation selection:
discovery cut3500 contains three chronologically different label regimes.

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-time-bin-training-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
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
  --output reports/router-logistic-veto-time-bin-training-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust diagnostics:

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
  --output reports/router-logistic-veto-time-bin-training-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective worst-fold \
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
  --output reports/router-logistic-veto-time-bin-training-worst-fold-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
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
  --output reports/router-logistic-veto-time-bin-training-strict-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

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
  --output reports/router-logistic-veto-time-bin-training-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Objective | Candidate count | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| default smoke | strict | combined | 28 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | combined | 200 | 4 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 200 | 4 | 0 | 54 | -0.0000143517 | not_promotable |
| no-series | robust | worst-fold | 200 | 4 | 0 | 54 | -0.0000143517 | not_promotable |
| include-series | strict | combined | 200 | 2 | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 200 | 2 | 0 | 1 | +0.0000001652 | incremental_positive_but_below_fallback |

## Selected No-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.55
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
training_time_bins: 3
```

Validation summary:

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
metric_delta: -0.0000143517
negative_series: 2 -> 2
verdict: rule_hurts_split
```

## Include-Series Robust Diagnostic

```text
l2: 0.1
probability_threshold: 0.65
false_positive_weight: 2.0
training_weighting: time-bin-label-balanced
training_time_bins: 3
```

Validation summary:

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
metric_delta: +0.0000001652
verdict: rule_improves_split
```

## Interpretation

Fact: time-bin balancing has real validation-selection leverage. No-series
robust-pass candidates drop from 5 under cut-balanced training to 4 under
time-bin-balanced training.

Fact: it does not produce any strict-positive candidate.

Fact: no-series final holdout regresses with 54 changed windows.

Fact: include-series final holdout is technically positive but only changes 1
window, so it is not meaningful promotion evidence.

Inference: simple temporal-bin balancing changes the learned decision boundary,
but it does not solve fold consistency. It reduces some validation exposure and
still leaves two fold metric regressions.

Recommendation: keep the time-bin report diagnostics, but do not promote this
training mode. The next lever should be a final-exposure gate plus bin-count
sensitivity, so tiny one-window final positives cannot appear stronger than
they are.
