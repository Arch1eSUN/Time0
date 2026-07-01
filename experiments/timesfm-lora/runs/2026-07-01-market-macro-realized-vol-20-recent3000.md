# 2026-07-01 Market Macro Realized Vol 20 Recent3000

## Goal

Test whether a longer recent window can keep the `cut5500` repair from
`recent2000` while recovering the stronger `cut4000` and `cut5000` behavior.

This run also clarifies the adapter domain and target:

```text
domain: public financial market and macro risk forecasting
data source: FRED public daily series
target: realized_vol_20
not target: buy/sell signal, direction prediction, portfolio advice
```

## Training Data Direction

The adapter is financial-domain, but the specific direction is narrower than
"finance" in general.

| Group | Series | Meaning |
|---|---|---|
| Equity and equity risk | `SP500`, `VIXCLS` | equity market level and implied volatility |
| Rates | `DGS10`, `DGS2`, `DFF` | Treasury yields and effective fed funds |
| Credit risk | `BAMLH0A0HYM2` | high-yield corporate bond spread |
| Commodities | `DCOILWTICO` | WTI crude oil |
| FX and dollar | `DTWEXBGS`, `DEXUSEU`, `DEXJPUS` | broad dollar index, EUR/USD, JPY/USD |

The current best target family is:

```text
realized_vol_20
```

Meaning:

```text
20-day realized volatility derived from daily log changes
```

## Experiment Design

Train each adapter only on the most recent 3000 balanced windows before the
holdout cut-point.

| Cut-point | Train skip | Train windows | Train per series | Holdout skip | Holdout windows |
|---:|---:|---:|---:|---:|---:|
| 4000 | 1000 | 3000 | 300 | 4000 | 500 |
| 5000 | 2000 | 3000 | 300 | 5000 | 500 |
| 5500 | 2500 | 3000 | 300 | 5500 | 500 |

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
adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train4000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train5000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train5500
```

## Results

| Cut | Last-value MAE | Zero-shot MAE | Full MAE | Full gain | Recent2000 MAE | Recent2000 gain | Recent3000 MAE | Recent3000 gain | Zero SMAPE | Recent3000 SMAPE | SMAPE gain | R3000 wins |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.123084281 | 0.117591233 | 0.113765778 | 3.253% | 0.114672099 | 2.482% | 0.113604199 | 3.391% | 0.196466619 | 0.193842963 | 1.335% | 7/10 |
| 5000 | 0.090382099 | 0.079628254 | 0.078652678 | 1.225% | 0.079087892 | 0.679% | 0.079124828 | 0.632% | 0.187775220 | 0.185936483 | 0.979% | 7/10 |
| 5500 | 0.139297543 | 0.131079191 | 0.130988480 | 0.069% | 0.128443571 | 2.011% | 0.130423513 | 0.500% | 0.218005509 | 0.218144161 | -0.064% | 4/10 |

Average MAE gains:

```text
full-history: 1.515849%
recent2000:   1.723918%
recent3000:   1.507674%
```

Average recent3000 SMAPE gain:

```text
0.750348%
```

## Cut5500 Per-Series Result

| Series | Recent3000 MAE improvement vs zero-shot |
|---|---:|
| `BAMLH0A0HYM2:realized_vol_20` | 1.607% |
| `DCOILWTICO:realized_vol_20` | -0.922% |
| `DEXJPUS:realized_vol_20` | -0.121% |
| `DEXUSEU:realized_vol_20` | -2.291% |
| `DFF:realized_vol_20` | 0.685% |
| `DGS10:realized_vol_20` | -1.950% |
| `DGS2:realized_vol_20` | 2.476% |
| `DTWEXBGS:realized_vol_20` | -2.209% |
| `SP500:realized_vol_20` | 0.266% |
| `VIXCLS:realized_vol_20` | -0.326% |

## Interpretation

Fact: `recent3000` improved `cut4000` to `3.391%`, the best `cut4000` result so
far.

Fact: `recent3000` did not recover `cut5000`; its MAE gain was `0.632%`, below
full-history `1.225%` and recent2000 `0.679%`.

Fact: `recent3000` weakened the `cut5500` repair. Its `cut5500` MAE gain was
`0.500%`, compared with recent2000 `2.011%`.

Fact: `recent3000` average MAE gain was `1.507674%`, below recent2000
`1.723918%` and below the `2%` Promotion Ready threshold.

Inference: a single longer recent window does not solve the tradeoff. The
optimal window appears regime-dependent.

Inference: `recent2000` is better for the weak `cut5500` regime, while
`recent3000` is better for `cut4000`.

Recommendation: do not publish and do not increase LoRA rank yet. Either test a
shorter `recent1500` window to map the recency curve, or start a regime-aware
adapter selection experiment.

## Next Experiment Direction

Next controlled direction:

```text
field=realized_vol_20
training_window=recent1500
lora_r=4
lora_alpha=8
max_steps=200
cutpoints=4000,5000,5500
```

Question:

```text
Does a shorter recent window strengthen cut5500 further, and how much does it
damage cut4000/cut5000?
```

If `recent1500` improves only `cut5500` while weakening the others, the next
research step should be regime-aware adapter routing rather than a single fixed
window.
