# 2026-07-01 Market Macro Realized Vol 20 Expanded Grid

## Goal

Increase chronological supervision for the prediction-level adapter router.

The previous router experiment had only 3 cuts:

```text
4000,5000,5500
```

That gave too few prior-validation decisions. This run expands the rolling grid
so the router can be tested across more time positions before we decide whether
learned adapter selection is real.

## Implementation

Added:

```text
scripts/rolling_grid.py
scripts/train_rolling_grid_adapters.py
```

Updated:

```text
scripts/export_prediction_archives.py
scripts/join_prediction_archives.py
scripts/evaluate_prediction_router.py
```

The grid definition is now centralized in `rolling_grid.py` so training,
archive export, and router-row joining share one cut/family contract.

## Expanded Grid

Cuts:

```text
3500,3750,4000,4250,4500,4750,5000,5250,5500
```

Families:

```text
zero-shot,full,recent1500,recent2000,recent3000
```

Training coverage:

```text
new adapters trained: 24
existing adapters reused: 12
zero-shot families: no adapter training
```

Archive coverage:

```text
prediction archives: 45
router rows: 4500
windows per cut/family: 500
alignment key: window_id
```

## Commands

```bash
uv run python -m py_compile \
  scripts/rolling_grid.py \
  scripts/train_rolling_grid_adapters.py \
  scripts/export_prediction_archives.py \
  scripts/join_prediction_archives.py \
  scripts/evaluate_prediction_router.py

uv run python scripts/train_rolling_grid_adapters.py --grid expanded

uv run python scripts/export_prediction_archives.py --grid expanded

uv run python scripts/join_prediction_archives.py \
  --grid expanded \
  --output reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-expanded-market-macro-realized-vol-20-h20-r4.json
```

Generated adapters and reports remain local ignored artifacts.

## Router-Row Results

All 4500 rows:

| Family | Mean MAE |
|---|---:|
| zero-shot | 0.0945869804 |
| full | 0.0933575549 |
| recent1500 | 0.0932794720 |
| recent2000 | 0.0928097800 |
| recent3000 | 0.0931267339 |

Best fixed family:

```text
recent2000
```

Label counts:

| Best family label | Rows |
|---|---:|
| zero-shot | 1027 |
| full | 617 |
| recent1500 | 1107 |
| recent2000 | 890 |
| recent3000 | 859 |

Leaky oracle:

| Metric | Value |
|---|---:|
| MAE | 0.0876920517 |
| MAE improvement vs zero-shot | 7.289511% |
| SMAPE improvement vs zero-shot | 5.848610% |

Interpretation:

```text
Adapter selection has large theoretical upside, but the leaky oracle uses
future errors and is not deployable evidence.
```

## No-Leak Router Results

Routed cuts only:

| Policy | MAE | MAE improvement vs zero-shot |
|---|---:|---:|
| fixed `recent2000` | 0.0958798640 | 1.987592% |
| best learned diagnostic: `knn_regret_no_series_k50` | 0.0959988452 | 1.865964% |
| validation-gated router | 0.0957538599 | 2.116398% |

Validation-gated router vs fixed fallback:

```text
absolute MAE delta: 0.0001260041
relative lift over fallback MAE: 0.131419%
```

Per-cut selected config:

| Cut | Selected config | MAE improvement vs zero-shot |
|---:|---|---:|
| 3500 | fixed:recent2000 | 0.640621% |
| 3750 | fixed:recent2000 | 0.816933% |
| 4000 | softmax_series | 3.635257% |
| 4250 | knn_regret_no_series_k50 | 6.677896% |
| 4500 | fixed:recent2000 | 1.500391% |
| 4750 | fixed:recent2000 | 0.669219% |
| 5000 | fixed:recent2000 | 0.678605% |
| 5250 | fixed:recent2000 | -0.812779% |
| 5500 | fixed:recent2000 | 2.010708% |

## Interpretation

Fact: expanding from 3 cuts to 9 cuts improved the fixed fallback evidence.
`recent2000` remains the strongest fixed family.

Fact: the best standalone learned diagnostic still does not beat fixed
`recent2000` on routed cuts.

Fact: the validation-gated policy now beats fixed `recent2000` by a small
amount because it switches only on cuts where prior validation clears the gate.

Inference: the router signal is becoming more useful as chronological
supervision increases, but the extra lift over fallback is still tiny.

Recommendation: do not publish the router yet. Keep the expanded grid as the
valid research surface and next inspect per-series behavior before any Moirai
or Hugging Face release claim.

## Current Verdict

```text
adapter family: useful research candidate
best fixed adapter: recent2000
router: promising but not promotion-ready
publication: blocked
next step: per-series review of expanded validation-gated selections
```
