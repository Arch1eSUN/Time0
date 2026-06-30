# 2026-07-01 Market Macro Realized Vol 20 H20 R4

## Goal

Test whether `realized_vol_20` is a better market/macro-risk target than raw
`level` or `log_change` for TimesFM 2.5 LoRA adaptation.

## Why This Target

Previous targets:

```text
level: failed Candidate Success
log_change: partial signal, MAE improved but SMAPE regressed
```

This target:

```text
field=realized_vol_20
```

Reason:

```text
realized_vol_20 is closer to risk forecasting than raw price/level prediction.
It also avoids some near-zero denominator instability from log_change SMAPE.
```

## Data Split

Training windows:

```text
skip_windows=0
max_windows=5000
500 windows per series
```

Holdout windows:

```text
skip_windows=5000
max_windows=500
50 windows per series
```

Series coverage:

```text
BAMLH0A0HYM2, DCOILWTICO, DEXJPUS, DEXUSEU, DFF,
DGS10, DGS2, DTWEXBGS, SP500, VIXCLS
```

## Holdout Baselines

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 0.09038209915835001 | 0.20442511989606849 |
| Seasonal naive | 0.12437439321615 | 0.29747420644269 |
| TimesFM 2.5 zero-shot | 0.0796282537318497 | 0.1877752198880728 |

## LoRA Training

Adapter:

```text
adapters/market-macro-realized-vol-20-h20-r4-step200-balanced
```

Config:

```text
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
lora_dropout=0.05
batch_size=2
max_steps=200
learning_rate=5e-5
seed=7
device=mps
```

Trainable parameters:

```text
1,382,912 / 232,672,192 = 0.5944%
```

Observed logged losses:

```text
step=1 loss=0.93052828
step=20 loss=0.33145612
step=40 loss=1.23565519
step=60 loss=1.69736600
step=80 loss=0.77752662
step=100 loss=3.21070695
step=120 loss=0.44589117
step=140 loss=0.46694925
step=160 loss=0.07944214
step=180 loss=1.25532508
step=200 loss=0.59476203
```

## Holdout Result

| Model | MAE | SMAPE |
|---|---:|---:|
| TimesFM 2.5 zero-shot | 0.0796282537318497 | 0.1877752198880728 |
| LoRA r4 step200 realized_vol_20 | 0.07865267778637558 | 0.18479685396576195 |

Relative improvement vs TimesFM zero-shot:

```text
MAE improvement: 1.225163054258857%
SMAPE improvement: 1.5861336357833395%
```

Relative improvement vs last-value naive:

```text
MAE improvement: 12.977593440736984%
```

## Interpretation

Fact: the adapter improved both MAE and SMAPE vs TimesFM 2.5 zero-shot on the
same chronological holdout split.

Fact: the adapter improved MAE by more than the 1% Candidate Success threshold
defined in `SUCCESS_CRITERIA.md`.

Fact: this is still only one holdout cut-point.

Inference: `realized_vol_20` is the first target in this project with a clean
single-split LoRA win.

Recommendation: treat this adapter as Candidate Success, not Promotion Ready.
The next experiment should run rolling holdout cut-points before increasing
LoRA rank or publishing any adapter.

## Next Step

Run the same adapter recipe against at least three chronological holdout
cut-points:

```text
skip_windows=4000 max_windows=500
skip_windows=5000 max_windows=500
skip_windows=6000 max_windows=500
```

Promotion remains blocked until the average primary-metric improvement is at
least 2% and the adapter does not depend on one favorable holdout segment.
