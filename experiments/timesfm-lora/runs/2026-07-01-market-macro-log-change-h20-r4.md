# 2026-07-01 Market Macro Log Change H20 R4

## Goal

Test whether changing the target from raw `level` to `log_change` improves
TimesFM 2.5 LoRA holdout behavior.

## Tooling Fix

Transformers 5.12.1 startup repeatedly stalled while dynamically scanning all
model modules. Added:

```text
scripts/patch_transformers_fast_import.py
```

This patch limits local Transformers lazy import metadata to the entries needed
for TimesFM 2.5 and PEFT LoRA in this experiment.

Observed import test after patch:

```text
TimesFm2_5ModelForPrediction
1.638 seconds
```

## Experiment Change

Previous target:

```text
field=level
```

This run:

```text
field=log_change
```

Everything else stayed intentionally conservative:

```text
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
lora_dropout=0.05
batch_size=2
max_steps=200
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

## Holdout Baselines

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 0.02846349734552 | 1.3721631236138991 |
| Seasonal naive | 0.026348636656100002 | 1.342713152518601 |
| TimesFM 2.5 zero-shot | 0.01852017978944989 | 1.7846263993121316 |

## LoRA Training

Adapter:

```text
adapters/market-macro-log-change-h20-r4-step200-balanced
```

Observed losses:

```text
step=1 loss=1.14145172
step=20 loss=0.77540541
step=40 loss=0.71983969
step=60 loss=0.68322301
step=80 loss=2.22868586
step=100 loss=1.76485598
step=120 loss=0.57479203
step=140 loss=0.41480857
step=160 loss=0.64630598
step=180 loss=1.73545766
step=200 loss=1.19211233
```

## Holdout Result

| Model | MAE | SMAPE |
|---|---:|---:|
| TimesFM 2.5 zero-shot | 0.01852017978944989 | 1.7846263993121316 |
| LoRA r4 step200 log_change | 0.018340936770009884 | 1.8129117903524623 |

## Interpretation

Fact: LoRA improved MAE by about `0.00017924301944000676`.

Fact: LoRA worsened SMAPE by about `0.02828539104033069`.

Inference: `log_change` is more promising than raw `level` on absolute error,
but the adapter is not cleanly better because relative error worsened.

Recommendation: do not promote this adapter yet. Next run should evaluate
`realized_vol_20`, because it is closer to the market-macro-risk goal and avoids
some near-zero denominator issues that make SMAPE noisy on `log_change`.
