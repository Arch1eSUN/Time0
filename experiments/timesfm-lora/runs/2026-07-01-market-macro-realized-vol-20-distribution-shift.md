# 2026-07-01 Market Macro Realized Vol 20 Distribution Shift

## Goal

Diagnose whether the weak `cut5500` LoRA result is explained by distribution
shift between the training windows and the holdout windows.

## Tooling Change

Added:

```text
scripts/summarize_series_distribution.py
```

The script compares train vs holdout target distributions at the same grain as
the forecast metric:

```text
window future values
```

It reports:

```text
count, mean, std, min, p10, p50, p90, max
mean_delta_pct
std_ratio
p90_delta
```

## Cut-Point Summary

| Cut-point | LoRA MAE improvement | Holdout mean delta vs train | Holdout std ratio vs train |
|---:|---:|---:|---:|
| 4000 | 3.253180574182707% | 3.708459% | 1.186646 |
| 5000 | 1.225163054258857% | -1.994440% | 0.913917 |
| 5500 | 0.06920319934520795% | 5.950047% | 1.259878 |

`cut5500` is not weak because the aggregate holdout distribution is stable. It
is weak while the aggregate holdout mean and variance are both higher than the
training distribution.

## Cut5500 Per-Series Distribution Shift

| Series | LoRA MAE Improvement | Holdout Mean Delta | Holdout Std Ratio | Interpretation |
|---|---:|---:|---:|---|
| `DEXUSEU:realized_vol_20` | -2.037267% | -35.939341% | 0.403940 | much lower and narrower holdout |
| `DTWEXBGS:realized_vol_20` | -1.485192% | -49.670691% | 0.334922 | much lower and narrower holdout |
| `DGS10:realized_vol_20` | -1.142659% | -14.997429% | 0.455578 | lower and narrower holdout |
| `DCOILWTICO:realized_vol_20` | -0.174774% | -16.291626% | 0.532833 | lower and narrower holdout |
| `VIXCLS:realized_vol_20` | -0.095068% | -16.437615% | 0.548616 | lower and narrower holdout |
| `DEXJPUS:realized_vol_20` | -0.048423% | -13.602421% | 0.431117 | lower and narrower holdout |
| `DFF:realized_vol_20` | -0.045858% | 74.485666% | 1.355348 | much higher and wider holdout |
| `BAMLH0A0HYM2:realized_vol_20` | 0.469182% | 8.479435% | 0.721147 | slightly higher, narrower holdout |
| `SP500:realized_vol_20` | 1.403606% | 3.940449% | 0.433104 | slightly higher, narrower holdout |
| `DGS2:realized_vol_20` | 1.911722% | -17.676788% | 0.334233 | lower and narrower holdout, but LoRA helped |

## Interpretation

Fact: at `cut5500`, 7 of 10 series regressed vs zero-shot.

Fact: 6 of those 7 regressing series had materially lower and narrower holdout
target distributions than the training region.

Fact: `DFF` was the exception: its holdout mean rose by `74.485666%` and its
standard deviation rose to `1.355348x` of training.

Fact: the three improving series at `cut5500` were `BAMLH0A0HYM2`, `SP500`, and
`DGS2`.

Inference: `cut5500` mixes multiple regime shifts. Most series moved into a
lower-volatility, narrower holdout regime, while `DFF` moved into a much higher
volatility regime.

Inference: this is not good evidence for simply increasing LoRA rank. A larger
adapter may overfit the training distribution instead of fixing the regime
mismatch.

Recommendation: add target normalization or regime-aware evaluation before
running `r=8`.

## Next Experiment Direction

Do not publish and do not jump directly to `r=8`.

Next controlled direction:

```text
field=realized_vol_20
normalization=per-series train-window z-score or scale normalization
lora_r=4 first
same cutpoints: 4000, 5000, 5500
```

The question should be:

```text
Does normalization make cut5500 robust without losing cut4000/cut5000 gains?
```

Only after that should `r=8` be considered.
