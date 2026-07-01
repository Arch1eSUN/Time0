# 2026-07-01 Market Macro Realized Vol 20 Multi-Cut Series Guard

## Goal

Test whether multi-cut per-series validation improves on the previous
latest-cut `series_guarded` router policy.

Previous best valid policy:

```text
policy: series_guarded
min_series_validation_lift: 0.0
routed MAE delta vs fixed recent2000: 0.0002025053
routed relative lift vs fixed recent2000: 0.211207%
```

Reason for this run:

```text
The latest-cut series guard fixed cut4250 by blocking DGS10/SP500, but it still
uses only one prior validation cut. This run tests whether broader chronological
series evidence is better.
```

## Implementation

Updated:

```text
scripts/summarize_router_attribution.py
```

Added policies:

```text
series_multicut_guarded:
  aggregate all prior chronological validation cuts into one per-series gate

series_multicut_worst_guarded:
  compute a per-series gate for each prior chronological validation cut
  block a series if any prior cut-level gate fails
```

The default policy remains `validation_gated`.

## Commands

Baseline:

```bash
uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-expanded-market-macro-realized-vol-20-h20-r4.json
```

Aggregate multi-cut gate:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_multicut_guarded \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-multicut-guarded-expanded-market-macro-realized-vol-20-h20-r4.json
```

Worst-cut multi-cut gate:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_multicut_worst_guarded \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-multicut-worst-guarded-expanded-market-macro-realized-vol-20-h20-r4.json
```

Threshold sweep:

```bash
uv run python scripts/summarize_router_attribution.py \
  --policy series_multicut_worst_guarded \
  --min-series-validation-lift 0.005 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-multicut-worst-guarded-msvl-0.005-expanded-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --min-series-validation-lift 0.005 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-msvl-0.005-expanded-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Results

Routed cuts only:

| Policy | Rule | MAE | MAE delta vs fallback | Relative lift vs fallback | Improvement vs zero-shot | Negative series |
|---|---|---:|---:|---:|---:|---:|
| validation-gated | global latest cut only | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-guarded | latest cut per series | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-multicut | aggregate prior cuts per series | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-multicut-worst | every prior cut must pass | 0.0957048950 | 0.0001749690 | 0.182488% | 2.166452% | 5 |

Threshold sweep:

| Policy | min series lift | MAE delta vs fallback | Relative lift vs fallback | Negative series |
|---|---:|---:|---:|---:|
| series-guarded | 0.25% | 0.0002025053 | 0.211207% | 5 |
| series-guarded | 0.50% | 0.0000418135 | 0.043610% | 5 |
| series-guarded | 1.00% | 0.0000580597 | 0.060555% | 4 |
| worst-cut | 0.25% | 0.0001749690 | 0.182488% | 5 |
| worst-cut | 0.50% | -0.0000077771 | -0.008111% | 6 |
| worst-cut | 1.00% | 0.0000084691 | 0.008833% | 5 |

## What The Gates Did

At `cut4000`:

```text
selected config: softmax_series
available multi-cut validation evidence: only cut3750
aggregate multi-cut: allowed all series
worst-cut: allowed all series
MAE delta vs fallback: 0.0013556099
```

At `cut4250`, aggregate multi-cut:

```text
selected config: knn_regret_no_series_k50
validation cuts: 3750, 4000
blocked series: none
MAE delta vs fallback: -0.0003475770
```

At `cut4250`, worst-cut multi-cut:

```text
selected config: knn_regret_no_series_k50
blocked series:
  DFF:realized_vol_20
  DGS10:realized_vol_20
  SP500:realized_vol_20
MAE delta vs fallback: 0.0000441421
```

The worst-cut gate reduced cut4250 risk but over-blocked `DFF`, which is the
largest positive contributor in the current router evidence.

## Interpretation

Fact: aggregate multi-cut gating produced the same routed result as
validation-gated because it allowed every series at the routed cuts.

Fact: worst-cut gating improved over validation-gated but underperformed
latest-cut `series_guarded`.

Fact: stricter `min_series_validation_lift` thresholds did not rescue either
policy; they removed useful adapter switches faster than they removed future
error.

Inference: the issue is not only threshold tuning. Hard multi-cut gates are the
wrong shape for this dataset because they either dilute local failures or let old
failures dominate recent positive signal.

Recommendation: keep `series_guarded` with `min_series_validation_lift=0.0` as
the best current valid policy. The next router policy should test a
recency-weighted series-risk penalty rather than another stricter hard gate.

## Current Verdict

```text
best current policy: series_guarded with min_series_validation_lift=0.0
new multi-cut result: useful negative result
router status: improved but not promotion-ready
publication: blocked
next step: recency-weighted series-risk penalty
```
