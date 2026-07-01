# 2026-07-01 Market Macro Realized Vol 20 Adapter Router

## Goal

Test whether adapter routing can beat a single fixed-window LoRA adapter without
using holdout results to choose the adapter.

This is the first routing checkpoint after the fixed-window sweep:

```text
full-history
recent1500
recent2000
recent3000
```

## Experiment Design

This run does not train a new adapter.

It reads existing rolling evaluation reports and tests two no-leak routing
policies:

| Policy | Selection grain | Selection data | Evaluation data |
|---|---|---|---|
| `global_history_best` | one adapter family per cut | prior cut reports only | current cut |
| `per_series_history_best` | one adapter family per series per cut | prior cut reports only | current cut |

Cold start:

```text
cut4000 has no prior cut, so it defaults to full-history.
cut5000 can only look at cut4000.
cut5500 can only look at cut4000 and cut5000.
```

Guardrail:

```text
The current cut is never used for no-leak route selection.
```

Script:

```text
scripts/evaluate_adapter_router.py
```

Generated local report:

```text
reports/timesfm-router-market-macro-realized-vol-20-h20-r4-history-best.json
```

## Command

```bash
uv run python scripts/evaluate_adapter_router.py \
  --metric mae \
  --horizon-len 20 \
  --cold-start-family full \
  --zero-shot 4000=reports/timesfm-zero-shot-market-macro-realized-vol-20-h20-holdout500-skip4000.json \
  --zero-shot 5000=reports/timesfm-zero-shot-market-macro-realized-vol-20-h20-holdout500-skip5000.json \
  --zero-shot 5500=reports/timesfm-zero-shot-market-macro-realized-vol-20-h20-holdout500-skip5500.json \
  --candidate full:4000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-train4000-holdout500-skip4000.json \
  --candidate full:5000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-holdout500-skip5000.json \
  --candidate full:5500=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-train5500-holdout500-skip5500.json \
  --candidate recent1500:4000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent1500-train4000-holdout500-skip4000.json \
  --candidate recent1500:5000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent1500-train5000-holdout500-skip5000.json \
  --candidate recent1500:5500=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent1500-train5500-holdout500-skip5500.json \
  --candidate recent2000:4000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent2000-train4000-holdout500-skip4000.json \
  --candidate recent2000:5000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent2000-train5000-holdout500-skip5000.json \
  --candidate recent2000:5500=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent2000-train5500-holdout500-skip5500.json \
  --candidate recent3000:4000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent3000-train4000-holdout500-skip4000.json \
  --candidate recent3000:5000=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent3000-train5000-holdout500-skip5000.json \
  --candidate recent3000:5500=reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-step200-recent3000-train5500-holdout500-skip5500.json \
  --output reports/timesfm-router-market-macro-realized-vol-20-h20-r4-history-best.json
```

## Results

### Fixed Families

| Family | Avg MAE | Avg MAE gain | Avg SMAPE gain |
|---|---:|---:|---:|
| `full` | 0.107802312 | 1.490% | 0.889% |
| `recent1500` | 0.108919098 | 0.470% | -0.670% |
| `recent2000` | 0.107401187 | 1.857% | 0.838% |
| `recent3000` | 0.107717513 | 1.568% | 0.718% |

### Routing Policies

| Policy | Scope | Avg MAE | Avg MAE gain | Avg SMAPE gain | Verdict |
|---|---|---:|---:|---:|---|
| `global_history_best` | all cuts | 0.109046436 | 0.353% | -0.313% | not useful |
| `global_history_best` | routed cuts only | 0.106686764 | -1.265% | -1.032% | failed |
| `per_series_history_best` | all cuts | 0.108206387 | 1.121% | 0.334% | below fixed recent2000 |
| `per_series_history_best` | routed cuts only | 0.105426692 | -0.069% | -0.072% | neutral/failed |

### Leaky Upper Bound

| Policy | Avg MAE | Avg MAE gain | Avg SMAPE gain | Verdict |
|---|---:|---:|---:|---|
| `leaky_current_cut_best_global` | 0.106748241 | 2.453% | 0.791% | not valid, but informative |

The leaky policy selects the best family using the same cut being evaluated:

```text
cut4000 -> recent1500
cut5000 -> full
cut5500 -> recent2000
```

This is not a deployable result because it uses the answer key. It is useful
because it shows that correct adapter-family selection could pass the 2%
average MAE threshold if the selection rule were learned from valid pre-holdout
signals.

## Interpretation

Fact: the best fixed family remains `recent2000`, with `1.857%` average MAE
gain.

Fact: `global_history_best` regressed on routed cuts. It chose `recent1500` for
`cut5000` because `recent1500` won `cut4000`, then failed on `cut5000`.

Fact: `per_series_history_best` improved `cut5500` by `0.819%`, but regressed
`cut5000` by `1.531%`.

Fact: leaky current-cut selection reaches `2.453%` average MAE gain, above the
Promotion Ready threshold, but it is invalid.

Inference: adapter choice matters, but historical average metric is too weak as
a router signal.

Inference: the next routing experiment needs window-level predictions or
pre-holdout regime features. Per-series aggregate MAE is too coarse.

Recommendation: do not publish and do not move to `r=8` yet. Add prediction
archive support to `evaluate_timesfm.py`, then build a nested validation router
from pre-holdout features such as recent volatility level, volatility trend,
series identity, and adapter disagreement.

## Next Experiment Direction

Next controlled direction:

```text
method=prediction-level router instrumentation
target=realized_vol_20
candidate_adapters=full-history,recent1500,recent2000,recent3000
new artifact=per-window prediction archive
router_features=series_id,recent_mean,recent_std,last_value,adapter_disagreement
validation=pre-holdout only
```

Question:

```text
Can a router learn adapter-family selection from features available before the
forecast, instead of from previous aggregate cut metrics?
```
