# 2026-07-01 Market Macro Level H20 R4

## Goal

Fine-tune TimesFM 2.5 with a LoRA adapter for public market and macro risk
time-series forecasting.

## Data

Source: FRED public CSV endpoint.

Seed series:

```text
VIXCLS, SP500, DGS10, DGS2, DFF, BAMLH0A0HYM2, DCOILWTICO, DTWEXBGS, DEXUSEU, DEXJPUS
```

Training field:

```text
level
```

Window configuration:

```text
context_len=128
horizon_len=20
max_windows=5000
balanced sampling=500 windows per series
```

## Baselines

Naive baseline over 5000 balanced windows:

```text
last_value.mae=5.370801646
last_value.smape=0.05623413994392316
seasonal_naive.mae=7.591353572999999
seasonal_naive.smape=0.07797490203801292
```

TimesFM zero-shot over 200 balanced windows:

```text
mae=3.352549499458163
smape=0.043185524621834885
```

## LoRA Run

Adapter:

```text
adapters/market-macro-level-h20-r4-step200-balanced
```

Configuration:

```text
base=.hf-cache/timesfm-2.5-200m-transformers
lora_r=4
lora_alpha=8
lora_dropout=0.05
batch_size=2
max_steps=200
device=mps
trainable_params=1,382,912
all_params=232,672,192
trainable_percent=0.5944
```

Observed training losses:

```text
step=1 loss=0.17880824
step=20 loss=1.02559090
step=40 loss=1.47098923
step=60 loss=0.32837954
step=80 loss=0.48509637
step=100 loss=0.86686522
step=120 loss=0.58205879
step=140 loss=0.57431847
step=160 loss=1.49183714
step=180 loss=0.40927640
step=200 loss=0.93479133
```

LoRA evaluation over the same 200 balanced windows:

```text
mae=3.2645185147089473
smape=0.0415481501766979
```

## Result

Fact: the r=4 LoRA adapter improved the 200-window TimesFM comparison:

```text
MAE improvement = 0.08803098474921567
SMAPE improvement = 0.001637374445136985
```

Inference: the adapter learned useful market/macro level adaptation, but this is
not enough to call the model stronger globally.

Recommendation: next run should add rolling cut-point evaluation and train r=4
for more steps before trying r=8.
