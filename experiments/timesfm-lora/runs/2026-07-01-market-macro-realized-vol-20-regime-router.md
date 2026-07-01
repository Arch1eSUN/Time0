# 2026-07-01 Market Macro Realized Vol 20 Regime Router

## Goal

Add richer no-leak runtime features to the prediction-level router after the
early rolling grid showed that more cut points alone did not make learned
routing deployable.

Previous blocker:

```text
early grid validation-gated routed MAE: 0.0921934286
fixed recent2000 routed MAE:            0.0920232799
delta vs fallback:                     -0.0001701487
```

## Implementation

Updated:

```text
scripts/join_prediction_archives.py
scripts/evaluate_prediction_router.py
```

New feature set:

```text
context_prediction_regime_v2
```

Runtime feature groups:

```text
context
context_regime
prediction_summaries
prediction_disagreement
prediction_disagreement_normalized
prediction_context_alignment
```

Guardrail:

```text
All new features are derived from past context or model predictions. Actuals,
current-window errors, and current-window best-family labels remain under label
only and are rejected by validate_no_leak() if they appear in runtime_features.
```

## Commands

Rebuild early router rows with regime features:

```bash
uv run python scripts/join_prediction_archives.py \
  --grid early \
  --output reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json
```

Evaluate default MAE router:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-market-macro-realized-vol-20-h20-r4.json
```

Attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-early-regime-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_guarded \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-guarded-early-regime-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/summarize_router_attribution.py \
  --policy series_risk_penalized \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-series-risk-penalized-early-regime-market-macro-realized-vol-20-h20-r4.json
```

SMAPE check:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --metric smape \
  --input reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-smape-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Feature Counts

```text
context: 6
context_regime: 8
prediction_summaries: 35
prediction_disagreement: 7
prediction_disagreement_normalized: 14
prediction_context_alignment: 40
```

## Main MAE Results

Routed cuts only:

| Policy | MAE | Improvement vs zero-shot | Delta vs fixed recent2000 | Verdict |
|---|---:|---:|---:|---|
| fixed recent2000 fallback | 0.0920232799 | 1.738276% | 0.0000000000 | fallback |
| best chronological diagnostic | 0.0916329967 | 2.155018% | 0.0003902831 | diagnostic only |
| validation-gated | 0.0917723992 | 2.006165% | 0.0002508807 | first positive MAE gate |
| series-guarded | 0.0920553357 | 1.704048% | -0.0000320558 | failed |
| series-risk-penalized | 0.0920553357 | 1.704048% | -0.0000320558 | failed |

Compared with the prior early-grid report:

```text
before regime features validation-gated delta: -0.0001701487
after regime features validation-gated delta:   0.0002508807
```

## Threshold Sweep

Routed cuts only:

| min_validation_lift | Routed MAE | Delta vs fallback | Positive series | Negative series |
|---:|---:|---:|---:|---:|
| 0.000 | 0.0917256164 | 0.0002976635 | 5 | 5 |
| 0.005 | 0.0917529851 | 0.0002702947 | 6 | 4 |
| 0.010 | 0.0917723992 | 0.0002508807 | 5 | 5 |
| 0.020 | 0.0920283258 | -0.0000050459 | 5 | 5 |
| 0.030 | 0.0920232799 | 0.0000000000 | 0 | 0 |
| 0.050 | 0.0920232799 | 0.0000000000 | 0 | 0 |

## SMAPE Check

Routed cuts only:

```text
fixed recent2000 SMAPE:          0.1848619901
validation-gated SMAPE:          0.1850602337
validation-gated delta vs fixed: -0.0001982436
```

The MAE gain is not yet cross-metric robust.

## Attribution

Default validation-gated MAE:

```text
positive routed series: 5
negative routed series: 5
```

Top positive series:

```text
DFF delta sum:               1.2318491423
DGS2 delta sum:              0.4884609157
BAMLH0A0HYM2 delta sum:      0.1388417346
```

Top negative series:

```text
SP500 delta sum:             -0.2331060204
DGS10 delta sum:             -0.2028037781
VIXCLS delta sum:            -0.1353390468
```

## Interpretation

Fact: richer no-leak runtime features turn the default MAE validation-gated
router positive against fixed `recent2000`.

Fact: SMAPE validation, series-guarded MAE, and series-risk MAE remain negative
against the same fallback.

Inference: the feature seam is the right next lever, but the current risk gate
does not preserve the MAE gain.

Recommendation: do not publish yet. The next controlled run should ablate the
new feature groups, then design a risk policy that keeps the positive MAE lift
without reintroducing series-level regressions.

## Current Verdict

```text
regime feature status: first positive MAE no-leak router milestone
promotion status: blocked
next step: feature ablation and stronger series-risk policy
```
