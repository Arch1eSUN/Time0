# 2026-07-01 Market Macro Realized Vol 20 Router Attribution

## Goal

Explain where the expanded validation-gated router's small lift comes from.

The previous expanded-grid result looked positive at aggregate level:

```text
validation-gated routed MAE improvement vs zero-shot: 2.116398%
fixed recent2000 routed MAE improvement vs zero-shot: 1.987592%
extra MAE delta over fallback: 0.0001260041
```

This run checks whether that extra lift is broad across series or concentrated
in a small subset.

## Implementation

Added:

```text
scripts/summarize_router_attribution.py
```

Input:

```text
reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json
```

Output:

```text
reports/router-attribution-expanded-market-macro-realized-vol-20-h20-r4.json
```

The output report is a generated local artifact and remains ignored by Git.

The script recomputes validation-gated routing from prior cuts only, then
scores each selected window against:

```text
zero-shot
fixed recent2000 fallback
leaky per-window oracle
```

## Command

```bash
uv run python -m py_compile \
  scripts/summarize_router_attribution.py \
  scripts/evaluate_prediction_router.py

uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-expanded-market-macro-realized-vol-20-h20-r4.json
```

## Routed-Cut Summary

Routed cuts only:

| Metric | Value |
|---|---:|
| windows | 4000 |
| selected MAE | 0.0957538599 |
| zero-shot MAE | 0.0978242098 |
| fixed recent2000 MAE | 0.0958798640 |
| oracle MAE | 0.0907393132 |
| improvement vs zero-shot | 2.116398% |
| MAE delta vs fallback | 0.0001260041 |
| relative lift vs fallback | 0.131419% |
| positive delta windows | 412 |
| negative delta windows | 424 |

Selected families:

| Family | Windows |
|---|---:|
| recent2000 | 3164 |
| zero-shot | 306 |
| recent3000 | 292 |
| recent1500 | 131 |
| full | 107 |

## Per-Series Contribution

Positive contributors:

| Series | Delta sum vs fallback | Share of net delta | Mean MAE delta |
|---|---:|---:|---:|
| `DFF:realized_vol_20` | 0.7494884166 | 148.703165% | 0.0018737210 |
| `VIXCLS:realized_vol_20` | 0.1037528657 | 20.585214% | 0.0002593822 |
| `DGS2:realized_vol_20` | 0.0543806398 | 10.789457% | 0.0001359516 |
| `DEXUSEU:realized_vol_20` | 0.0102083329 | 2.025365% | 0.0000255208 |
| `DEXJPUS:realized_vol_20` | 0.0044602339 | 0.884927% | 0.0000111506 |

Negative contributors:

| Series | Delta sum vs fallback | Share of net delta | Mean MAE delta |
|---|---:|---:|---:|
| `DGS10:realized_vol_20` | -0.2748701807 | -54.535954% | -0.0006871755 |
| `SP500:realized_vol_20` | -0.1073125770 | -21.291483% | -0.0002682814 |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0347256513 | -6.889785% | -0.0000868141 |
| `DCOILWTICO:realized_vol_20` | -0.0011436877 | -0.226912% | -0.0000028592 |
| `DTWEXBGS:realized_vol_20` | -0.0002219409 | -0.044034% | -0.0000005549 |

## Cut-Level Attribution

Only two cuts used learned routing:

| Cut | Selected config | MAE delta vs fallback | Relative lift vs fallback |
|---:|---|---:|---:|
| 4000 | `softmax_series` | 0.0013556099 | 1.182162% |
| 4250 | `knn_regret_no_series_k50` | -0.0003475770 | -0.344281% |

All other routed cuts stayed on fixed `recent2000`, so their delta vs fallback
is exactly zero.

## Interpretation

Fact: routed-cut validation-gated MAE is better than fixed recent2000 by
`0.0001260041`.

Fact: `DFF:realized_vol_20` contributes more than the total net gain because
negative series offset it.

Fact: 5 series are positive and 5 are negative vs fallback.

Fact: one learned-routing cut is positive (`4000`) and one learned-routing cut
is negative (`4250`).

Inference: the router signal is real enough to keep studying, but not broad or
stable enough for promotion.

Recommendation: do not publish the router. The next research step should add a
guardrail that blocks learned routing for series where prior validation shows
negative series-level behavior, especially `DGS10` and `SP500`.

## Current Verdict

```text
router aggregate: slightly positive
router attribution: concentrated and fragile
publication: blocked
next step: series-aware validation gate or per-series router guardrail
```
