# 2026-07-02 Market Macro Realized Vol 20 Formal Fallback-Veto Policy

## Goal

Promote the fallback-veto diagnostic into the formal no-leak router policy
surface.

Previous checkpoint:

```text
diagnostic best:
  knn-regret validation_gated mvl=0.005
  global fallback-veto k=50 threshold=0.0002
  MAE delta: 0.0003088776
  positive/negative routed series: 9/1
```

The question for this run:

```text
Does the same fallback-veto result hold when routed through
summarize_router_attribution.py and sweep_router_policies.py instead of a
standalone diagnostic script?
```

## Implementation

Added shared fallback-veto Module:

```text
scripts/router_fallback_veto.py
```

The Module owns:

```text
VetoExample
historical_veto_examples
apply_neighbor_regret_veto
```

Updated:

```text
scripts/evaluate_router_fallback_veto.py
scripts/summarize_router_attribution.py
scripts/sweep_router_policies.py
```

New formal policy:

```text
--policy fallback_veto
```

New policy parameters:

```text
--veto-k
--veto-regret-threshold
--veto-feature-mode global|series
```

## Guardrail

The formal policy keeps the same no-leak rule as the diagnostic:

```text
For each current cut:
  base KNN-regret selection uses only prior cuts
  fallback-veto examples are built only from completed prior cuts
  current-cut errors are used only for offline scoring
```

When there are no prior historical override examples, the policy fails open to
the base selection and records:

```text
mode: no_historical_override_examples
```

## Commands

Formal attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.0002 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-fallback-veto-knn-regret-mvl005-global-k50-thr0002-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Formal sweep:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-fallback-veto-knn-regret-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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

Generated JSON reports remain ignored local artifacts.

## Results

Formal attribution result:

```text
policy: fallback_veto
candidate_set: knn-regret
min_validation_lift: 0.005
veto_feature_mode: global
veto_k: 50
veto_regret_threshold: 0.0002
```

Routed cuts only:

```text
windows: 5000
selected_mae: 0.0917144023
fallback_mae: 0.0920232799
MAE delta vs fallback: 0.0003088776
relative lift vs fallback: 0.0033565156
positive/negative routed series: 9/1
```

Selected counts:

```text
full: 363
recent1500: 502
recent2000: 2766
recent3000: 569
zero-shot: 800
```

Top positive series:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0012367423 |
| `DFF:realized_vol_20` | 0.0012003241 |
| `DGS2:realized_vol_20` | 0.0004388087 |

Only negative series:

| Series | MAE delta vs fallback |
|---|---:|
| `DEXJPUS:realized_vol_20` | -0.0000342279 |

## Sweep Ranking

| Rank | Policy | Min validation | k | Threshold | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `fallback_veto` | 0.005 | 50 | 0.00020 | 0.0003088776 | 9 / 1 |
| 2 | `fallback_veto` | 0.005 | 50 | 0.00015 | 0.0003043504 | 9 / 1 |
| 3 | `fallback_veto` | 0.000 | 50 | 0.00020 | 0.0003038838 | 6 / 4 |
| 4 | `fallback_veto` | 0.005 | 50 | 0.00025 | 0.0003037471 | 7 / 3 |
| 5 | `fallback_veto` | 0.000 | 50 | 0.00025 | 0.0003035812 | 6 / 4 |
| 6 | `fallback_veto` | 0.000 | 50 | 0.00015 | 0.0003003556 | 6 / 4 |
| 7 | `validation_gated` | 0.000 | - | - | 0.0002705342 | 6 / 4 |
| 8 | `validation_gated` | 0.005 | - | - | 0.0002687244 | 7 / 3 |

## Per-Cut Veto Behavior

| Cut | Mode | Historical examples | Current overrides | Vetoed windows |
|---:|---|---:|---:|---:|
| 3500 | `no_historical_override_examples` | 0 | - | 0 |
| 3750 | `neighbor_regret_veto` | 442 | 430 | 11 |
| 4000 | `neighbor_regret_veto` | 872 | 437 | 63 |
| 4250 | `neighbor_regret_veto` | 1309 | 448 | 54 |
| 4750 | `neighbor_regret_veto` | 1757 | 389 | 93 |
| 5250 | `neighbor_regret_veto` | 2146 | 392 | 83 |

## Interpretation

Fact: The formal `fallback_veto` policy reproduced the diagnostic best result:
MAE delta `0.0003088776`, routed-series split `9/1`.

Fact: `sweep_router_policies.py` now ranks `fallback_veto` against
`validation_gated` in the same policy table.

Fact: The best formal row still uses `mvl=0.005`, `global`, `k=50`, and
`threshold=0.0002`.

Inference: The fallback-veto signal survived promotion from diagnostic script
to formal attribution/sweep surface.

Recommendation: Treat formal fallback-veto as the current best research
checkpoint. The next validation should test a different target or later archive,
not tune the same archive further.

## Current Verdict

```text
frontier moved: no new number, but diagnostic result is now formalized
formal best: fallback_veto mvl0.005 global k50 threshold0.0002
MAE delta: 0.0003088776
series split: 9/1
promotion status: still research checkpoint
next step: test the formal policy on another target or later archive
```
