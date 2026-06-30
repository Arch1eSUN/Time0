# 2026-07-01 Market Macro Realized Vol 20 Rolling Validation

## Goal

Validate whether the first clean `realized_vol_20` LoRA win survives multiple
chronological cut-points without data leakage.

## Design Correction

The earlier suggested cut-points included:

```text
skip_windows=4000, 5000, 6000
```

That is wrong if one adapter trained on the first 5000 windows is evaluated at
`skip_windows=4000`, because the holdout would overlap the training region.

Correct rolling validation requires a separate adapter per cut-point:

| Cut-point | Training windows | Holdout windows |
|---:|---:|---:|
| 4000 | `skip=0, max=4000` | `skip=4000, max=500` |
| 5000 | `skip=0, max=5000` | `skip=5000, max=500` |
| 5500 | `skip=0, max=5500` | `skip=5500, max=500` |

`skip_windows=6000` was not used for the first rolling gate because the holdout
was no longer balanced across series.

## Data Coverage

All selected cut-points are balanced:

```text
cut4000: 400 train windows per series, 50 holdout windows per series
cut5000: 500 train windows per series, 50 holdout windows per series
cut5500: 550 train windows per series, 50 holdout windows per series
```

## Adapter Recipe

Each cut-point used the same conservative LoRA recipe:

```text
field=realized_vol_20
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
lora_dropout=0.05
batch_size=2
max_steps=200
learning_rate=5e-5
device=mps
```

Trainable parameters:

```text
1,382,912 / 232,672,192 = 0.5944%
```

## Rolling Results

| Cut-point | Last-value MAE | Zero-shot MAE | LoRA MAE | MAE Improvement vs Zero-shot | Zero-shot SMAPE | LoRA SMAPE | SMAPE Improvement |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.12308428096729002 | 0.11759123320482111 | 0.11376577804925998 | 3.253180574182707% | 0.19646661915877023 | 0.1941615794770051 | 1.173247491932641% |
| 5000 | 0.09038209915835001 | 0.0796282537318497 | 0.07865267778637558 | 1.225163054258857% | 0.1877752198880728 | 0.18479685396576195 | 1.5861336357833395% |
| 5500 | 0.13929754301636002 | 0.13107919061242465 | 0.13098847961884505 | 0.06920319934520795% | 0.21800550932341226 | 0.2179365651864745 | 0.03162495165912306% |

Average improvement:

```text
MAE:   1.5158489425955908%
SMAPE: 0.9303353597917012%
```

## Verdict

Fact: LoRA improved MAE and SMAPE at all three balanced cut-points.

Fact: the average MAE improvement was `1.5158489425955908%`, below the 2%
Promotion Ready threshold.

Fact: the `5500` cut-point improvement was only `0.06920319934520795%`, below
the 1% Candidate Success threshold for that individual split.

Inference: `realized_vol_20` remains the best target so far, but the adapter
family is not stable enough for release.

Recommendation: do not publish this adapter. Next step should add per-series
metrics and diagnose why `cut5500` is weak before increasing LoRA rank.

## Environment Note

During this run, `uv run` repeatedly tried to repair a stale
`transformers-4.57.1.dist-info` directory and overwrote the local Transformers
fast-import patch. The stale dist-info directory was removed from the ignored
`.venv`, and `scripts/patch_transformers_fast_import.py` was upgraded to provide
a lightweight `BloomPreTrainedModel` shim needed by PEFT.

Import smoke test after the patch:

```text
TimesFm2_5ModelForPrediction
LoraConfig
1.203 seconds
```

## Next Step

Add per-series evaluation so the next decision can answer:

```text
Is the LoRA improvement broad across series, or concentrated in a few symbols?
Why does cut5500 barely improve?
Would r=8 improve the weak cut-point or just overfit earlier cut-points?
```
