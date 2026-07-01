# 2026-07-02 Market Macro Realized Vol 20 Regime-Full Router

## Goal

Test whether no-leak regime features repair the two-horizon router's temporal
instability across late and expanded surfaces.

Previous two-horizon blocker:

```text
alignment-normalized both_positive_count: 0
best shared near-miss late delta: -0.0000019969607878561613
best shared near-miss expanded delta: 0.000014219138773169382
```

This run compares:

```text
alignment-normalized
regime-alignment
regime-full
```

## Regime-Alignment Surface

Generated with:

```bash
uv run python scripts/ablate_router_features.py \
  --preset regime-alignment \
  --input reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-rows-expanded-regime-alignment-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/ablate_router_features.py \
  --preset regime-alignment \
  --input reports/router-rows-late-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-rows-late-regime-alignment-market-macro-realized-vol-20-h20-r4.json
```

Kept groups:

```text
context
context_regime
prediction_context_alignment
prediction_disagreement
prediction_summaries
```

Regime-alignment failed:

```text
late best delta: -0.000008465304071225699
expanded best delta: -0.000004622446828056459
both_positive_count: 0
```

## Regime-Full Sweep

Late command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-late-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-two-horizon-fallback-veto-late-regime-full-market-macro-realized-vol-20-h20-r4.json \
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

Expanded command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-two-horizon-fallback-veto-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json \
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

Best single-surface rows:

| Surface | Best Delta | Config |
|---|---:|---|
| Late regime-full | 0.0000415758 | `series/k50/thr0.00025/msvl0.001/decay0.05` |
| Expanded regime-full | 0.0000441823 | `series/k25/thr0.0001/msvl0.001/decay0.05` |

## Joined Frozen Configs

Joined by exact parameter key:

```text
min_validation_lift
min_series_validation_lift
series_risk_decay
veto_k
veto_regret_threshold
veto_feature_mode
```

Result:

```text
both_positive_count: 40
```

Best shared config by minimum delta:

```text
policy: fallback_veto_two_horizon_guarded
candidate_set: knn-regret
min_validation_lift: 0
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.00025
late delta: 0.00002355445156944358
expanded delta: 0.000019947579099705015
```

## Shared Best Attribution

Late regime-full, routed cuts only:

```text
selected_mae: 0.09688450101269377
fallback_mae: 0.09690805546426322
MAE delta vs fallback: 0.00002355445156944358
positive/negative routed series: 3/4
```

Expanded regime-full, routed cuts only:

```text
selected_mae: 0.09585991638935906
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.000019947579099705015
positive/negative routed series: 3/3
```

Late top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0004450734 |
| `BAMLH0A0HYM2:realized_vol_20` | 0.0001609228 |
| `DGS2:realized_vol_20` | 0.0000159380 |

Late top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `DGS10:realized_vol_20` | -0.0001424441 |
| `SP500:realized_vol_20` | -0.0001391176 |
| `DCOILWTICO:realized_vol_20` | -0.0001044142 |

Expanded top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0003794032 |
| `DGS2:realized_vol_20` | 0.0001803004 |
| `DEXUSEU:realized_vol_20` | 0.0000054333 |

Expanded top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | -0.0002927554 |
| `DCOILWTICO:realized_vol_20` | -0.0000700318 |
| `DTWEXBGS:realized_vol_20` | -0.0000028739 |

## Interpretation

Fact: Regime-alignment failed on both late and expanded.

Fact: Regime-full produced 40 shared positive configurations in the same 48-row
parameter box.

Fact: The best shared frozen config is positive on both late and expanded.

Inference: Regime features are helpful only when combined with the full
no-leak prediction feature surface. Regime alone with alignment is not enough.

Recommendation: Treat this as the next router candidate checkpoint. Do not
call it final release until it is validated on a second target and frozen into
a manifest.

## Current Verdict

```text
regime-alignment: failed
regime-full: shared positive
promotion status: candidate checkpoint
next step: freeze router manifest and validate second financial target
```
