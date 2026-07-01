# 2026-07-01 Market Macro Realized Vol 20 Series Guard

## Goal

Test whether a series-aware validation gate can reduce the negative
per-series regressions found in the expanded router attribution run.

Previous finding:

```text
validation-gated router:
  routed MAE delta vs fixed recent2000: 0.0001260041
  DGS10 delta sum vs fallback: -0.2748701807
  SP500 delta sum vs fallback: -0.1073125770
```

This run adds a second guard:

```text
global gate:
  learned router must beat fallback on latest prior validation cut

series gate:
  learned router must also beat fallback for that series on latest prior validation cut
```

If either gate fails, the policy uses fixed `recent2000`.

## Implementation

Updated:

```text
scripts/summarize_router_attribution.py
```

Added CLI options:

```text
--policy {validation_gated,series_guarded}
--min-series-validation-lift
```

The default remains `validation_gated`, so the previous attribution command is
backward compatible.

## Commands

Baseline regression:

```bash
uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-expanded-market-macro-realized-vol-20-h20-r4.json
```

Series-aware guard:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-expanded-market-macro-realized-vol-20-h20-r4.json
```

Threshold sweep:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --min-series-validation-lift 0.005 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-lift005-expanded-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --min-series-validation-lift 0.01 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-lift010-expanded-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --min-series-validation-lift 0.02 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-lift020-expanded-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Results

Routed cuts only:

| Policy | Series lift | MAE | MAE delta vs fallback | Relative lift vs fallback | Improvement vs zero-shot | Negative series |
|---|---:|---:|---:|---:|---:|---:|
| validation-gated | n/a | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-guarded | 0.0% | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-guarded | 0.5% | 0.0958380504 | 0.0000418135 | 0.043610% | 2.030335% | 5 |
| series-guarded | 1.0% | 0.0958218043 | 0.0000580597 | 0.060555% | 2.046943% | 4 |
| series-guarded | 2.0% | 0.0958353379 | 0.0000445261 | 0.046439% | 2.033108% | 1 |

Best MAE policy in this sweep:

```text
series_guarded, min_series_validation_lift=0.0
```

Compared with validation-gated:

```text
extra MAE delta over fallback: +0.0000765012
relative increase in fallback delta: +60.713273%
```

## What The Guard Changed

At `cut4000`:

```text
selected config: softmax_series
series gate allowed all series
MAE delta vs fallback: 0.0013556099
```

At `cut4250`:

```text
selected config: knn_regret_no_series_k50
series gate blocked:
  DGS10:realized_vol_20
  SP500:realized_vol_20
MAE delta vs fallback before guard: -0.0003475770
MAE delta vs fallback after guard:  0.0002644327
```

The guard fixed the negative cut4250 switch by preserving `recent2000` for
`DGS10` and `SP500`.

## Remaining Weakness

The guard did not fully solve subgroup risk:

| Series | Guarded delta sum vs fallback |
|---|---:|
| `DGS10:realized_vol_20` | -0.0394606923 |
| `SP500:realized_vol_20` | -0.0367171801 |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0347256513 |

Reason:

```text
The current guard uses only the latest prior validation cut. At cut4000, the
validation cut did not block DGS10 or SP500, so the policy still allowed a
learned switch that later hurt those series.
```

## Interpretation

Fact: series-aware gating improves the routed MAE delta vs fallback from
`0.0001260041` to `0.0002025053`.

Fact: the guard blocks `DGS10` and `SP500` at cut4250 and turns that cut from
negative to positive vs fallback.

Fact: stricter series thresholds reduce negative-series count, but they also
remove too much positive signal.

Inference: series-aware validation is useful, but a one-cut series gate is not
enough for promotion.

Recommendation: keep `series_guarded` as the best current router policy, but do
not publish. The next controlled step should test a multi-cut series guard or a
series-risk penalty that can catch `DGS10`/`SP500` earlier.

## Current Verdict

```text
best current policy: series_guarded with min_series_validation_lift=0.0
router status: improved but not promotion-ready
publication: blocked
next step: multi-cut series guard / series-risk penalty
```
