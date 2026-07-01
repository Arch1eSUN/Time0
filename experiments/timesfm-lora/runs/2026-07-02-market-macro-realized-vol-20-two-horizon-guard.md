# 2026-07-02 Market Macro Realized Vol 20 Two-Horizon Guard

## Goal

Test whether combining latest-cut and recency-weighted per-series safety can
repair the temporal instability exposed by the latest-cut guard.

Prior blocker:

```text
latest-cut late-best delta: 0.000009607834422359351
same config on expanded: -0.000015001191475502718
```

New policy:

```text
policy: fallback_veto_two_horizon_guarded
candidate_set: knn-regret
fallback_family: recent2000
```

## Implementation

Added:

```text
two_horizon_selection_risk_gate
```

The gate computes:

```text
recency_gate = recency_weighted_selection_risk_gate(...)
latest_gate = latest_cut_selection_risk_gate(...)
allowed = recency_gate[series].allowed and latest_gate[series].allowed
```

The policy is intentionally conservative. It does not average the two horizons.
It requires both to pass.

## Frozen Balanced Check

Frozen balanced config:

```text
policy: fallback_veto_two_horizon_guarded
min_validation_lift: 0
min_series_validation_lift: -0.001
series_risk_decay: 0.25
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.00015
```

Expanded result, routed cuts only:

```text
selected_mae: 0.09578004644453712
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.00009981752392164422
positive/negative routed series: 5/5
```

Late result, routed cuts only:

```text
selected_mae: 0.0969406774046013
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.000032621940338081745
positive/negative routed series: 7/3
```

Verdict:

```text
frozen balanced two-horizon check: failed late
```

## Late Sweep

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-two-horizon-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_two_horizon_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --min-series-validation-lift 0.0025 \
  --series-risk-decay 0.05 \
  --series-risk-decay 0.1 \
  --veto-feature-mode global \
  --veto-feature-mode series \
  --veto-k 25 \
  --veto-k 50 \
  --veto-regret-threshold 0.0001 \
  --veto-regret-threshold 0.00015 \
  --veto-regret-threshold 0.00025
```

Best late row:

```text
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_feature_mode: series
veto_k: 50
veto_regret_threshold: 0.00025
selected_mae: 0.09689844762984086
fallback_mae: 0.09690805546426322
MAE delta vs fallback: 0.000009607834422359351
positive/negative routed series: 3/3
```

Same config on expanded:

```text
selected_mae: 0.09589486515993427
fallback_mae: 0.09587986396845877
MAE delta vs fallback: -0.000015001191475502718
positive/negative routed series: 4/4
```

Verdict:

```text
late-best two-horizon config failed expanded retest
```

## Expanded Sweep And Join

Expanded sweep command used the same 48-row parameter box as the late sweep.

Best expanded row:

```text
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_feature_mode: series
veto_k: 25
veto_regret_threshold: 0.00015
MAE delta vs fallback: 0.000035720968027716515
positive/negative routed series: 4/4
```

Joined late/expanded result:

```text
both_positive_count: 0
```

Best shared near-miss:

```text
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.0001
late delta: -0.0000019969607878561613
expanded delta: 0.000014219138773169382
```

## Near-Miss Attribution

Late near-miss result, routed cuts only:

```text
selected_mae: 0.09691005242505107
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.0000019969607878561613
positive/negative routed series: 3/3
```

Expanded near-miss result, routed cuts only:

```text
selected_mae: 0.0958656448296856
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.000014219138773169382
positive/negative routed series: 2/6
```

Late near-miss top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0002044349 |
| `BAMLH0A0HYM2:realized_vol_20` | 0.0000627130 |
| `DEXJPUS:realized_vol_20` | 0.0000018838 |

Late near-miss top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `DCOILWTICO:realized_vol_20` | -0.0001146945 |
| `DGS10:realized_vol_20` | -0.0001014310 |
| `SP500:realized_vol_20` | -0.0000728759 |

## Strict Near-Miss Check

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-two-horizon-fallback-veto-late-near-miss-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_two_horizon_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --min-series-validation-lift 0.0025 \
  --min-series-validation-lift 0.005 \
  --min-series-validation-lift 0.0075 \
  --min-series-validation-lift 0.01 \
  --series-risk-decay 0.05 \
  --series-risk-decay 0.1 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.0001
```

Result:

```text
best strict row was still min_series_validation_lift=0.001
best strict late delta: -0.0000019969607878561613
```

Tightening the series lift threshold did not repair the near-miss.

## Interpretation

Fact: Two-horizon guard is implemented and reproducible.

Fact: The frozen balanced check still fails on the late archive.

Fact: The late-best row fails expanded retest.

Fact: The same 48-row parameter box contains no config with positive delta on
both late and expanded.

Inference: The current failure is not just a guard strictness problem. The
router needs regime-state information that explains when the same series should
trust or distrust adapter overrides.

Recommendation: Do not promote `fallback_veto_two_horizon_guarded`. Use it as
diagnostic evidence for the next step: regime-aware routing.

## Current Verdict

```text
two-horizon policy implemented: yes
late-only positive candidate found: yes
expanded transfer passed: no
shared positive config found: no
promotion status: blocked
next step: regime-aware router feature or classifier
```
