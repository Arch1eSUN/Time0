# Market Macro Realized Vol 20 Series Downside Veto

Date: 2026-07-02

## Goal

Move the finance readiness gate that failed here:

```text
router_negative_series: required 0, actual 3
```

The experiment tests whether no-leak historical downside evidence can veto
router overrides that are likely to hurt a specific series.

## Code Changes

Added optional fallback-veto controls:

```text
--series-downside-threshold
--series-family-downside-threshold
```

Implementation:

```text
scripts/router_fallback_veto.py
scripts/evaluate_router_fallback_veto.py
```

The gates use only completed prior cuts. Current-cut errors are still used only
for offline scoring.

## Commands

Series-level strict sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-series-downside-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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

Series-family pair sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-series-family-only-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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
  --series-family-downside-threshold 0.0 \
  --series-family-downside-threshold 0.0001 \
  --series-family-downside-threshold 0.0005
```

Series + pair combined sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-series-family-downside-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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
  --series-family-downside-threshold 0.0 \
  --series-family-downside-threshold 0.0001 \
  --series-family-downside-threshold 0.0005
```

Readiness refresh:

```bash
uv run python scripts/evaluate_finance_readiness.py
```

## Results

| Policy | Extra lift vs fallback | Positive series | Negative series | Verdict |
|---|---:|---:|---:|---|
| previous best KNN fallback-veto | 0.316% | 7 | 3 | blocked |
| strict series-downside veto | 0.319% | 8 | 2 | improved but blocked |
| series-family pair veto | 0.231% | 7 | 3 | worse |
| series + pair combined | 0.210% | 7 | 3 | worse |

Best strict series-downside config:

```text
feature_mode: series
k: 50
regret_threshold: 0.0001
series_downside_threshold: 0.0005
delta_vs_fallback: 0.0002931205
relative_lift_vs_fallback: 0.318529%
positive / negative series: 8 / 2
vetoed windows: 1378
```

Remaining negative series:

```text
BAMLH0A0HYM2:realized_vol_20
DEXJPUS:realized_vol_20
```

## Interpretation

Fact: strict series-downside veto improved the current best router frontier:
extra lift rose from 0.316% to 0.319%, and negative routed series dropped from
3 to 2.

Fact: no tested policy reached `negative_routed_series_count = 0`.

Fact: series-family pair veto over-blocked useful routes and made DFF negative.

Inference: historical downside gates help but are not expressive enough to solve
the release blocker.

Recommendation: do not keep tuning hard thresholds. The next useful experiment
should use an explicit series-risk objective or a constrained selector that
optimizes aggregate lift while penalizing negative series.
