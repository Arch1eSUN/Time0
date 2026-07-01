# 2026-07-01 Market Macro Realized Vol 20 Series Risk Penalty

## Goal

Test whether a recency-weighted per-series risk score can improve on the latest
best router guard.

Previous best:

```text
policy: series_guarded
min_series_validation_lift: 0.0
routed MAE delta vs fixed recent2000: 0.0002025053
routed relative lift vs fixed recent2000: 0.211207%
```

Reason for this run:

```text
Multi-cut aggregate validation diluted local series failures.
Worst-cut validation over-blocked DFF.
This run tests whether recency-weighted history can keep recent signal while
still using older validation cuts as weak prior evidence.
```

## Implementation

Updated:

```text
scripts/summarize_router_attribution.py
```

Added policy:

```text
--policy series_risk_penalized
```

Added parameter:

```text
--series-risk-decay
```

Risk score:

```text
risk_score = (weighted_fallback_metric - weighted_candidate_metric)
             / weighted_fallback_metric
```

The latest validation cut receives weight `1.0`. Older validation cuts receive:

```text
weight = series_risk_decay ** distance_from_latest_validation_cut
```

The default is `0.1`.

## Commands

Default recency-weighted risk policy:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_risk_penalized \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-risk-penalized-expanded-market-macro-realized-vol-20-h20-r4.json
```

Decay sweep:

```bash
for d in 0.05 0.1 0.25 0.5 0.75 1.0; do
  uv run python scripts/summarize_router_attribution.py \
    --policy series_risk_penalized \
    --series-risk-decay "$d" \
    --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
    --output "reports/router-attribution-series-risk-penalized-decay-${d}-expanded-market-macro-realized-vol-20-h20-r4.json"
done
```

Generated reports remain ignored local artifacts.

## Results

Routed cuts only:

| Policy | Decay | MAE | MAE delta vs fallback | Relative lift vs fallback | Improvement vs zero-shot | Negative series |
|---|---:|---:|---:|---:|---:|---:|
| validation-gated | n/a | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-guarded | n/a | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk | 0.05 | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk | 0.10 | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk | 0.25 | 0.0957362110 | 0.0001436530 | 0.149826% | 2.134181% | 5 |
| series-risk | 0.50 | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-risk | 0.75 | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-risk | 1.00 | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |

## Cut4250 Behavior

At `cut4250`, default `series_risk_penalized` uses:

```text
cut3750 weight: 0.1
cut4000 weight: 1.0
```

Key series:

| Series | cut3750 lift | cut4000 lift | risk score | Decision |
|---|---:|---:|---:|---|
| `DFF:realized_vol_20` | -0.0041246154 | 0.0200250508 | 0.0188600061 | allow |
| `DGS10:realized_vol_20` | 0.0388681293 | -0.0035742330 | -0.0009757999 | block |
| `SP500:realized_vol_20` | 0.0115035050 | -0.0020552277 | -0.0012814833 | block |

This reproduces the useful behavior of the latest-cut series guard:

```text
keeps DFF positive contribution
blocks DGS10 and SP500 at cut4250
```

## Interpretation

Fact: `series_risk_penalized` with decay `0.05` or `0.1` ties the previous best
`series_guarded` policy.

Fact: it does not exceed `series_guarded`.

Fact: larger decay values degrade performance because older positive validation
evidence hides recent DGS10/SP500 failures.

Inference: recency weighting is directionally correct, but the current
chronological grid does not provide enough earlier validation evidence to improve
over a latest-cut guard.

Recommendation: keep `series_guarded` as the simpler current best policy. Keep
`series_risk_penalized` as a diagnostic policy for future larger grids. The next
controlled experiment should expand earlier rolling cuts or add richer no-leak
runtime features before more guard tuning.

## Current Verdict

```text
best simple policy: series_guarded with min_series_validation_lift=0.0
best diagnostic policy: series_risk_penalized with series_risk_decay=0.1
new net improvement over current best: none
router status: improved but not promotion-ready
publication: blocked
next step: more early chronological supervision or richer no-leak features
```
