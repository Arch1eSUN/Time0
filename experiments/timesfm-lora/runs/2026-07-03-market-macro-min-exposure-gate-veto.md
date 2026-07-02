# Minimum-Exposure Logistic Veto Gate

Date: 2026-07-03

## Problem Framing

The false-positive-penalty run created the first no-series strict-positive
logistic candidates, but the selected policy was too sparse:

```text
validation changed windows: 1, 3, 11
final changed windows: 6
final metric delta: -0.0000069200
```

That means the old strict gate was incomplete. It checked that validation folds
did not regress, but it did not check whether the rule touched enough windows to
be reliable evidence.

This run adds a minimum-exposure promotion gate.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--min-validation-changed-windows
--min-validation-fold-changed-windows
```

The default keeps previous behavior:

```text
min_validation_changed_windows: 1
min_validation_fold_changed_windows: 1
```

For the real gate in this run:

```text
combined validation changed windows >= 20
each validation fold changed windows >= 2
```

The validation summary now records:

```text
combined_changed_windows
fold_changed_windows
fold_under_min_exposure
exposure_pass
```

Strict and robust selection both require `exposure_pass`.

## Commands

Default compatibility smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --output reports/router-logistic-veto-default-smoke-min-exposure-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict no-series gate:

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
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --output reports/router-logistic-veto-min-exposure-gate-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust no-series diagnostic:

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
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --output reports/router-logistic-veto-min-exposure-gate-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict include-series gate:

```bash
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
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --output reports/router-logistic-veto-min-exposure-gate-strict-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust include-series diagnostic:

```bash
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
  --min-validation-changed-windows 20 \
  --min-validation-fold-changed-windows 2 \
  --output reports/router-logistic-veto-min-exposure-gate-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Candidate count | Robust-pass | Positive | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| default smoke | strict | 28 | 5 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | 200 | 5 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 200 | 5 | 5 | 0 | 52 | +0.0000070437 | incremental_positive_but_below_fallback |
| include-series | strict | 200 | 2 | 2 | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | 200 | 2 | 2 | 0 | 0 | +0.0000000000 | not_validated_no_future_exposure |

## Selected No-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.55
false_positive_weight: 1.0
learning_rate: 0.05
steps: 1200
```

Validation summary:

```text
combined_metric_delta: +0.0003127051
combined_changed_windows: 144
fold_changed_windows: 76, 33, 35
fold_negative_regressions: 0
fold_metric_regressions: 2
exposure_pass: true
robust_pass: true
```

Validation folds:

| Fold | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---|
| cut3750 | 76 | -0.0000538052 | 1 -> 1 | rule_hurts_split |
| cut4000 | 33 | -0.0003655074 | 1 -> 1 | rule_hurts_split |
| cut4250 | 35 | +0.0013574278 | 3 -> 1 | rule_improves_split |

Final holdout:

```text
changed_windows: 52
metric_delta: +0.0000070437
negative_series: 2 -> 2
relative_lift_vs_fallback: -0.0013671695
verdict: rule_improves_split
```

## Include-Series Diagnostic

Robust include-series selected:

```text
l2: 0.1
probability_threshold: 0.8
false_positive_weight: 1.0
```

Validation exposure:

```text
combined_changed_windows: 26
fold_changed_windows: 2, 10, 14
fold_metric_regressions: 2
```

Final holdout:

```text
changed_windows: 0
metric_delta: 0.0
verdict: no_rule_exposure
```

## Interpretation

Fact: the compatibility smoke preserved default behavior: 28 candidates and no
strict candidate.

Fact: the new exposure gate removes the previous sparse strict-positive
candidate set. Strict no-series drops from 7 strict-positive candidates to 0.

Fact: no-series robust now selects a much less sparse candidate: 144 validation
changes and 52 final changes.

Fact: that robust candidate still has 2 validation fold metric regressions, so
strict mode correctly refuses promotion.

Fact: final holdout improves slightly, but the routed policy remains below the
fixed recent2000 fallback.

Inference: the minimum-exposure gate fixed the previous false confidence
problem. It no longer lets a 1/3/11-window rule look promotable.

Inference: the current blocker moved from "too little exposure" to "inconsistent
fold direction". The model can find exposed rules, but the improvements are not
stable across chronological validation folds.

Recommendation: keep the exposure gate. Do not promote the robust no-series
candidate. The next useful experiment should directly address fold direction,
for example by changing selection from combined metric to worst-fold-aware
utility, or by training against fold-consistent labels rather than aggregate
fallback-better labels.
