# Market Macro Realized Vol 20 Series Risk Objective

Date: 2026-07-02

## Goal

Turn the previous qualitative router question into an explicit objective:

```text
risk_adjusted_score = delta_vs_fallback - penalty * downside_mass_per_window
```

This tests whether the current finance router should prefer lower aggregate
downside even if that costs some total MAE lift.

## Code Changes

Added risk-objective summaries to:

```text
scripts/evaluate_router_fallback_veto.py
```

New output fields:

```text
negative_delta_sum
negative_delta_abs_sum
downside_mass_per_window
worst_negative_series_mean
risk_objective
best_by_negative_count_then_delta
```

The router policy still uses only completed prior cuts. Current-cut errors are
used only for offline scoring and report ranking.

## Command

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --metric mae \
  --candidate-set knn-regret \
  --min-validation-lift 0.005 \
  --veto-k 25 \
  --veto-k 50 \
  --veto-k 100 \
  --regret-threshold -0.0001 \
  --regret-threshold 0.0 \
  --regret-threshold 0.0001 \
  --feature-mode global \
  --feature-mode series \
  --series-downside-threshold 0.0002 \
  --series-downside-threshold 0.0005 \
  --series-downside-threshold 0.001
```

Readiness refresh:

```bash
uv run python scripts/evaluate_finance_readiness.py
```

## Results

| Selection rule | Extra lift vs fallback | Positive series | Negative series | Downside mass / window | Vetoed windows |
|---|---:|---:|---:|---:|---:|
| baseline validation-gated | 0.292% | 7 | 3 | 0.0000251505 | 0 |
| best by delta | 0.319% | 8 | 2 | 0.0000080650 | 1378 |
| risk penalty 1 | 0.319% | 8 | 2 | 0.0000080650 | 1378 |
| risk penalty 10 | 0.319% | 8 | 2 | 0.0000080650 | 1378 |
| risk penalty 50 | 0.264% | 7 | 3 | 0.0000058045 | 1228 |
| risk penalty 100 | 0.264% | 7 | 3 | 0.0000058045 | 1228 |

Best ordinary risk-balanced config:

```text
feature_mode: series
k: 50
regret_threshold: 0.0001
series_downside_threshold: 0.0005
delta_vs_fallback: 0.0002931205
relative_lift_vs_fallback: 0.318529%
positive / negative series: 8 / 2
downside_mass_per_window: 0.0000080650
vetoed_windows: 1378
```

Extreme penalty config:

```text
feature_mode: series
k: 25
regret_threshold: -0.0001
series_downside_threshold: 0.0002
delta_vs_fallback: 0.0002424909
relative_lift_vs_fallback: 0.263510%
positive / negative series: 7 / 3
downside_mass_per_window: 0.0000058045
vetoed_windows: 1228
```

Best no-negative-series policy:

```text
null
```

Readiness gate:

```text
verdict: continue_research
fixed average MAE lift: 1.724%
router extra lift: 0.319%
negative router series: 2
```

## Interpretation

Fact: ordinary risk penalties from 1 to 10 choose the same config as
`best_veto_by_delta`.

Fact: extreme risk penalties from 50 to 100 choose a lower-downside policy, but
that policy has 3 negative series and lower total lift.

Fact: no tested policy reaches `negative_routed_series_count = 0`.

Inference: the current policy family can reduce downside amount, but it cannot
cleanly remove negative routed series.

Recommendation: do not keep hand-tuning this router threshold family. The next
gate-moving path should be either a new adapter/rank test for the two remaining
negative series or a selector with an explicit per-series constraint, not only
a softer aggregate downside penalty.
