# Calibrated Logistic Fallback-Veto Under Strict Gate

Date: 2026-07-02

## Problem Framing

The strict supervised gate rejected all KNN-regret candidates. This run tests a
different supervised model class: a small numpy logistic fallback-veto model.
Instead of estimating local regret by nearest neighbors, the model learns a
probability that the selected adapter will underperform the fixed `recent2000`
fallback.

The strict gate remains unchanged. A candidate must pass fold-level validation
before any final holdout policy is selected.

## Commands

No-series strict run:

```bash
uv run python scripts/validate_multifold_logistic_veto.py
```

Series-aware strict sensitivity:

```bash
uv run python scripts/validate_multifold_logistic_veto.py \
  --include-series \
  --output reports/router-logistic-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Setup

```text
model: logistic fallback-veto probability
selection_gate: strict
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
discovery_examples: 442
final_train_examples: 1022
candidate configs: 28
l2 values: 0.0, 0.001, 0.01, 0.1
probability thresholds: 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8
learning_rate: 0.05
steps: 1200
```

Label:

```text
1.0 = fallback was better than selected adapter
0.0 = selected adapter was better than fallback
```

Decision rule:

```text
if P(fallback_better | no-leak features, selected adapter) >= probability_threshold:
  selected_family = recent2000
```

## No-Series Strict Result

```text
verdict: strict_gate_no_candidate
validation_robust_pass_count: 5
validation_positive_count: 6
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Top loose validation candidates:

| L2 | Threshold | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions |
|---:|---:|---:|---:|---:|---:|
| 0.1 | 0.55 | 144 | +0.0003127051 | 0 | 2 |
| 0.1 | 0.50 | 245 | +0.0002748633 | 0 | 2 |
| 0.1 | 0.60 | 79 | +0.0002554725 | 0 | 1 |
| 0.1 | 0.65 | 54 | +0.0002337397 | 0 | 2 |
| 0.1 | 0.70 | 25 | +0.0000279336 | 0 | 1 |

## Series-Aware Strict Result

```text
verdict: strict_gate_no_candidate
validation_robust_pass_count: 1
validation_positive_count: 1
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Top loose validation candidates:

| L2 | Threshold | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions |
|---:|---:|---:|---:|---:|---:|
| 0.1 | 0.80 | 26 | +0.0004052857 | 0 | 2 |
| 0.1 | 0.75 | 31 | +0.0002097734 | 0 | 2 |
| 0.1 | 0.70 | 36 | +0.0001562503 | 0 | 2 |
| 0.1 | 0.65 | 49 | +0.0000352139 | 0 | 2 |
| 0.1 | 0.55 | 128 | -0.0002970712 | 0 | 2 |

## Interpretation

Fact: logistic fallback probability produces aggregate-positive validation
candidates on both no-series and series-aware surfaces.

Fact: every aggregate-positive candidate still has at least one fold-level
metric regression.

Fact: strict mode therefore fails closed and does not evaluate final holdout.

Inference: the calibrated probability interface is better than a hand-written
threshold ensemble, but current no-leak features still do not support a
fold-stable supervised veto policy.

Recommendation: keep the strict gate. The next experiment should improve
candidate quality through better labels or richer no-leak features, not by
relaxing fold-level validation.
