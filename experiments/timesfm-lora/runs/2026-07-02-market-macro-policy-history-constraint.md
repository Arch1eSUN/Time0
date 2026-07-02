# Market Macro Policy-History Series Constraint

Date: 2026-07-02

## Goal

Test whether a no-leak hard per-series constraint can clear the remaining
negative routed series without giving up the router's positive lift.

The constraint uses only the same policy's completed prior cut results:

```text
if prior same-policy mean_delta_vs_fallback(series) <= threshold:
  force current non-fallback selections for that series back to fallback
```

## Code Changes

Added policy-history constraint support to:

```text
scripts/evaluate_router_fallback_veto.py
```

New CLI controls:

```text
--policy-history-series-threshold
--policy-history-min-windows
```

Updated readiness candidate selection in:

```text
scripts/evaluate_finance_readiness.py
```

Readiness now uses `summary.best_no_negative_series` as the release candidate
when it exists. If no no-negative candidate exists, it falls back to
`summary.best_veto_by_delta`.

## Commands

Delayed hard-constraint sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-policy-history-constraint-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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
  --policy-history-series-threshold -0.00005 \
  --policy-history-series-threshold 0.0 \
  --policy-history-series-threshold 0.00005 \
  --policy-history-series-threshold 0.0001 \
  --policy-history-min-windows 100
```

Early strong hard-constraint sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-policy-history-constraint-fine-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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
  --series-downside-threshold 0.0005 \
  --policy-history-series-threshold 0.00001 \
  --policy-history-series-threshold 0.000025 \
  --policy-history-series-threshold 0.00005 \
  --policy-history-series-threshold 0.000075 \
  --policy-history-series-threshold 0.0001 \
  --policy-history-series-threshold 0.00015 \
  --policy-history-min-windows 50
```

Readiness checks:

```bash
uv run python scripts/evaluate_finance_readiness.py

uv run python scripts/evaluate_finance_readiness.py \
  --router-report reports/router-fallback-veto-policy-history-constraint-fine-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output-json reports/finance-readiness-policy-history-constraint-market-macro-realized-vol-20-h20-r4.json \
  --output-md runs/2026-07-02-market-macro-policy-history-constraint-readiness.md
```

## Results

| Policy | Extra lift vs fallback | Positive series | Negative series | Downside mass / window | Vetoed windows |
|---|---:|---:|---:|---:|---:|
| current series-risk objective | 0.319% | 8 | 2 | 0.0000080650 | 1378 |
| delayed policy-history constraint | 0.294% | 7 | 3 | 0.0000190793 | 1440 |
| early policy-history constraint | 0.000% | 0 | 0 | 0.0000000000 | 2538 |

Delayed constraint best config:

```text
feature_mode: series
k: 50
regret_threshold: 0.0001
series_downside_threshold: 0.0005
policy_history_series_threshold: -0.00005
policy_history_min_windows: 100
relative_lift_vs_fallback: 0.293806%
positive / negative series: 7 / 3
```

Early constraint best no-negative config:

```text
feature_mode: global
k: 25
regret_threshold: -0.0001
series_downside_threshold: 0.0005
policy_history_series_threshold: 0.00001
policy_history_min_windows: 50
relative_lift_vs_fallback: 0.000000%
positive / negative series: 0 / 0
```

## Readiness

Default current readiness:

```text
verdict: continue_research
router_release_candidate: best_by_delta
router_extra_lift: 0.319%
negative_router_series: 2
```

Policy-history constraint readiness:

```text
verdict: continue_research
router_release_candidate: best_no_negative_series
router_extra_lift: 0.000%
negative_router_series: 0
```

## Interpretation

Fact: delayed policy-history constraints preserve positive lift, but they do not
clear negative series.

Fact: early policy-history constraints clear negative series only by collapsing
to the fixed fallback policy.

Fact: a 0-negative candidate with 0% extra lift fails the router extra-lift gate.

Inference: the remaining release blocker is not solved by another scalar
per-series veto threshold.

Recommendation: stop tuning this hard-threshold router family. The next
gate-moving work should target the two remaining problem series with new adapter
capacity or a genuinely different selector, not another all-series fallback
constraint.
