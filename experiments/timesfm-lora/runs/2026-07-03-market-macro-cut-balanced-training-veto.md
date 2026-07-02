# Cut-Balanced Logistic Veto Training

Date: 2026-07-03

## Problem Framing

The worst-fold selection run rejected a post-hoc ranking-only fix. It improved
validation shape but failed final holdout, which suggested the next lever should
enter training or sample weighting.

This run tests a no-leak training-weighting change:

```text
training_weighting = cut-label-balanced
```

The idea is simple: avoid letting one discovery cut or one label dominate the
logistic fallback-veto boundary.

## What Changed

`validate_multifold_logistic_veto.py` now supports:

```bash
--training-weighting global-label-balanced
--training-weighting cut-label-balanced
```

Default behavior remains:

```text
training_weighting: global-label-balanced
```

The new report also records:

```text
discovery_example_cut_summary
final_train_example_cut_summary
```

That diagnostic matters because a cut-balanced objective only helps if the
training split actually contains multiple cuts.

## No-Leak Constraint

This run does not train on validation fold outcomes.

The cut-balanced weighting only uses the examples available inside the current
training split:

```text
validation selection training:
  discovery examples only

final holdout training:
  discovery + validation examples
```

## Results

| Surface | Gate | Objective | Candidate count | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| default smoke | strict | combined | 28 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | strict | combined | 200 | 5 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 200 | 5 | 0 | 53 | -0.0000121668 | not_promotable |
| no-series | robust | worst-fold | 200 | 5 | 0 | 15 | -0.0000299353 | not_promotable |
| include-series | strict | combined | 200 | 2 | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 200 | 2 | 0 | 0 | +0.0000000000 | not_validated_no_future_exposure |

## Split Composition

Discovery examples:

| Cut | Fallback better | Selected better |
|---:|---:|---:|
| 3500 | 210 | 232 |

Final-train examples:

| Cut | Fallback better | Selected better |
|---:|---:|---:|
| 3500 | 210 | 232 |
| 3750 | 141 | 132 |
| 4000 | 68 | 90 |
| 4250 | 82 | 67 |

## Selected No-Series Robust Candidate

```text
l2: 0.1
probability_threshold: 0.55
false_positive_weight: 1.0
training_weighting: cut-label-balanced
```

Validation summary:

```text
combined_metric_delta: +0.0003127051
combined_changed_windows: 144
fold_metric_deltas: -0.0000538052, -0.0003655074, +0.0013574278
fold_changed_windows: 76, 33, 35
fold_metric_regressions: 2
```

Final holdout:

```text
changed_windows: 53
metric_delta: -0.0000121668
negative_series: 2 -> 2
verdict: rule_hurts_split
```

## Selected Worst-Fold Robust Candidate

```text
l2: 0.1
probability_threshold: 0.5
false_positive_weight: 2.0
training_weighting: cut-label-balanced
```

Validation summary:

```text
combined_metric_delta: +0.0002187544
combined_changed_windows: 45
fold_metric_deltas: -0.0000696377, +0.0000006906, +0.0007252104
fold_changed_windows: 24, 2, 19
fold_metric_regressions: 1
```

Final holdout:

```text
changed_windows: 15
metric_delta: -0.0000299353
negative_series: 2 -> 2
verdict: rule_hurts_split
```

## Interpretation

Fact: discovery selection training has only one cut, cut3500.

Fact: because discovery has only one cut, cut-label balancing cannot change the
validation candidate surface relative to global label balancing.

Fact: final retraining does contain multiple cuts, so cut-label balancing does
change final behavior.

Fact: the changed final behavior is worse: combined robust flips from tiny
positive in the previous global-label run to negative here.

Inference: the cut-balanced idea is directionally reasonable, but this split
layout makes it ineffective for validation selection and harmful for final
retraining.

Recommendation: keep `training_weighting` and split summaries as diagnostics,
but do not use `cut-label-balanced` for promotion. The next experiment should
create temporal bins inside discovery cut3500 so fold-consistency pressure exists
before validation selection.
