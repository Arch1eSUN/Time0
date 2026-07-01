# 2026-07-02 Market Macro Realized Vol 20 Fallback Veto

## Goal

Test whether a no-leak fallback-veto layer can predict risky KNN-regret
overrides before the current cut is scored.

Previous checkpoint:

```text
best aggregate before this run:
  knn-regret validation_gated mvl=0.0
  MAE delta: 0.0002705342
  positive/negative routed series: 6/4

best research checkpoint before this run:
  knn-regret validation_gated mvl=0.005
  MAE delta: 0.0002687244
  positive/negative routed series: 7/3

best conservative downside-budget candidate:
  series_risk_penalized mvl=0.005 min_series=-0.0025 decay=0.25
  MAE delta: 0.0002451542
  positive/negative routed series: 8/2
```

The question for this run:

```text
Can we learn a window-level no-leak veto signal that blocks risky KNN-regret
overrides while keeping useful overrides?
```

## Implementation

Added:

```text
scripts/evaluate_router_fallback_veto.py
```

The script keeps the base router unchanged:

```text
base router:
  candidate_set = knn-regret
  policy = validation_gated
```

Then it trains a local veto signal from completed prior cuts only:

```text
historical example:
  runtime row features
  selected adapter family
  selected_error - fallback_error

current decision:
  if nearest historical override examples have mean regret above threshold,
  replace the selected adapter with fallback recent2000
```

No current-cut labels are used to decide current-cut vetoes.

## Commands

Default veto sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --candidate-set knn-regret \
  --min-validation-lift 0.005 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-knn-regret-mvl005-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Refined global veto sweep:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --candidate-set knn-regret \
  --min-validation-lift 0.005 \
  --feature-mode global \
  --veto-k 25 \
  --veto-k 50 \
  --veto-k 75 \
  --veto-k 100 \
  --regret-threshold 0 \
  --regret-threshold 0.000025 \
  --regret-threshold 0.00005 \
  --regret-threshold 0.000075 \
  --regret-threshold 0.0001 \
  --regret-threshold 0.000125 \
  --regret-threshold 0.00015 \
  --regret-threshold 0.0002 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-knn-regret-mvl005-global-refined-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

High-threshold check:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --candidate-set knn-regret \
  --min-validation-lift 0.005 \
  --feature-mode global \
  --veto-k 50 \
  --veto-k 75 \
  --regret-threshold 0.0002 \
  --regret-threshold 0.00025 \
  --regret-threshold 0.0003 \
  --regret-threshold 0.0004 \
  --regret-threshold 0.0005 \
  --regret-threshold 0.00075 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-knn-regret-mvl005-global-high-threshold-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Fair comparison against `mvl=0.0`:

```bash
uv run python scripts/evaluate_router_fallback_veto.py \
  --candidate-set knn-regret \
  --min-validation-lift 0 \
  --feature-mode global \
  --veto-k 50 \
  --regret-threshold 0.0001 \
  --regret-threshold 0.00015 \
  --regret-threshold 0.0002 \
  --regret-threshold 0.00025 \
  --regret-threshold 0.0003 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-fallback-veto-knn-regret-mvl0-global-refined-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Generated JSON reports remain ignored local artifacts.

## Results

Baseline before veto:

| Policy | Min validation | MAE delta | Positive / Negative series |
|---|---:|---:|---:|
| `validation_gated` | 0.000 | 0.0002705342 | 6 / 4 |
| `validation_gated` | 0.005 | 0.0002687244 | 7 / 3 |
| `series_risk_penalized` | 0.005 | 0.0002451542 | 8 / 2 |

Best fallback-veto result:

| Base | Feature mode | k | Regret threshold | Vetoed windows | MAE delta | Positive / Negative series |
|---|---|---:|---:|---:|---:|---:|
| `mvl=0.005` | `global` | 50 | 0.0002 | 304 | 0.0003088776 | 9 / 1 |

Refined global sweep top rows:

| Rank | Feature mode | k | Threshold | MAE delta | Positive / Negative series | Vetoed windows |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `global` | 50 | 0.000200 | 0.0003088776 | 9 / 1 | 304 |
| 2 | `global` | 50 | 0.000150 | 0.0003043504 | 9 / 1 | 337 |
| 3 | `global` | 50 | 0.000125 | 0.0002983225 | 9 / 1 | 355 |
| 4 | `global` | 50 | 0.000100 | 0.0002912377 | 7 / 3 | 376 |
| 5 | `global` | 50 | 0.000075 | 0.0002855062 | 8 / 2 | 394 |
| 6 | `global` | 50 | 0.000050 | 0.0002776343 | 8 / 2 | 431 |

High-threshold check:

| Feature mode | k | Threshold | MAE delta | Positive / Negative series | Vetoed windows |
|---|---:|---:|---:|---:|---:|
| `global` | 50 | 0.000200 | 0.0003088776 | 9 / 1 | 304 |
| `global` | 50 | 0.000250 | 0.0003037471 | 7 / 3 | 272 |
| `global` | 50 | 0.000300 | 0.0003015125 | 7 / 3 | 254 |
| `global` | 50 | 0.000400 | 0.0002754654 | 7 / 3 | 229 |

Fair comparison:

| Base | Feature mode | k | Threshold | MAE delta | Positive / Negative series |
|---|---|---:|---:|---:|---:|
| `mvl=0.000` | `global` | 50 | 0.0002 | 0.0003038838 | 6 / 4 |
| `mvl=0.005` | `global` | 50 | 0.0002 | 0.0003088776 | 9 / 1 |

## Best Result Attribution

Routed cuts only:

```text
selected_metric: 0.0917144023
fallback_metric: 0.0920232799
MAE delta vs fallback: 0.0003088776
relative lift vs fallback: 0.0033565156
vetoed windows: 304
positive/negative routed series: 9/1
```

Selected counts:

```text
full: 363
recent1500: 502
recent2000: 2766
recent3000: 569
zero-shot: 800
```

Top positive series:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0012367423 |
| `DFF:realized_vol_20` | 0.0012003241 |
| `DGS2:realized_vol_20` | 0.0004388087 |

Only negative series:

| Series | MAE delta vs fallback |
|---|---:|
| `DEXJPUS:realized_vol_20` | -0.0000342279 |

## Interpretation

Fact: The fallback-veto layer produced a new best aggregate result:
`0.0003088776` MAE delta vs fallback.

Fact: The same row also improved the routed-series split to `9/1`.

Fact: `mvl=0.005 + veto` beat `mvl=0.0 + veto` on both aggregate delta and
series spread.

Inference: The useful signal is not just "route more." The useful signal is
"route with a moderate global validation gate, then veto historically risky
overrides at the window level."

Recommendation: Promote `knn-regret validation_gated mvl=0.005 + global
fallback-veto k50 threshold=0.0002` to the current best research checkpoint.
Do not call it release-ready until the same veto is tested on a later archive
or a different target.

## Current Verdict

```text
frontier moved: yes
best previous aggregate: 0.0002705342
new best aggregate: 0.0003088776
series split improved: 9/1
promotion status: research checkpoint only
next step: export this veto as a formal router policy and test on another target or later archive
```
