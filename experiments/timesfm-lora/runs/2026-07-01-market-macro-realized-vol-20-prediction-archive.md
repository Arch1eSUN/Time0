# 2026-07-01 Market Macro Realized Vol 20 Prediction Archive

## Goal

Add prediction-level instrumentation so the next router can learn from
per-window evidence instead of aggregate report metrics.

This run is not a new LoRA training run.

It extends the existing TimesFM evaluation surface:

```text
scripts/evaluate_timesfm.py --predictions-output <path>
```

## Why This Was Needed

The first no-leak router used historical aggregate reports:

```text
global_history_best routed-cuts MAE improvement: -1.265%
per_series_history_best routed-cuts MAE improvement: -0.069%
leaky_current_cut_best_global average MAE improvement: 2.453%
```

Interpretation:

```text
Adapter selection has upside, but aggregate historical MAE is too coarse as the
router signal.
```

The next router needs records at this grain:

```text
one forecast window -> pre-forecast features + model prediction + actual future
```

## Implementation

Changed:

```text
scripts/evaluate_timesfm.py
```

New optional argument:

```text
--predictions-output reports/predictions-*.json
```

Default behavior is unchanged. When `--predictions-output` is omitted,
`evaluate_timesfm.py` still writes only the aggregate report.

When enabled, it writes a JSON archive with:

| Field | Meaning |
|---|---|
| `window_id` | stable join key: `series_id:start_index` |
| `series_id` | source series and target field |
| `start_index` | chronological window start |
| `features` | pre-forecast context features |
| `actual` | true future horizon |
| `predicted` | model forecast horizon |
| `mae` | window-level MAE |
| `smape` | window-level SMAPE |

Feature set:

```text
past_last
past_mean
past_std
past_min
past_max
past_trend
```

## Smoke Runs

### LoRA Adapter

```bash
uv run python scripts/evaluate_timesfm.py \
  --csv data/market/daily_market_series.csv \
  --field realized_vol_20 \
  --model-id .hf-cache/timesfm-2.5-200m-transformers \
  --adapter-dir adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train5500 \
  --context-len 128 \
  --horizon-len 20 \
  --max-windows 20 \
  --skip-windows 5500 \
  --output reports/smoke-timesfm-lora-realized-vol-20-recent2000-prediction-archive.json \
  --predictions-output reports/predictions-smoke-timesfm-lora-realized-vol-20-recent2000-train5500-skip5500.json
```

Result:

```text
windows: 20
series: 10
device: mps
MAE: 0.05884612045210917
SMAPE: 0.16560844820366266
prediction_records: 20
```

### Zero-Shot

```bash
uv run python scripts/evaluate_timesfm.py \
  --csv data/market/daily_market_series.csv \
  --field realized_vol_20 \
  --model-id .hf-cache/timesfm-2.5-200m-transformers \
  --context-len 128 \
  --horizon-len 20 \
  --max-windows 20 \
  --skip-windows 5500 \
  --output reports/smoke-timesfm-zero-shot-realized-vol-20-prediction-archive.json \
  --predictions-output reports/predictions-smoke-timesfm-zero-shot-realized-vol-20-skip5500.json
```

Result:

```text
windows: 20
series: 10
device: mps
MAE: 0.057759466783332866
SMAPE: 0.1619342552566055
prediction_records: 20
```

The smoke metric is not used as adapter evidence because it only covers 20
windows. The point of this run is to validate the archive interface.

## Archive Validation

Validation command checked:

```text
zero-shot and LoRA archives have identical window_id order
first record has 20 actual values and 20 predicted values
feature keys match the router feature contract
```

Observed:

```text
archives_aligned 20
first_window_id VIXCLS:realized_vol_20:550
feature_keys past_last,past_max,past_mean,past_min,past_std,past_trend
zero_first_mae 0.05017235472868775
lora_first_mae 0.050924211827857356
```

## Interpretation

Fact: `evaluate_timesfm.py` can now emit prediction-level archives for both
zero-shot and LoRA adapter inference.

Fact: zero-shot and LoRA records align by `window_id`, which makes later
adapter-disagreement features possible.

Fact: each record separates pre-forecast features from future actuals and
predictions.

Inference: the next router can be built from archives without changing the
training script or the base data windowing logic.

Recommendation: generate full 500-window archives for zero-shot and all four
candidate adapter families across `cut4000`, `cut5000`, and `cut5500`, then
build a joiner that creates adapter-disagreement features and no-leak router
training rows.

## Next Experiment Direction

Next controlled step:

```text
method=full prediction archive export
cuts=4000,5000,5500
families=zero-shot,full,recent1500,recent2000,recent3000
target=realized_vol_20
output=reports/predictions-*.json
```

Then:

```text
method=prediction archive joiner
features=past statistics + adapter disagreement + series identity
label=lowest future error adapter family
validation=nested pre-holdout only
```
