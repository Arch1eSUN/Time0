# 2026-07-01 Market Macro Realized Vol 20 Per-Series Attribution

## Goal

Explain where the `realized_vol_20` LoRA rolling improvement comes from by
adding per-series metrics to the evaluation reports.

## Tooling Change

Updated:

```text
scripts/evaluate_naive.py
scripts/evaluate_timesfm.py
```

Both scripts now keep existing aggregate fields and add:

```text
per_series
```

For `evaluate_timesfm.py`, each series reports:

```text
windows
mae
smape
```

For `evaluate_naive.py`, each series reports:

```text
windows
last_value.mae
last_value.smape
seasonal_naive.mae
seasonal_naive.smape
```

## Rolling Cut-Points

| Cut-point | Training windows | Holdout windows | Holdout balance |
|---:|---:|---:|---|
| 4000 | 400 per series | 50 per series | balanced |
| 5000 | 500 per series | 50 per series | balanced |
| 5500 | 550 per series | 50 per series | balanced |

## Aggregate Result

| Cut-point | Zero-shot MAE | LoRA MAE | MAE Improvement | Zero-shot SMAPE | LoRA SMAPE | SMAPE Improvement |
|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.11759123320482111 | 0.11376577804925998 | 3.253180574182707% | 0.19646661915877023 | 0.1941615794770051 | 1.173247491932641% |
| 5000 | 0.0796282537318497 | 0.07865267778637558 | 1.225163054258857% | 0.1877752198880728 | 0.18479685396576195 | 1.5861336357833395% |
| 5500 | 0.13107919061242465 | 0.13098847961884505 | 0.06920319934520795% | 0.21800550932341226 | 0.2179365651864745 | 0.03162495165912306% |

## Per-Series MAE Improvement vs TimesFM Zero-Shot

| Series | Cut4000 | Cut5000 | Cut5500 | Average |
|---|---:|---:|---:|---:|
| `DEXUSEU:realized_vol_20` | -2.627553% | 0.624542% | -2.037267% | -1.346759% |
| `DGS10:realized_vol_20` | 0.253103% | 0.283125% | -1.142659% | -0.202144% |
| `DGS2:realized_vol_20` | -2.644006% | 1.568999% | 1.911722% | 0.278905% |
| `VIXCLS:realized_vol_20` | 0.277337% | 0.673529% | -0.095068% | 0.285266% |
| `DTWEXBGS:realized_vol_20` | 2.226942% | 1.497981% | -1.485192% | 0.746577% |
| `SP500:realized_vol_20` | 1.601611% | -0.000741% | 1.403606% | 1.001492% |
| `BAMLH0A0HYM2:realized_vol_20` | -0.162285% | 3.042571% | 0.469182% | 1.116489% |
| `DCOILWTICO:realized_vol_20` | 1.067360% | 3.455488% | -0.174774% | 1.449358% |
| `DFF:realized_vol_20` | 5.769349% | 0.754525% | -0.045858% | 2.159339% |
| `DEXJPUS:realized_vol_20` | 4.233439% | 3.674496% | -0.048423% | 2.619837% |

## What This Explains

Fact: average per-series MAE improvement is positive for 8 of 10 series.

Fact: `DEXUSEU` and `DGS10` are negative on average.

Fact: `cut5500` is weak because only 3 of 10 series improved:

```text
BAMLH0A0HYM2
SP500
DGS2
```

Fact: 7 of 10 series regressed at `cut5500`, but most regressions were small.

Inference: the adapter family has broad but shallow signal, not a release-grade
improvement.

Inference: increasing rank before diagnosing `cut5500` would mix capacity
effects with regime/series effects.

Recommendation: do not publish and do not jump to `r=8` yet. Next step should
diagnose `cut5500` by series distribution, volatility regime, and target scale.

## Current Verdict

```text
Candidate Success: yes, for realized_vol_20 direction.
Promotion Ready: no.
Release: blocked.
Next technical step: per-series diagnostics and target normalization/regime analysis.
```
