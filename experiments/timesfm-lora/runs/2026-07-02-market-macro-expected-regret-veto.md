# Expected-Regret Fallback-Veto Under Strict Gate

Date: 2026-07-02

## Problem Framing

The logistic fallback-veto run improved the decision interface by estimating
`P(fallback_better)`, but strict chronological validation still rejected every
candidate. This run keeps the same strict gate and changes the supervised target
from a binary label to a continuous expected-regret label.

The goal is to test whether the router can learn not only whether fallback is
better, but how much worse the selected adapter is expected to be.

## Commands

No-series strict run:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py
```

Series-aware strict sensitivity:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --output reports/router-expected-regret-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Setup

```text
model: expected-regret ridge fallback-veto
selection_gate: strict
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
discovery_examples: 442
final_train_examples: 1022
candidate configs: 105
l2 values: 0.0, 0.001, 0.01, 0.1, 1.0
regret thresholds: -0.002, -0.001, -0.0005, 0.0, 0.0005, 0.001, 0.002
positive weights: 1.0, 2.0, 4.0
```

Target:

```text
regret_vs_fallback = selected_adapter_error - fallback_error

positive target:
  selected adapter was worse than fallback

negative target:
  selected adapter was better than fallback
```

Decision rule:

```text
if predicted_regret_vs_fallback >= regret_threshold:
  selected_family = recent2000
```

## No-Series Strict Result

```text
verdict: strict_gate_no_candidate
validation_robust_pass_count: 14
validation_positive_count: 14
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Top loose validation candidates by combined metric delta:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.0020 | 4.0 | 140 | +0.0014757435 | 2 | 2 | 1 |
| 0.01 | 0.0010 | 4.0 | 222 | +0.0014325354 | 1 | 2 | 2 |
| 0.01 | 0.0020 | 2.0 | 94 | +0.0014307208 | 1 | 2 | 1 |
| 0.001 | -0.0020 | 2.0 | 343 | +0.0014103636 | 0 | 1 | 1 |
| 0.001 | 0.0000 | 2.0 | 263 | +0.0014024314 | 0 | 2 | 1 |
| 0.001 | -0.0005 | 2.0 | 283 | +0.0014022106 | 0 | 2 | 1 |
| 0.001 | -0.0010 | 2.0 | 306 | +0.0013962858 | 0 | 2 | 0 |

## Series-Aware Strict Result

```text
verdict: strict_gate_no_candidate
validation_robust_pass_count: 7
validation_positive_count: 7
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Top loose validation candidates by combined metric delta:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | -0.0020 | 4.0 | 382 | +0.0013341791 | 1 | 2 | 1 |
| 0.1 | 0.0020 | 4.0 | 185 | +0.0013310477 | 1 | 2 | 2 |
| 0.1 | 0.0010 | 4.0 | 239 | +0.0013189093 | 1 | 2 | 2 |
| 0.1 | 0.0000 | 4.0 | 286 | +0.0013165386 | 1 | 2 | 2 |
| 0.1 | 0.0005 | 4.0 | 258 | +0.0013160841 | 1 | 2 | 2 |
| 0.1 | -0.0010 | 4.0 | 337 | +0.0013128797 | 0 | 2 | 2 |
| 0.1 | -0.0005 | 4.0 | 321 | +0.0013097114 | 0 | 2 | 2 |

## Interpretation

Fact: expected-regret regression finds more aggregate-positive validation
candidates than logistic probability did.

Fact: every aggregate-positive candidate still violates strict fold-level
validation.

Fact: many high-lift candidates also increase validation negative-series count,
especially when ranked only by aggregate metric delta.

Fact: strict mode fails closed and does not evaluate final holdout.

Inference: the continuous regret target improves signal strength, but it does
not solve transfer stability. The current no-leak features still cannot
separate future-safe adapter overrides from time-local wins.

Recommendation: keep the expected-regret script as a diagnostic, but do not
promote this router. The next useful experiment should make the loss surface
more risk-aware, for example by selecting on a utility that combines aggregate
lift, fold non-regression, and negative-series penalty before holdout.
