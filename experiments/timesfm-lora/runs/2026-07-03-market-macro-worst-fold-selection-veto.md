# Worst-Fold Logistic Veto Selection

Date: 2026-07-03

## Problem Framing

The minimum-exposure gate fixed the previous sparse-promotion problem. It also
made the next blocker clearer:

```text
best robust no-series candidate:
  validation changed windows: 144
  final changed windows: 52
  final metric delta: +0.0000070437
  validation fold metric regressions: 2
```

The candidate had enough exposure, but its chronological validation folds were
directionally inconsistent. This run tests whether robust diagnostics improve
when candidate selection prioritizes the worst validation fold instead of mostly
ranking by combined validation lift.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--selection-objective combined
--selection-objective worst-fold
```

Default behavior remains:

```text
selection_objective: combined
```

The new worst-fold objective records and uses:

```text
fold_metric_deltas
min_fold_metric_delta
mean_fold_metric_delta
```

In robust mode, it still requires:

```text
combined_metric_delta > 0
combined_negative_series_delta <= 0
fold_negative_regressions == 0
exposure_pass == true
```

But among candidates, it ranks the least-bad fold before combined metric lift.

## Commands

Strict smoke:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-objective worst-fold \
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
  --output reports/router-logistic-veto-worst-fold-selection-strict-smoke-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

No-series robust diagnostic:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective worst-fold \
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
  --output reports/router-logistic-veto-worst-fold-selection-robust-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Include-series robust diagnostic:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --selection-gate robust \
  --selection-objective worst-fold \
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
  --output reports/router-logistic-veto-worst-fold-selection-robust-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Surface | Gate | Objective | Candidate count | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| no-series | strict | worst-fold | 200 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | worst-fold | 200 | 5 | 0 | 14 | -0.0000146476 | not_promotable |
| include-series | robust | worst-fold | 200 | 2 | 0 | 0 | +0.0000000000 | not_validated_no_future_exposure |

## No-Series Worst-Fold Candidate

Selected config:

```text
l2: 0.1
probability_threshold: 0.5
false_positive_weight: 2.0
learning_rate: 0.05
steps: 1200
```

Validation summary:

```text
combined_metric_delta: +0.0002187544
combined_changed_windows: 45
fold_metric_deltas: -0.0000696377, +0.0000006906, +0.0007252104
min_fold_metric_delta: -0.0000696377
mean_fold_metric_delta: +0.0002187544
fold_changed_windows: 24, 2, 19
fold_negative_regressions: 0
fold_metric_regressions: 1
exposure_pass: true
robust_pass: true
```

Validation folds:

| Fold | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---|
| cut3750 | 24 | -0.0000696377 | 1 -> 1 | rule_hurts_split |
| cut4000 | 2 | +0.0000006906 | 1 -> 1 | rule_improves_split |
| cut4250 | 19 | +0.0007252104 | 3 -> 1 | rule_improves_split |

Final holdout:

```text
changed_windows: 14
metric_delta: -0.0000146476
negative_series: 2 -> 2
relative_lift_vs_fallback: -0.0015963435
verdict: rule_hurts_split
```

## Comparison With Combined Objective

| Objective | Selected config | Fold regressions | Worst fold | Validation changed | Final changed | Final delta |
|---|---|---:|---:|---:|---:|---:|
| combined | `l2=0.1`, `threshold=0.55`, `fpw=1.0` | 2 | -0.0003655074 | 144 | 52 | +0.0000070437 |
| worst-fold | `l2=0.1`, `threshold=0.5`, `fpw=2.0` | 1 | -0.0000696377 | 45 | 14 | -0.0000146476 |

The ranking objective improved validation fold shape:

```text
fold regressions: 2 -> 1
worst fold delta: -0.0003655074 -> -0.0000696377
```

But it reduced useful intervention mass:

```text
validation changed windows: 144 -> 45
final changed windows: 52 -> 14
final metric delta: +0.0000070437 -> -0.0000146476
```

## Include-Series Diagnostic

Worst-fold include-series selected the same robust config as the previous
minimum-exposure diagnostic:

```text
l2: 0.1
probability_threshold: 0.8
false_positive_weight: 1.0
```

Validation:

```text
combined_metric_delta: +0.0004052857
combined_changed_windows: 26
fold_metric_deltas: -0.0000653468, -0.0006609429, +0.0019421468
fold_metric_regressions: 2
```

Final:

```text
changed_windows: 0
metric_delta: 0.0
verdict: no_rule_exposure
```

## Interpretation

Fact: worst-fold selection changes the no-series robust candidate.

Fact: it improves chronological validation consistency but does not eliminate
all fold metric regressions.

Fact: final holdout becomes worse and less exposed.

Fact: include-series still has no final exposure.

Inference: a ranking-only objective can choose a less fragile-looking validation
candidate, but it does not teach the logistic model a fold-consistent boundary.

Inference: the failure is not just candidate ordering. The training target still
learns fallback-better labels pooled across discovery, while the promotion
contract requires chronological consistency.

Recommendation: keep worst-fold ranking as a diagnostic report option, but do
not use it for promotion. The next useful lever is a fold-consistency-aware
training target or sample weighting scheme, not another post-hoc ranking pass.
