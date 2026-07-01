# 2026-07-02 Market Macro Realized Vol 20 Policy Sweep

## Goal

Tune router policy thresholds around the current best feature surface:

```text
alignment-normalized
```

Previous checkpoint:

```text
validation-gated routed MAE:             0.0917558798
validation-gated MAE delta vs fallback:  0.0002674001
series-guarded MAE delta vs fallback:    0.0000148190
```

The open question was whether series-risk tuning can preserve aggregate MAE
lift while reducing per-series regressions.

## Implementation

Added:

```text
scripts/sweep_router_policies.py
```

The script reuses `summarize_router_attribution.build_report` and runs a compact
policy grid over the same router-row report. It writes one ranked JSON report
containing the tested policy rows, best row by aggregate delta, and top rows.

Generated reports remain ignored local artifacts.

## Commands

Compile check:

```bash
uv run python -m py_compile \
  scripts/sweep_router_policies.py \
  scripts/summarize_router_attribution.py
```

Policy sweep:

```bash
uv run python scripts/sweep_router_policies.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy validation_gated \
  --policy series_guarded \
  --policy series_risk_penalized \
  --min-validation-lift 0 \
  --min-validation-lift 0.005 \
  --min-validation-lift 0.01 \
  --min-series-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --series-risk-decay 0.05 \
  --series-risk-decay 0.1 \
  --series-risk-decay 0.25
```

## Results

Configs tested:

```text
27
```

Top rows, routed cuts only, MAE:

| Rank | Policy | Min validation | Min series | Decay | MAE | Delta vs fallback | Positive / Negative series |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `validation_gated` | 0.010 | 0.000 | 0.10 | 0.0917558798 | 0.0002674001 | 4 / 6 |
| 2 | `validation_gated` | 0.000 | 0.000 | 0.10 | 0.0917603146 | 0.0002630 | 6 / 4 |
| 3 | `validation_gated` | 0.005 | 0.000 | 0.10 | 0.0917621244 | 0.0002612 | 7 / 3 |
| 4 | `series_guarded` | 0.000 | 0.000 | 0.10 | 0.0919869385 | 0.0000363 | 6 / 4 |
| 5 | `series_risk_penalized` | 0.000 | 0.000 | 0.05 | 0.0919869385 | 0.0000363 | 6 / 4 |
| 6 | `series_guarded` | 0.000 | 0.001 | 0.10 | 0.0919982524 | 0.0000250 | 6 / 4 |
| 7 | `series_guarded` | 0.005 | 0.000 | 0.10 | 0.0920020171 | 0.0000213 | 8 / 2 |
| 8 | `series_risk_penalized` | 0.005 | 0.000 | 0.05 | 0.0920020171 | 0.0000213 | 8 / 2 |

Best by policy:

| Policy | Best threshold | MAE | Delta vs fallback | Positive / Negative series |
|---|---|---:|---:|---:|
| `validation_gated` | `min_validation_lift=0.01` | 0.0917558798 | 0.0002674001 | 4 / 6 |
| `series_guarded` | `min_validation_lift=0.0`, `min_series_validation_lift=0.0` | 0.0919869385 | 0.0000363414 | 6 / 4 |
| `series_risk_penalized` | `min_validation_lift=0.0`, `min_series_validation_lift=0.0`, `decay=0.05` | 0.0919869385 | 0.0000363414 | 6 / 4 |

Best risk-balanced aggregate candidate:

```text
policy: validation_gated
min_validation_lift: 0.005
MAE: 0.0917621244
delta vs fallback: 0.0002611555
positive routed series: 7
negative routed series: 3
```

Best 8/2 series split with positive delta:

```text
policy: series_guarded
min_validation_lift: 0.005
min_series_validation_lift: 0.0
MAE delta vs fallback: 0.0000212628
positive routed series: 8
negative routed series: 2
```

## Interpretation

Fact: the best aggregate row is still a simple `validation_gated` policy.

Fact: lowering the validation threshold from `0.01` to `0.005` keeps almost the
same aggregate delta while improving the series split from `4/6` to `7/3`.

Fact: `series_risk_penalized` does not beat `series_guarded`; its best row ties
the guarded policy.

Fact: the 8/2 series split is possible, but the aggregate delta falls to
`0.0000212628`, which is too small for promotion.

Inference: the policy frontier did not improve. Manual hard-gate and risk
threshold tuning trades aggregate lift for series stability, but does not create
a publishable combination of both.

Recommendation: stop manual policy-threshold tuning for this surface. Keep
`alignment-normalized` as the current feature seam and move next toward a
loss-aware supervised selector or a richer no-leak training objective.

## Current Verdict

```text
best aggregate: validation_gated, min_validation_lift=0.01
best risk-balanced aggregate: validation_gated, min_validation_lift=0.005
series-risk policy: useful diagnostic, no new lift
promotion status: blocked
next step: supervised selector objective or richer loss-aware router training
```
