# 2026-07-01 Market Macro Level H20 R4 Holdout

## Goal

Continue TimesFM 2.5 LoRA training and evaluate whether longer training improves
unseen balanced holdout windows.

## Change From Previous Round

Added `skip_windows` support to separate train and holdout windows.

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

## LoRA Run

Adapter:

```text
adapters/market-macro-level-h20-r4-step1000-balanced
```

Configuration:

```text
field=level
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
lora_dropout=0.05
batch_size=2
max_steps=1000
device=mps
trainable_params=1,382,912
all_params=232,672,192
trainable_percent=0.5944
```

Observed training losses:

```text
step=1 loss=0.17880824
step=100 loss=0.86686522
step=200 loss=0.93479133
step=300 loss=0.42192423
step=400 loss=0.51295173
step=500 loss=0.88093245
step=600 loss=1.70393884
step=700 loss=0.18508051
step=800 loss=0.82756817
step=900 loss=1.36308241
step=1000 loss=0.15799338
```

## Holdout Results

500 balanced holdout windows, 50 per series.

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 6.8866578500000015 | 0.04814407659052045 |
| Seasonal naive | 12.616396260000002 | 0.0690725444758241 |
| TimesFM 2.5 zero-shot | 5.477592374297006 | 0.04519216076482665 |
| LoRA r4 step200 | 5.778416210730518 | 0.04560542206655007 |
| LoRA r4 step1000 | 6.478898421882549 | 0.04788307865447745 |

## Result

Fact: TimesFM 2.5 zero-shot won this holdout evaluation.

Fact: r4 step1000 was worse than r4 step200 on holdout.

Inference: longer training overfit or adapted to early-window distribution in a
way that did not generalize to later windows.

Recommendation: do not increase LoRA rank yet. Next run should add validation
checkpoints or train on transformed targets such as `log_change` or
`realized_vol_20` instead of raw `level`.
