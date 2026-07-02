# False-Positive-Penalized Logistic Veto

Date: 2026-07-03

## Problem Framing

The compact-alignment run showed that adding or compressing alignment features
does not solve the remaining fold regressions. The next lever is the supervised
target itself.

This run tests a false-positive-penalized logistic fallback veto:

```text
false positive = veto to fallback when the selected adapter was actually better
```

In financial routing, that error is expensive because it suppresses useful
adapter specialization. The model should prefer abstaining when the evidence
for fallback is weak.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--false-positive-weight
```

Default behavior is unchanged:

```text
false_positive_weight default: 1.0
```

When the value is greater than `1.0`, training upweights negative examples:

```text
label 1: fallback better than selected adapter
label 0: selected adapter better than fallback

false_positive_weight > 1:
  make label 0 more costly during logistic training
```

## Commands

Default smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-false-positive-penalty-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

False-positive penalty strict validation:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
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
  --output reports/router-logistic-veto-false-positive-penalty-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --include-series \
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
  --output reports/router-logistic-veto-false-positive-penalty-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust diagnostic:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
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
  --output reports/router-logistic-veto-false-positive-penalty-robust-diagnostic-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --include-series \
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
  --output reports/router-logistic-veto-false-positive-penalty-robust-diagnostic-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Candidate count | Robust-pass | Positive | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| no-series | strict | 200 | 14 | 31 | 7 | 6 | -0.0000069200 | not_promotable |
| include-series | strict | 200 | 3 | 40 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 200 | 14 | 31 | 7 | 6 | -0.0000069200 | not_promotable |
| include-series | robust | 200 | 3 | 40 | 0 | 0 | +0.0000000000 | not_validated_no_future_exposure |

## Selected No-Series Strict Candidate

```text
l2: 0.001
probability_threshold: 0.5
false_positive_weight: 8.0
learning_rate: 0.05
steps: 1200
```

Validation summary:

```text
combined_metric_delta: +0.00009907197
combined_negative_series_delta: 0
fold_negative_regressions: 0
fold_metric_regressions: 0
fold_no_exposure: 0
```

Validation folds:

| Fold | Metric delta | Changed windows | Negative series | Verdict |
|---|---:|---:|---:|---|
| cut3750 | +0.0000181343 | 1 | 1 | rule_improves_split |
| cut4000 | +0.0001175328 | 3 | 1 | rule_improves_split |
| cut4250 | +0.0001615488 | 11 | 2 | rule_improves_split |

Final holdout:

```text
changed_windows: 6
metric_delta: -0.0000069200
negative_series: 2 -> 2
verdict: rule_hurts_split
```

## Interpretation

Fact: false-positive weighting creates the first strict-positive logistic
no-series candidates.

Fact: the selected strict candidate has tiny validation exposure: 1, 3, and 11
changed windows across the three validation folds.

Fact: final holdout exposure is also tiny, only 6 changed windows, and the
metric delta is negative.

Fact: include-series remains strict-blocked. Its robust selected config has no
future exposure at all.

Inference: the target change works in one narrow sense: it can eliminate
validation fold regressions. But it does so by becoming too conservative and
selecting sparse veto policies that do not transfer.

Recommendation: keep false-positive weighting as a useful target lever, but add
a minimum-exposure gate before treating strict validation as promotion evidence.
The next experiment should require enough changed windows per validation split
or combined validation before final holdout is evaluated.
