# Utility-Aware Expected-Regret Veto Under Strict Gate

Date: 2026-07-02

## Problem Framing

The previous expected-regret run found stronger aggregate validation signal than
logistic fallback probability, but the highest-lift candidates were unstable:
they still had fold metric regressions and sometimes increased negative-series
count. This run keeps the same expected-regret model and adds a utility score
on validation candidates.

The utility score is only a diagnostic and ranking surface. The strict gate is
unchanged: no candidate reaches final holdout unless it has zero fold metric
regressions, zero fold downside regressions, and sufficient exposure.

## Commands

No-series strict run with utility diagnostics:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --output reports/router-expected-regret-veto-utility-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Series-aware strict sensitivity with utility diagnostics:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --output reports/router-expected-regret-veto-utility-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
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
```

Utility formula:

```text
utility_score =
  combined_metric_delta
  - 0.001 * max(combined_negative_series_delta, 0)
  - 0.001 * fold_negative_regressions
  - 0.001 * fold_metric_regressions
  - 0.001 * fold_no_exposure
```

Default utility pass:

```text
utility_positive = utility_score > 0.0 and changed_windows > 0
```

## No-Series Result

```text
verdict: strict_gate_no_candidate
validation_positive_count: 14
validation_utility_positive_count: 5
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Best utility-ranked validation candidate:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | -0.0010 | 2.0 | 308 | +0.0013203037 | 0 | 1 | 0 | +0.0003203037 |

Highest raw-lift candidate:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.0020 | 4.0 | 140 | +0.0014757435 | 2 | 2 | 1 | -0.0035242565 |

Interpretation:

```text
The raw highest-lift no-series candidate is rejected by utility scoring because
its aggregate lift is smaller than its downside and fold-instability penalties.
The best utility candidate is cleaner, but still has one fold metric regression,
so strict gate correctly blocks final holdout.
```

## Series-Aware Result

```text
verdict: strict_gate_no_candidate
validation_positive_count: 7
validation_utility_positive_count: 0
validation_strict_positive_count: 0
selected_config: null
final_holdout_evaluated: false
```

Best utility-ranked validation candidate:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.0020 | 4.0 | 94 | +0.0010332927 | 0 | 2 | 0 | -0.0009667073 |

Highest raw-lift candidate:

| L2 | Regret threshold | Positive weight | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | -0.0020 | 4.0 | 382 | +0.0013341791 | 1 | 2 | 1 | -0.0026658209 |

Interpretation:

```text
Once series identity is included, every loose positive candidate fails the
utility score. The series-aware surface therefore looks less publishable than
the no-series surface, not more publishable.
```

## Conclusion

Fact: utility scoring reduces no-series loose positives from 14 to 5 and
series-aware loose positives from 7 to 0.

Fact: strict validation still has 0 passing candidates on both surfaces.

Fact: final holdout remains untouched.

Inference: the utility score is doing useful diagnostic work. It filters out
high average-lift candidates whose gains are not large enough to pay for fold
instability and downside regressions.

Recommendation: keep this utility diagnostic in the expected-regret script.
The next useful experiment should not relax strict validation. It should either
search for features that reduce fold regressions, or train a utility-aware
model objective directly instead of applying utility only after model training.
