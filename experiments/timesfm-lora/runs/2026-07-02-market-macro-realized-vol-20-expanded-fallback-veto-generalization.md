# 2026-07-02 Market Macro Realized Vol 20 Expanded Fallback-Veto Generalization

## Goal

Test whether the formal fallback-veto policy generalizes from the
alignment-normalized router-row surface to the earlier expanded router-row
surface.

Previous checkpoint:

```text
formal best on alignment-normalized surface:
  fallback_veto mvl=0.005 global k=50 threshold=0.0002
  MAE delta: 0.0003088776
  positive/negative routed series: 9/1
```

The question for this run:

```text
Does formal fallback_veto still beat fixed recent2000 when the router rows do
not include alignment and normalized-disagreement features?
```

## Evaluation Surface

Source router rows:

```text
reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json
```

Surface details:

```text
rows: 4500
cuts: 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500
series: 10
families: zero-shot, full, recent1500, recent2000, recent3000
```

Runtime feature groups:

```text
context
cut
prediction_disagreement
prediction_summaries
series_id
start_index
window_index
```

Missing versus the latest alignment-normalized surface:

```text
prediction_context_alignment
prediction_disagreement_normalized
```

## Commands

Formal sweep:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-fallback-veto-knn-regret-expanded-market-macro-realized-vol-20-h20-r4.json \
  --policy validation_gated \
  --policy fallback_veto \
  --min-validation-lift 0 \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.00015 \
  --veto-regret-threshold 0.0002 \
  --veto-regret-threshold 0.00025
```

Best expanded attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-fallback-veto-knn-regret-expanded-global-k50-thr00015-market-macro-realized-vol-20-h20-r4.json
```

Generated JSON reports remain ignored local artifacts.

## Results

Sweep ranking:

| Rank | Policy | Min validation | Threshold | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|
| 1 | `fallback_veto` | 0.000 | 0.00015 | -0.0000468273 | 5 / 5 |
| 2 | `fallback_veto` | 0.005 | 0.00015 | -0.0000468273 | 5 / 5 |
| 3 | `fallback_veto` | 0.000 | 0.00020 | -0.0000737068 | 4 / 6 |
| 4 | `fallback_veto` | 0.005 | 0.00020 | -0.0000737068 | 4 / 6 |
| 5 | `fallback_veto` | 0.000 | 0.00025 | -0.0000807729 | 2 / 8 |
| 6 | `fallback_veto` | 0.005 | 0.00025 | -0.0000807729 | 2 / 8 |
| 7 | `validation_gated` | 0.000 | - | -0.0002021702 | 4 / 6 |
| 8 | `validation_gated` | 0.005 | - | -0.0002021702 | 4 / 6 |

Best expanded row:

```text
policy: fallback_veto
min_validation_lift: 0.0
feature_mode: global
k: 50
regret_threshold: 0.00015
MAE delta vs fallback: -0.0000468273
positive/negative routed series: 5/5
```

Best expanded attribution, routed cuts only:

```text
windows: 4000
selected_mae: 0.0959266912
fallback_mae: 0.0958798640
MAE delta vs fallback: -0.0000468273
relative lift vs fallback: -0.0004883952
positive/negative routed series: 5/5
```

## What Improved And What Failed

Fallback-veto improved over validation-gated on the expanded surface:

```text
validation_gated best:
  MAE delta: -0.0002021702
  split: 4/6

fallback_veto best:
  MAE delta: -0.0000468273
  split: 5/5
```

But fallback-veto still failed the promotion baseline:

```text
best fallback_veto delta:
  -0.0000468273

required for promotion:
  > 0
```

## Attribution

Top positive series:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | 0.0005268410 |
| `DGS2:realized_vol_20` | 0.0000272370 |
| `DEXJPUS:realized_vol_20` | 0.0000100944 |

Top negative series:

| Series | MAE delta vs fallback |
|---|---:|
| `DGS10:realized_vol_20` | -0.0006345752 |
| `SP500:realized_vol_20` | -0.0001922201 |
| `VIXCLS:realized_vol_20` | -0.0001554748 |

The expanded-surface failure is concentrated most strongly in:

```text
DGS10:realized_vol_20
SP500:realized_vol_20
VIXCLS:realized_vol_20
```

## Interpretation

Fact: Formal fallback-veto did not generalize to the expanded router-row
surface.

Fact: It still reduced loss versus plain validation-gated routing on the same
surface, from `-0.0002021702` to `-0.0000468273`.

Fact: The expanded surface lacks the alignment and normalized-disagreement
feature groups used by the current best alignment-normalized result.

Inference: The fallback-veto signal appears to depend on the richer
alignment-normalized feature surface. The policy concept is useful, but the
weaker expanded feature surface is not promotion-ready.

Recommendation: Do not promote fallback-veto as a feature-agnostic policy.
Treat the current best as scoped to the alignment-normalized router rows until
it is tested on a later archive with the same feature groups.

## Current Verdict

```text
generalization result: failed
best expanded fallback-veto delta: -0.0000468273
best expanded fallback-veto split: 5/5
plain validation-gated on expanded: worse, -0.0002021702
promotion status: blocked outside alignment-normalized surface
next step: build or export a later alignment-normalized archive, then retest formal fallback_veto
```
