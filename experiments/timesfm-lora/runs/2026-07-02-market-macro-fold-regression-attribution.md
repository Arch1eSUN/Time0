# Expected-Regret Fold-Regression Attribution

Date: 2026-07-02

## Problem Framing

The consensus run showed that adding more post-hoc gates does not solve the
remaining blocker. Strict validation still fails because at least one
validation fold regresses. This run stops changing the router and instead
diagnoses where the fold regressions come from.

The diagnostic uses the already selected expected-regret utility configs and
reconstructs their validation-fold veto decisions. It does not select a new
candidate and does not evaluate final holdout.

## Commands

No-series attribution:

```bash
uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-utility-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Series-aware attribution:

```bash
uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-utility-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## No-Series Diagnostic

Selected config:

```text
l2: 0.0
regret_threshold: -0.001
positive_weight: 2.0
```

Fold summary:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | -0.0002406373 | 154 | 77 | 77 | fold_regresses |
| 4000 | +0.0000346664 | 90 | 36 | 54 | fold_improves |
| 4250 | +0.0041668820 | 64 | 42 | 22 | fold_improves |

Worst regression fold:

```text
cut: 3750
metric_delta: -0.0002406373
changed_windows: 154
help_windows: 77
harm_windows: 77
sum_help_delta: +0.1112237212
sum_harm_delta: -0.2315423740
```

Main harm sources on cut3750:

| Source | Windows | Sum delta | Mean delta | Harm/help |
|---|---:|---:|---:|---:|
| VIXCLS:realized_vol_20 | 6 | -0.0780834848 | -0.0130139141 | 6/0 |
| DFF:realized_vol_20 | 20 | -0.0267729316 | -0.0013386466 | 7/13 |
| SP500:realized_vol_20 | 50 | -0.0182753274 | -0.0003655065 | 35/15 |
| original family recent3000 | 25 | -0.1263973501 | -0.0050558940 | 15/10 |

Largest harmed-vs-helped feature contrast on cut3750:

```text
prediction_context_alignment.recent1500_predicted_trend_minus_past_trend
  harmed_mean: +0.1638228940
  helped_mean: +0.0549151759

prediction_context_alignment.recent3000_predicted_trend_minus_past_trend
  harmed_mean: +0.1653268248
  helped_mean: +0.0570490099
```

Interpretation:

```text
The no-series strict failure is concentrated in cut3750. The biggest series
harm is VIXCLS, and the largest family harm is vetoing recent3000. Harmed
windows have much larger predicted-trend-minus-past-trend alignment values than
helped windows.
```

## Series-Aware Diagnostic

Selected config:

```text
l2: 1.0
regret_threshold: 0.002
positive_weight: 4.0
```

Fold summary:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | -0.0001224054 | 27 | 15 | 12 | fold_regresses |
| 4000 | -0.0003824223 | 10 | 2 | 8 | fold_regresses |
| 4250 | +0.0036047056 | 57 | 32 | 25 | fold_improves |

Worst regression fold:

```text
cut: 4000
metric_delta: -0.0003824223
changed_windows: 10
help_windows: 2
harm_windows: 8
sum_help_delta: +0.0444639475
sum_harm_delta: -0.2356750793
```

Main harm sources on cut4000:

| Source | Windows | Sum delta | Mean delta | Harm/help |
|---|---:|---:|---:|---:|
| DFF:realized_vol_20 | 5 | -0.1903805358 | -0.0380761072 | 4/1 |
| DCOILWTICO:realized_vol_20 | 4 | -0.0012894591 | -0.0003223648 | 4/0 |
| original family recent1500 | 3 | -0.1773439093 | -0.0591146364 | 2/1 |
| original family recent3000 | 6 | -0.0143260857 | -0.0023876810 | 6/0 |

Largest harmed-vs-helped feature contrast on cut4000:

```text
prediction_context_alignment.full_predicted_last_delta_from_past_last_over_std
  harmed_mean: -0.3460372675
  helped_mean: -0.0412065639

prediction_context_alignment.zero-shot_predicted_last_delta_from_past_last_over_std
  harmed_mean: -0.4068272438
  helped_mean: -0.1202672612
```

Interpretation:

```text
Series-aware routing does not merely overfit identity. Its worst fold is a tiny
10-window exposure where DFF dominates the loss. The harmed windows have much
more negative predicted-last-vs-past-last alignment than helped windows.
```

## Conclusion

Fact: the no-series strict blocker is localized to cut3750, especially VIXCLS
and vetoes away from recent3000.

Fact: the series-aware strict blocker is worse: two folds regress, with cut4000
dominated by DFF harm.

Fact: feature contrasts repeatedly point to prediction-context-alignment
signals, especially predicted trend or predicted last relative to the past
context.

Inference: the current expected-regret surface is missing a stability feature,
not another gate. The router can identify many useful vetoes, but it cannot yet
distinguish when trend/last-value alignment means fallback safety versus when it
means the selected adapter should be left alone.

Recommendation: next round should add or test explicit alignment-risk features
around trend direction and predicted-last displacement, then rerun strict
validation. Do not tune more consensus or utility thresholds until the feature
surface changes.
