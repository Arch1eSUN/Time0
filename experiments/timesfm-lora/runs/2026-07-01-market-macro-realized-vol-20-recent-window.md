# 2026-07-01 Market Macro Realized Vol 20 Recent-Window Training

## Goal

Test whether recency-limited fine-tuning handles the weak `cut5500` regime
mismatch better than full-history fine-tuning.

Previous evidence:

```text
full-history rolling average MAE improvement: 1.515849%
normalized rolling average MAE improvement: 0.978786%
Promotion Ready threshold: 2.000000%
```

## Experiment Design

Use the same raw target and LoRA hyperparameters as the full-history
`realized_vol_20` runs, but train each adapter only on the most recent 2000
balanced windows before the holdout cut-point.

| Cut-point | Train skip | Train windows | Train per series | Holdout skip | Holdout windows |
|---:|---:|---:|---:|---:|---:|
| 4000 | 2000 | 2000 | 200 | 4000 | 500 |
| 5000 | 3000 | 2000 | 200 | 5000 | 500 |
| 5500 | 3500 | 2000 | 200 | 5500 | 500 |

Fixed settings:

| Setting | Value |
|---|---|
| Base model | `.hf-cache/timesfm-2.5-200m-transformers` |
| Field | `realized_vol_20` |
| Context length | 128 |
| Horizon length | 20 |
| LoRA rank | 4 |
| LoRA alpha | 8 |
| LoRA dropout | 0.05 |
| Max steps | 200 |
| Batch size | 2 |
| Device | MPS |

Local adapters:

```text
adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train4000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train5000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train5500
```

## Results

| Cut | Last-value MAE | Zero-shot MAE | Full-history LoRA MAE | Full MAE gain | Recent2000 LoRA MAE | Recent MAE gain | Zero-shot SMAPE | Recent SMAPE | Recent SMAPE gain | Recent wins | Full wins |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.123084281 | 0.117591233 | 0.113765778 | 3.253% | 0.114672099 | 2.482% | 0.196466619 | 0.194735224 | 0.881% | 6/10 | 7/10 |
| 5000 | 0.090382099 | 0.079628254 | 0.078652678 | 1.225% | 0.079087892 | 0.679% | 0.187775220 | 0.185190278 | 1.377% | 7/10 | 9/10 |
| 5500 | 0.139297543 | 0.131079191 | 0.130988480 | 0.069% | 0.128443571 | 2.011% | 0.218005509 | 0.217275777 | 0.335% | 5/10 | 3/10 |

Average recent-window MAE improvement:

```text
1.723918%
```

Average recent-window SMAPE improvement:

```text
0.864204%
```

## Cut5500 Per-Series Result

| Series | Recent2000 MAE improvement vs zero-shot |
|---|---:|
| `BAMLH0A0HYM2:realized_vol_20` | 1.072% |
| `DCOILWTICO:realized_vol_20` | -0.106% |
| `DEXJPUS:realized_vol_20` | -0.235% |
| `DEXUSEU:realized_vol_20` | -5.324% |
| `DFF:realized_vol_20` | 2.522% |
| `DGS10:realized_vol_20` | -4.225% |
| `DGS2:realized_vol_20` | 8.973% |
| `DTWEXBGS:realized_vol_20` | -4.910% |
| `SP500:realized_vol_20` | 0.639% |
| `VIXCLS:realized_vol_20` | 0.152% |

## Interpretation

Fact: recent-window training improved `cut5500` MAE by `2.011%`, compared with
`0.069%` for full-history training.

Fact: recent-window training improved `cut5500` per-series wins from `3/10` to
`5/10`.

Fact: recent-window training reduced the `cut4000` MAE gain from `3.253%` to
`2.482%`.

Fact: recent-window training reduced the `cut5000` MAE gain from `1.225%` to
`0.679%`.

Fact: recent-window average MAE improvement was `1.723918%`, still below the
`2%` Promotion Ready threshold.

Inference: recency is a real lever. It addresses the weak `cut5500` split better
than normalization, but `recent2000` is probably too narrow for all cut-points.

Inference: this is not yet release evidence. It is evidence that the training
window length should become an explicit hyperparameter before increasing LoRA
rank.

Recommendation: do not publish and do not jump to `r=8` yet. Test a longer
recent window, starting with `recent3000`, using the same cut-points and LoRA
settings.

## Next Experiment Direction

Next controlled direction:

```text
field=realized_vol_20
training_window=recent3000
lora_r=4
lora_alpha=8
max_steps=200
cutpoints=4000,5000,5500
```

Question:

```text
Can recent3000 keep the cut5500 repair while recovering cut4000/cut5000 gains?
```

If `recent3000` clears 2% average MAE improvement and does not collapse
per-series robustness, then Time0 can test repeat stability before any larger
rank.
