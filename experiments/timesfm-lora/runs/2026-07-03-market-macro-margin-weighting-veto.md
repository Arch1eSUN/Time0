# Margin-Weighted Logistic Veto Training

Date: 2026-07-03

## Problem Framing

The previous final-exposure gate blocked one-window positives. The next
question was whether the logistic router could learn a cleaner decision
boundary by paying more attention to high-magnitude discovery mistakes.

This run adds a no-leak margin-weighted training mode:

```text
training_weighting = time-bin-margin-balanced
```

The idea is simple: not every historical label is equally important. If
fallback beat the selected adapter by a large amount, that example should carry
more training weight than a nearly tied window.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--training-weighting margin-label-balanced
--training-weighting time-bin-margin-balanced
```

The tested mode was:

```text
time-bin-margin-balanced
```

It multiplies:

```text
time-bin label balance * bounded absolute regret weight
```

The regret margin comes only from discovery or final-train examples, not from
validation or final holdout labels.

Reports now include:

```text
discovery_example_margin_summary
final_train_example_margin_summary
```

## Discovery Margin Shape

```text
examples: 442
fallback_better: 210
selected_better: 232
mean_abs_regret: 0.0052084259
median_abs_regret: 0.0016010391
p90_abs_regret: 0.0142864516
max_abs_regret: 0.0733746976
```

The margin distribution is heavy-tailed. Most examples are small, but a few
windows have much larger selected-vs-fallback regret.

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-margin-weighting-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --training-weighting time-bin-margin-balanced \
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
  --output reports/router-logistic-veto-margin-weighting-time-bin-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --training-weighting time-bin-margin-balanced \
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
  --output reports/router-logistic-veto-margin-weighting-time-bin-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Worst-fold no-series:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective worst-fold \
  --training-weighting time-bin-margin-balanced \
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
  --output reports/router-logistic-veto-margin-weighting-time-bin-worst-fold-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series diagnostics:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --include-series \
  --training-weighting time-bin-margin-balanced \
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
  --output reports/router-logistic-veto-margin-weighting-time-bin-strict-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --include-series \
  --training-weighting time-bin-margin-balanced \
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
  --output reports/router-logistic-veto-margin-weighting-time-bin-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Objective | Candidate count | Robust-pass | Strict-positive | Final changed | Final exposure pass | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| default smoke | strict | combined | 28 | 5 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | combined | 200 | 2 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 200 | 2 | 0 | 0 | false | 0.0 | not_validated_no_future_exposure |
| no-series | robust | worst-fold | 200 | 2 | 0 | 0 | false | 0.0 | not_validated_no_future_exposure |
| include-series | strict | combined | 200 | 0 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 200 | 0 | 0 | 0 | false | 0.0 | not_validated_no_future_exposure |

## Selected No-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.75
false_positive_weight: 1.0
training_weighting: time-bin-margin-balanced
training_time_bins: 3
```

Validation:

```text
combined_metric_delta: +0.0000779967
combined_changed_windows: 34
fold_metric_deltas: +0.0000286664, -0.0009475161, +0.0011528397
fold_changed_windows: 3, 11, 20
fold_metric_regressions: 1
```

Final holdout:

```text
changed_windows: 0
final_exposure_pass: false
metric_delta: 0.0
promotion_verdict: not_validated_no_future_exposure
```

Worst-fold selection chose the same candidate and produced the same final
outcome.

## Interpretation

Fact: Margin weighting reduced no-series robust-pass candidates from 4 to 2
compared with time-bin-only weighting.

Fact: The selected no-series margin-weighted candidate has one validation fold
metric regression and zero final holdout exposure.

Fact: Include-series margin weighting has zero robust-pass and zero
validation-positive candidates.

Inference: Margin weighting makes the logistic veto more conservative, but it
does not create a transferable final-holdout policy.

Recommendation: Stop this specific training lever. The next useful experiment
should not be another scalar sample-weight tweak. It should change the router
interface, likely by separating "is fallback better?" from "should we abstain
because confidence/exposure is too low?"
