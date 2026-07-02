# Two-Feature Veto Under Multi-Fold Gate

Date: 2026-07-02

## Problem Framing

The previous multi-fold feature veto selected a single prediction-context
alignment rule that improved the final holdout incrementally, but still stayed
below the fixed `recent2000` fallback. This run tests whether a deeper
two-feature AND veto can improve the router under the same chronological gate.

## Command

Default run:

```bash
uv run python scripts/validate_multifold_two_feature_veto.py
```

Sensitivity run with a wider pair pool:

```bash
uv run python scripts/validate_multifold_two_feature_veto.py \
  --pair-candidate-limit 1200 \
  --output reports/router-two-feature-veto-multifold-validation-pair1200-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Setup

```text
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
single_candidate_count: 60
pair_candidate_count: 400
max_validation_fold_no_exposure: 0
```

The rule class is:

```text
if single_rule_A matches AND single_rule_B matches:
  selected_family = recent2000
```

## Selected Rule

```text
first:
  prediction_context_alignment.recent2000_predicted_trend_minus_past_trend >= 0.8012431066174683

second:
  prediction_context_alignment.recent1500_predicted_mean_delta_from_past_last_over_std >= 0.30731040774514196
```

Selection result:

```text
selection_reason: best_available_no_robust_pass
validation_robust_pass_count: 0
```

## Validation Folds

| Fold | Windows | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---:|---|
| cut3750 | 500 | 0 | 0.0000000000 | 1 -> 1 | no_rule_exposure |
| cut4000 | 500 | 0 | 0.0000000000 | 1 -> 1 | no_rule_exposure |
| cut4250 | 500 | 5 | +0.0000795744 | 3 -> 3 | rule_improves_split |

Combined validation:

```text
combined_metric_delta: +0.0000265248
combined_negative_series_delta: 0
fold_negative_regressions: 0
fold_metric_regressions: 2
fold_no_exposure: 2
robust_pass: false
```

## Final Holdout

```text
windows: 2500
changed_windows: 7
harmful_vetoed: 5
beneficial_blocked: 2
metric_delta: +0.0000844906
negative_series: 2 -> 2
```

Relative lift vs fallback:

```text
original router: -0.144159%
two-feature veto: -0.054892%
```

Overall verdict:

```text
incremental_positive_but_below_fallback
```

## Sensitivity Check

With `--pair-candidate-limit 1200`:

```text
validation_robust_pass_count: 0
final_metric_delta: +0.0000291548
final_relative_lift_vs_fallback: -0.113356%
negative_series: 2 -> 2
```

The wider pair pool does not find a robust-pass rule.

## Interpretation

Fact: two-feature AND rules improve the final holdout more than the previous
single-feature rule, while keeping negative series unchanged.

Fact: no two-feature candidate passes the strict multi-fold robust gate because
the selected rule has no exposure in two validation folds.

Fact: even the stronger final holdout improvement remains below the fixed
`recent2000` fallback.

Inference: two-feature AND rules are more precise but too sparse. They can fix
some bad override windows, but they do not create a reliable release-ready
router.

Recommendation: stop hand-growing AND veto rules. The next policy class should
be score-based or supervised, so it can combine multiple signals without
requiring every condition to fire simultaneously.

