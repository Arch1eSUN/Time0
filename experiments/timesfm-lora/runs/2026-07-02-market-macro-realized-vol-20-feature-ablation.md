# 2026-07-02 Market Macro Realized Vol 20 Feature Ablation

## Goal

Identify which no-leak runtime feature groups caused the first positive MAE
validation-gated router result.

Previous checkpoint:

```text
full regime feature set validation-gated routed MAE: 0.0917723992
fixed recent2000 routed MAE:                     0.0920232799
delta vs fallback:                              0.0002508807
```

## Implementation

Added:

```text
scripts/ablate_router_features.py
```

The script copies a router-row report and removes selected runtime feature
groups while preserving labels, actuals, and errors outside `runtime_features`.

No-leak guard:

```text
The ablation script rejects forbidden runtime keys:
actual, mae, smape, best_family, family_errors, label
```

## Commands

Create ablated router rows:

```bash
uv run python scripts/ablate_router_features.py \
  --preset alignment-normalized \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Evaluate:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/evaluate_prediction_router.py \
  --metric smape \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-smape-market-macro-realized-vol-20-h20-r4.json
```

Attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Presets

| Preset | Kept feature groups |
|---|---|
| baseline | `context`, `prediction_summaries`, `prediction_disagreement` |
| context-regime | baseline + `context_regime` |
| normalized-disagreement | baseline + `prediction_disagreement_normalized` |
| alignment | baseline + `prediction_context_alignment` |
| regime-alignment | baseline + `context_regime`, `prediction_context_alignment` |
| alignment-normalized | baseline + `prediction_context_alignment`, `prediction_disagreement_normalized` |
| regime-no-alignment | baseline + `context_regime`, `prediction_disagreement_normalized` |
| all | all enriched groups |

## Ablation Results

Routed cuts only, MAE:

| Preset | Validation MAE | Delta vs fallback | Best diagnostic | Diagnostic delta |
|---|---:|---:|---|---:|
| baseline | 0.0921934286 | -0.0001701487 | knn_regret_no_series_k25 | 0.0000588164 |
| context-regime | 0.0919376472 | 0.0000856326 | knn_regret_series_k50 | 0.0001107554 |
| normalized-disagreement | 0.0924055351 | -0.0003822553 | knn_regret_series_k50 | 0.0000700370 |
| alignment | 0.0918978930 | 0.0001253869 | knn_regret_series_k50 | 0.0003071304 |
| regime-alignment | 0.0920801016 | -0.0000568217 | knn_regret_series_k25 | 0.0002975609 |
| alignment-normalized | 0.0917558798 | 0.0002674001 | knn_regret_no_series_k25 | 0.0004631997 |
| regime-no-alignment | 0.0921409215 | -0.0001176417 | knn_regret_series_k100 | 0.0000506950 |
| all | 0.0917723992 | 0.0002508807 | knn_regret_series_k25 | 0.0003902831 |

Best default gate:

```text
alignment-normalized
```

Best diagnostic headroom:

```text
alignment-normalized
```

## Robustness Checks

`alignment-normalized`, routed cuts only:

| Check | Metric | Delta vs fixed recent2000 |
|---|---:|---:|
| MAE validation-gated | 0.0917558798 | 0.0002674001 |
| SMAPE validation-gated | 0.1846992897 | 0.0001627004 |
| MAE series-guarded | 0.0920084609 | 0.0000148190 |
| MAE series-risk | 0.0920084609 | 0.0000148190 |

Series attribution under default validation-gated MAE:

```text
positive routed series: 4
negative routed series: 6
```

Series attribution under series-guarded MAE:

```text
positive routed series: 6
negative routed series: 4
```

## Interpretation

Fact: prediction-context alignment is the core useful feature group.

Fact: normalized disagreement is harmful by itself, but becomes useful when
combined with prediction-context alignment.

Fact: adding `context_regime` on top of alignment-normalized slightly reduces
the validation-gated MAE result.

Inference: the router benefits more from "how forecasts relate to the current
context" than from standalone context-regime scalars.

Recommendation: keep `alignment-normalized` as the current best feature surface.
Do not promote yet; the series-guarded lift is positive but too small. The next
step should tune the risk policy around this feature surface rather than adding
more raw context features.

## Current Verdict

```text
best feature preset: alignment-normalized
MAE validation gate: positive
SMAPE validation gate: positive
series guard: barely positive
promotion status: blocked until broader series stability
```
