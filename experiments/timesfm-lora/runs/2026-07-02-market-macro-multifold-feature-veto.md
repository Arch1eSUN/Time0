# Multi-Fold Feature Veto Validation

Date: 2026-07-02

## Problem Framing

Single-cut feature veto selection found a no-leak aggregate signal, but
discovery-side downside control did not transfer to future downside. This run
adds a chronological validation layer:

```text
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
```

The goal is to select a feature-veto rule using validation folds before testing
it once on the final holdout.

## Command

```bash
uv run python scripts/validate_multifold_feature_veto.py
```

## Inputs

```text
router rows:
  reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

router report:
  reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

output:
  reports/router-feature-veto-multifold-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Selection Setup

```text
candidate_objective: downside-first
candidate_limit: 200
validation_candidate_count: 200
validation_robust_pass_count: 2
selection_reason: robust_pass
```

Selected rule:

```text
feature: prediction_context_alignment.recent3000_predicted_last_delta_from_past_last_over_std
direction: >=
threshold: 0.7595631100372521
```

## Validation Folds

| Fold | Windows | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---:|---|
| cut3750 | 500 | 3 | +0.0000913814 | 1 -> 0 | rule_improves_split |
| cut4000 | 500 | 2 | -0.0000147256 | 1 -> 1 | rule_hurts_split |
| cut4250 | 500 | 3 | +0.0001041148 | 3 -> 3 | rule_improves_split |

Combined validation summary:

```text
combined_metric_delta: +0.0000602569
combined_negative_series_delta: 0
fold_negative_regressions: 0
fold_metric_regressions: 1
fold_no_exposure: 0
```

## Final Holdout

```text
final_holdout_min_cut: 4250
windows: 2500
changed_windows: 9
harmful_vetoed: 4
beneficial_blocked: 5
metric_delta: +0.0000160188
negative_series: 2 -> 2
```

Relative lift vs fallback:

```text
original router: -0.144159%
feature veto:   -0.127235%
```

Overall verdict:

```text
incremental_positive_but_below_fallback
```

## Interpretation

Fact: multi-fold validation selected a different rule than single-cut discovery.
The new selected rule is based on prediction-context alignment, not raw
`context.past_trend`.

Fact: final holdout improves relative to the current router and does not
increase negative series.

Fact: final holdout is still below the fixed `recent2000` fallback. The rule
improves a weak router state but does not produce a publishable router.

Inference: multi-fold chronological validation is a better selection method
than single-cut discovery, but the current single-rule veto family is still too
weak to beat fallback on the final holdout.

Recommendation: keep multi-fold validation as the router selection gate. The
next experiment should use the same gate with a richer policy class, such as a
two-feature veto or small supervised router, rather than continuing to tune
single-feature thresholds.

