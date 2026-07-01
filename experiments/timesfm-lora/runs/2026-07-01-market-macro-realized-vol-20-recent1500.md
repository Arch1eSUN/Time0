# 2026-07-01 Market Macro Realized Vol 20 Recent1500

## Goal

Test whether a shorter recent window strengthens the weak `cut5500` split
further than `recent2000`, and measure the damage to `cut4000` and `cut5000`.

This run completes the first fixed-window recency sweep:

```text
full-history
recent3000
recent2000
recent1500
```

## Experiment Design

Train each adapter only on the most recent 1500 balanced windows before the
holdout cut-point.

| Cut-point | Train skip | Train windows | Train per series | Holdout skip | Holdout windows |
|---:|---:|---:|---:|---:|---:|
| 4000 | 2500 | 1500 | 150 | 4000 | 500 |
| 5000 | 3500 | 1500 | 150 | 5000 | 500 |
| 5500 | 4000 | 1500 | 150 | 5500 | 500 |

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
adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train4000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train5000
adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train5500
```

## Results

| Cut | Zero MAE | Full MAE | Full gain | R1500 MAE | R1500 gain | R2000 MAE | R2000 gain | R3000 MAE | R3000 gain | R1500 SMAPE | R1500 SMAPE gain | R1500 wins | Best window | Best MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 4000 | 0.117591233 | 0.113765778 | 3.253% | 0.113148473 | 3.778% | 0.114672099 | 2.482% | 0.113604199 | 3.391% | 0.195412644 | 0.536% | 2/10 | recent1500 | 0.113148473 |
| 5000 | 0.079628254 | 0.078652678 | 1.225% | 0.082385049 | -3.462% | 0.079087892 | 0.679% | 0.079124828 | 0.632% | 0.192032974 | -2.267% | 4/10 | full | 0.078652678 |
| 5500 | 0.131079191 | 0.130988480 | 0.069% | 0.131223773 | -0.110% | 0.128443571 | 2.011% | 0.130423513 | 0.500% | 0.218838982 | -0.382% | 3/10 | recent2000 | 0.128443571 |

Average MAE gains:

```text
full-history: 1.515849%
recent1500:   0.068585%
recent2000:   1.723918%
recent3000:   1.507674%
```

Average recent1500 SMAPE gain:

```text
-0.704442%
```

## Interpretation

Fact: `recent1500` produced the best `cut4000` MAE so far, with `3.778%`
improvement vs zero-shot.

Fact: `recent1500` failed `cut5000`, with `-3.462%` MAE improvement vs
zero-shot.

Fact: `recent1500` failed to repair `cut5500`, with `-0.110%` MAE improvement
vs zero-shot.

Fact: the best window differs by cut-point:

```text
cut4000: recent1500
cut5000: full-history
cut5500: recent2000
```

Inference: fixed-window recency tuning is not enough. A single global adapter
window cannot represent all observed regimes.

Inference: the next meaningful step is not `r=8`. The next step is
regime-aware adapter selection or per-series/window routing.

Recommendation: stop fixed-window sweep for now. Build a routing experiment
that selects among `full-history`, `recent1500`, `recent2000`, and `recent3000`
based on validation evidence or regime features.

## Next Experiment Direction

Next controlled direction:

```text
field=realized_vol_20
method=regime-aware adapter routing
candidate_adapters=full-history,recent1500,recent2000,recent3000
selection_grain=cutpoint first, then per-series if useful
```

Question:

```text
Can a routing policy beat every fixed-window adapter family without leaking
holdout information?
```

Guardrail:

```text
Routing selection must be learned or chosen from validation windows before the
holdout, not from the holdout results themselves.
```
