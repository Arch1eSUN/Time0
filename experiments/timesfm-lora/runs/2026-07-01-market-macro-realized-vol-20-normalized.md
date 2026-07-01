# 2026-07-01 Market Macro Realized Vol 20 Normalized Target

## Goal

Test whether per-series train-window z-score normalization makes the
`realized_vol_20` LoRA adapter more robust across rolling holdout cut-points,
especially the weak `cut5500` split.

## Tooling Change

Added:

```text
scripts/write_normalized_series_csv.py
```

The script computes normalization statistics from training windows only:

```text
z = (value - train_future_mean) / train_future_std
```

Normalization grain:

```text
train_window_future_values
```

This avoids using holdout values to compute mean/std.

Generated local data artifacts:

```text
data/market/normalized-realized-vol-20-zscore-train4000.csv
data/market/normalized-realized-vol-20-zscore-train5000.csv
data/market/normalized-realized-vol-20-zscore-train5500.csv
```

Generated local metadata reports:

```text
reports/normalization-realized-vol-20-train4000.json
reports/normalization-realized-vol-20-train5000.json
reports/normalization-realized-vol-20-train5500.json
```

## Training Setup

| Setting | Value |
|---|---|
| Base model | `.hf-cache/timesfm-2.5-200m-transformers` |
| Target family | `realized_vol_20_zscore_train*` |
| Context length | 128 |
| Horizon length | 20 |
| LoRA rank | 4 |
| LoRA alpha | 8 |
| LoRA dropout | 0.05 |
| Max steps | 200 |
| Batch size | 2 |
| Device | MPS |

Trained local adapters:

```text
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-train4000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-train5000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-train5500
```

All training and holdout splits were balanced across 10 series:

| Cut-point | Train windows | Train per series | Holdout windows | Holdout per series |
|---:|---:|---:|---:|---:|
| 4000 | 4000 | 400 | 500 | 50 |
| 5000 | 5000 | 500 | 500 | 50 |
| 5500 | 5500 | 550 | 500 | 50 |

## Evaluation Results

Metric values are in normalized units. They should not be directly compared to
raw-space MAE from previous runs. Relative improvement vs zero-shot is still a
valid adaptation signal within each cut-point.

| Cut-point | Last-value MAE | Zero-shot MAE | LoRA MAE | MAE Improvement | Zero-shot SMAPE | LoRA SMAPE | SMAPE Improvement | Per-series MAE wins |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.499572175 | 0.498800980 | 0.491267123 | 1.510% | 0.764127827 | 0.769457399 | -0.697% | 7/10 |
| 5000 | 0.475717191 | 0.453603232 | 0.446293657 | 1.611% | 1.092148615 | 1.087371854 | 0.437% | 9/10 |
| 5500 | 0.519281951 | 0.520132411 | 0.521097160 | -0.185% | 0.854735333 | 0.857036655 | -0.269% | 3/10 |

Average MAE improvement:

```text
0.978786%
```

Average SMAPE improvement:

```text
-0.176447%
```

## Cut5500 Per-Series Result

| Series | MAE improvement vs zero-shot |
|---|---:|
| `BAMLH0A0HYM2:realized_vol_20_zscore_train5500` | 0.469% |
| `DCOILWTICO:realized_vol_20_zscore_train5500` | -0.175% |
| `DEXJPUS:realized_vol_20_zscore_train5500` | -0.048% |
| `DEXUSEU:realized_vol_20_zscore_train5500` | -2.037% |
| `DFF:realized_vol_20_zscore_train5500` | -0.046% |
| `DGS10:realized_vol_20_zscore_train5500` | -1.143% |
| `DGS2:realized_vol_20_zscore_train5500` | 1.912% |
| `DTWEXBGS:realized_vol_20_zscore_train5500` | -1.485% |
| `SP500:realized_vol_20_zscore_train5500` | 1.404% |
| `VIXCLS:realized_vol_20_zscore_train5500` | -0.095% |

## Interpretation

Fact: normalized LoRA improved MAE at `cut4000` and `cut5000`.

Fact: normalized LoRA regressed MAE and SMAPE at `cut5500`.

Fact: normalized LoRA improved only 3 of 10 series at `cut5500`.

Fact: average normalized MAE improvement was `0.978786%`, below the
`2%` Promotion Ready threshold.

Inference: per-series z-score normalization preserved some adaptation signal but
did not solve the weak `cut5500` regime-shift problem.

Inference: the blocker is less likely to be simple cross-series scale mismatch.
It is more likely related to recency, regime mixing, or target dynamics.

Recommendation: do not publish this adapter family and do not jump directly to
`r=8`. The next controlled experiment should test recent-window training before
capacity scaling.

## Next Experiment Direction

Next controlled direction:

```text
field=realized_vol_20
training_window=recent-only rolling window before each cut-point
example: train last 2000 windows before holdout
lora_r=4
lora_alpha=8
max_steps=200
cutpoints=4000,5000,5500
```

Question:

```text
Does recent-window fine-tuning handle cut5500 better than full-history
fine-tuning?
```

If recent-window training improves `cut5500` without collapsing `cut4000` and
`cut5000`, then the project should pursue regime-aware adapter selection or
recency-weighted training. If it fails, then test target dynamics such as
relative volatility or log-volatility before increasing LoRA rank.
