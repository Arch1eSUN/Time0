# 2026-07-02 Market Macro Realized Vol 20 Latest-Cut Guard

## Goal

Test whether a latest-prior-cut downside guard can repair the late-archive
failure from the frozen guarded fallback-veto policy without breaking the
expanded alignment-normalized surface.

Previous blocker:

```text
frozen guarded fallback-veto late delta: -0.000032621940338081745
best recency-guard diagnostic late delta: -0.0000032972286630600367
```

New policy:

```text
policy: fallback_veto_latest_cut_guarded
candidate_set: knn-regret
fallback_family: recent2000
```

## Implementation

Added a latest-cut per-series gate:

```text
latest_cut_selection_risk_gate
```

The gate uses:

```text
validation_cut = prior_cuts[-1]
validation_selected = selected_by_cut[validation_cut]
```

Then it calls the existing per-series validation gate:

```text
series_validation_gate(...)
```

Blocked series revert to the fixed fallback family.

## Late Smoke Checks

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto_latest_cut_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --series-risk-decay 0.1 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-latest-cut-guarded-fallback-veto-msvl001-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Result, routed cuts only:

```text
selected_mae: 0.09691135269292628
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.0000032972286630600367
positive/negative routed series: 3/3
```

This matches the previous near-break-even diagnostic level, but still does not
clear fallback.

## Late Diagnostic Sweep

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-latest-cut-guarded-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_latest_cut_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift -0.001 \
  --min-series-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --min-series-validation-lift 0.0025 \
  --veto-feature-mode global \
  --veto-feature-mode series \
  --veto-k 15 \
  --veto-k 25 \
  --veto-k 50 \
  --veto-regret-threshold 0.00005 \
  --veto-regret-threshold 0.0001 \
  --veto-regret-threshold 0.00015 \
  --veto-regret-threshold 0.00025
```

Best late row:

```text
policy: fallback_veto_latest_cut_guarded
min_validation_lift: 0.0
min_series_validation_lift: 0.001
series_risk_decay: 0.1
veto_feature_mode: series
veto_k: 50
veto_regret_threshold: 0.00025
selected_mae: 0.09689844762984086
fallback_mae: 0.09690805546426322
MAE delta vs fallback: 0.000009607834422359351
relative lift vs fallback: 0.00009914381602572175
positive/negative routed series: 3/3
```

## Expanded Retest Of Late-Best Config

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto_latest_cut_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --series-risk-decay 0.1 \
  --veto-feature-mode series \
  --veto-k 50 \
  --veto-regret-threshold 0.00025 \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-latest-cut-guarded-fallback-veto-best-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Result, routed cuts only:

```text
selected_mae: 0.09589486515993427
fallback_mae: 0.09587986396845877
MAE delta vs fallback: -0.000015001191475502718
relative lift vs fallback: -0.00015645820566075898
positive/negative routed series: 4/4
```

Verdict:

```text
late-best latest-cut config failed expanded retest
```

## Expanded Narrow Sweep

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-latest-cut-guarded-fallback-veto-expanded-narrow-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_latest_cut_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift -0.001 \
  --min-series-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --veto-feature-mode global \
  --veto-feature-mode series \
  --veto-k 25 \
  --veto-regret-threshold 0.00015
```

Best expanded narrow row:

```text
min_series_validation_lift: -0.001
veto_feature_mode: series
veto_k: 25
veto_regret_threshold: 0.00015
MAE delta vs fallback: 0.00019838923819456844
positive/negative routed series: 6/4
```

Same config on late:

```text
MAE delta vs fallback: -0.00004261579686283545
positive/negative routed series: 7/3
```

Verdict:

```text
expanded-best narrow config failed late retest
```

## Expanded K50 Strict Sweep

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-latest-cut-guarded-fallback-veto-expanded-k50-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_latest_cut_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --min-series-validation-lift 0.0025 \
  --veto-feature-mode global \
  --veto-feature-mode series \
  --veto-k 50 \
  --veto-regret-threshold 0.00005 \
  --veto-regret-threshold 0.0001 \
  --veto-regret-threshold 0.00015 \
  --veto-regret-threshold 0.00025
```

Best expanded k50 strict row:

```text
min_series_validation_lift: 0.001
veto_feature_mode: series
veto_k: 50
veto_regret_threshold: 0.00015
MAE delta vs fallback: -0.000012337300042117305
positive/negative routed series: 4/4
```

## Interpretation

Fact: The latest-cut policy can produce a late-positive configuration.

Fact: The late-positive configuration failed expanded retest.

Fact: The expanded-positive narrow configuration failed late retest.

Fact: The stricter k50 subspace failed expanded retest.

Inference: Latest-cut gating reacts to recent downside, but the current version
is too myopic to serve as a promotion-quality router policy.

Recommendation: Keep `fallback_veto_latest_cut_guarded` as an experimental
policy and build a two-horizon temporal guard next: latest cut must be safe,
and longer prior history must also be safe.

## Current Verdict

```text
latest-cut guard implemented: yes
late-only positive candidate found: yes
expanded transfer passed: no
promotion status: blocked
next step: two-horizon temporal guard
```
