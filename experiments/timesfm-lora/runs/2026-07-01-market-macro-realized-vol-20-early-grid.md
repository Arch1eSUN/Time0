# 2026-07-01 Market Macro Realized Vol 20 Early Grid

## Goal

Add earlier chronological cut points so router policies have more evidence
before `cut4000`.

Previous blocker:

```text
cut4000 had too little prior validation evidence.
multi-cut and recency-weighted guards could not beat latest-cut series_guarded.
```

This run adds:

```text
3000
3250
```

## Implementation

Updated:

```text
scripts/rolling_grid.py
```

Added grid:

```text
--grid early
```

Early grid cuts:

```text
3000, 3250, 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500
```

The existing `expanded` grid is unchanged.

## Commands

Train only new early adapters:

```bash
uv run python scripts/train_rolling_grid_adapters.py \
  --grid early \
  --cut 3000 \
  --cut 3250
```

Export only new early archives:

```bash
uv run python scripts/export_prediction_archives.py \
  --grid early \
  --cut 3000 \
  --cut 3250
```

Join full early grid:

```bash
uv run python scripts/join_prediction_archives.py \
  --grid early \
  --output reports/router-rows-early-market-macro-realized-vol-20-h20-r4.json
```

Evaluate router:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-early-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-market-macro-realized-vol-20-h20-r4.json
```

Attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-early-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-early-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --input reports/router-rows-early-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-early-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_risk_penalized \
  --input reports/router-rows-early-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-risk-penalized-early-market-macro-realized-vol-20-h20-r4.json
```

Generated adapters and reports remain ignored local artifacts.

## New Artifacts

New LoRA adapters:

```text
cut3000: full, recent1500, recent2000, recent3000
cut3250: full, recent1500, recent2000, recent3000
```

New prediction archives:

```text
2 cuts * 5 families = 10 archives
```

Joined early router rows:

```text
rows: 5500
cuts: 3000,3250,3500,3750,4000,4250,4500,4750,5000,5250,5500
```

## Fixed-Family Results

All cuts:

```text
zero-shot mean MAE:   0.0954784775
full mean MAE:        0.0944640066
recent1500 mean MAE:  0.0943295315
recent2000 mean MAE:  0.0938765687
recent3000 mean MAE:  0.0941845478
leaky oracle MAE:     0.0888025342
```

Best fixed family remains:

```text
recent2000
```

Leaky oracle headroom:

```text
MAE improvement vs zero-shot: 6.992092%
```

## Router Results

Routed cuts only:

| Policy | MAE | Improvement vs zero-shot | Delta vs fixed recent2000 | Verdict |
|---|---:|---:|---:|---|
| fixed recent2000 fallback | 0.0920232799 | 1.738276% | 0.0000000000 | safe baseline |
| best chronological diagnostic | 0.0919644635 | 1.801080% | 0.0000588164 | not fail-closed |
| validation-gated | 0.0921934286 | 1.556593% | -0.0001701487 | failed |
| series-guarded | 0.0921456132 | 1.607650% | -0.0001223333 | failed |
| series-risk-penalized | 0.0921345873 | 1.619423% | -0.0001113074 | failed |

Threshold sweep for validation-gated:

| min_validation_lift | Delta vs fallback |
|---:|---:|
| 0.000 | -0.0001599213 |
| 0.005 | -0.0001410594 |
| 0.010 | -0.0001701487 |
| 0.020 | -0.0001957226 |
| 0.030 | 0.0000000000 |
| 0.050 | 0.0000000000 |

The safest deployable result is still full fallback to `recent2000`.

## Cut-Level Attribution

Validation-gated policy:

| Cut | Delta vs fallback | Selected config |
|---:|---:|---|
| 3750 | 0.0013651981 | softmax |
| 4000 | 0.0024793740 | softmax |
| 4250 | -0.0033224244 | softmax |
| 4750 | -0.0001914564 | knn_regret_series_k100 |
| 5250 | -0.0020321786 | knn_regret_series_k25 |

Series-risk policy improves the damage but stays negative:

```text
validation-gated routed delta vs fallback: -0.0001701487
series-guarded routed delta vs fallback:   -0.0001223333
series-risk routed delta vs fallback:      -0.0001113074
```

Largest negative routed series under series-risk:

```text
DFF delta sum:     -0.9585108104
DEXJPUS delta sum: -0.0148636323
DGS2 delta sum:    -0.0143766340
```

## Interpretation

Fact: the early grid increased aligned router rows from 4500 to 5500.

Fact: fixed `recent2000` remains the best deployable policy.

Fact: `knn_regret_no_series_k25` slightly beats fallback as a chronological
diagnostic, but no validation-gated fail-closed policy beats fallback.

Inference: router headroom exists, but the current gate and feature set cannot
capture it causally.

Recommendation: stop adding hard gates or more nearby cut points for now. The
next controlled experiment should add richer no-leak runtime features for regime
detection, then rerun the early grid.

## Current Verdict

```text
early grid status: completed
new net deployable lift: none
best safe policy: fixed recent2000
publication: blocked
next step: richer no-leak runtime features
```
