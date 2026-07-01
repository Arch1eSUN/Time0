# 2026-07-02 Market Macro Realized Vol 20 Calibrated KNN-Regret

## Goal

Test whether isolating KNN-regret selectors and recalibrating the validation
gate improves the current alignment-normalized router frontier.

Previous checkpoint:

```text
baseline candidate set validation-gated delta: 0.0002674001
loss-aware candidate set validation-gated delta: 0.0002366568
best diagnostic: knn_regret_no_series_k25
```

The question for this run:

```text
If KNN-regret is the best diagnostic selector, does a KNN-only candidate set
with a lower validation threshold produce a better deployable policy?
```

## Implementation

Changed:

```text
scripts/evaluate_prediction_router.py
scripts/summarize_router_attribution.py
scripts/sweep_router_policies.py
```

Added candidate set:

```text
--candidate-set knn-regret
```

Default behavior remains:

```text
--candidate-set baseline
```

## Commands

Direct KNN-regret default gate:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --candidate-set knn-regret \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-knn-regret-market-macro-realized-vol-20-h20-r4.json
```

KNN-regret policy sweep:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-knn-regret-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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

Best aggregate KNN-regret run:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --candidate-set knn-regret \
  --min-validation-lift 0 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-knn-regret-mvl0-market-macro-realized-vol-20-h20-r4.json
```

Best risk-balanced KNN-regret run:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --candidate-set knn-regret \
  --min-validation-lift 0.005 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-knn-regret-mvl005-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Results

Routed cuts only:

| Candidate set | Min validation | MAE delta | SMAPE delta | Positive / Negative series |
|---|---:|---:|---:|---:|
| `baseline` | 0.010 | 0.0002674001 | 0.0001307865 | 4 / 6 |
| `knn-regret` | 0.010 | -0.0000393438 | -0.0000238320 | not promoted |
| `knn-regret` | 0.000 | 0.0002705342 | 0.0004127764 | 6 / 4 |
| `knn-regret` | 0.005 | 0.0002687244 | 0.0005225268 | 7 / 3 |

Top KNN-regret policy sweep rows:

| Rank | Policy | Min validation | Min series | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|
| 1 | `validation_gated` | 0.000 | 0.000 | 0.0002705342 | 6 / 4 |
| 2 | `validation_gated` | 0.005 | 0.000 | 0.0002687244 | 7 / 3 |
| 3 | `series_guarded` | 0.000 | 0.000 | 0.0001428194 | 7 / 3 |
| 4 | `series_risk_penalized` | 0.000 | 0.000 | 0.0001428194 | 7 / 3 |

Best aggregate:

```text
candidate_set: knn-regret
policy: validation_gated
min_validation_lift: 0.0
MAE delta vs fallback: 0.0002705342
SMAPE delta vs fallback: 0.0004127764
positive/negative routed series: 6/4
```

Best risk-balanced:

```text
candidate_set: knn-regret
policy: validation_gated
min_validation_lift: 0.005
MAE delta vs fallback: 0.0002687244
SMAPE delta vs fallback: 0.0005225268
positive/negative routed series: 7/3
```

## Interpretation

Fact: KNN-regret with the old `0.01` validation threshold regresses both MAE and
SMAPE.

Fact: KNN-regret with a lighter `0.0` threshold gives the best aggregate MAE
delta so far.

Fact: KNN-regret with `0.005` gives nearly the same MAE delta, stronger SMAPE
delta, and a better positive/negative series split.

Inference: KNN-regret is useful, but it needs a different calibration than the
mixed baseline candidate set.

Recommendation: treat `knn-regret min_validation_lift=0.005` as the current
best risk-balanced router checkpoint. Promotion remains blocked because the
extra MAE lift over baseline is only `0.0000013244`.

## Current Verdict

```text
frontier moved: yes, slightly
best aggregate: knn-regret mvl0
best risk-balanced: knn-regret mvl0.005
promotion status: blocked
next step: per-series downside control on top of KNN-regret
```
