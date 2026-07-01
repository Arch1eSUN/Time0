# 2026-07-02 Market Macro Realized Vol 20 Router Manifest

## Goal

Freeze the shared-positive regime-full router candidate into a structured
manifest and validate that the manifest reproduces late and expanded results.

Previous candidate:

```text
policy: fallback_veto_two_horizon_guarded
candidate_set: knn-regret
feature_surface: regime-full
late delta: 0.00002355445156944358
expanded delta: 0.000019947579099705015
```

## Manifest

Created:

```text
manifests/router/market-macro-realized-vol-20-regime-full-two-horizon.json
```

Frozen router:

```text
policy: fallback_veto_two_horizon_guarded
candidate_set: knn-regret
selection_metric: mae
cold_start_family: recent2000
fallback_family: recent2000
min_validation_lift: 0
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.00025
softmax_steps: 2000
```

Required runtime feature groups:

```text
context
context_regime
prediction_context_alignment
prediction_disagreement
prediction_disagreement_normalized
prediction_summaries
```

Required validation surfaces:

```text
late_regime_full
expanded_regime_full
```

## Evaluator

Added:

```text
scripts/evaluate_router_manifest.py
```

The evaluator:

```text
1. loads the manifest
2. rebuilds attribution reports from the frozen parameters
3. verifies rows, cuts, families, and required runtime feature groups
4. compares observed delta against expected delta
5. fails if any required surface is below the promotion floor or mismatches expected values
```

## Validation Command

```bash
uv run python scripts/evaluate_router_manifest.py \
  --manifest manifests/router/market-macro-realized-vol-20-regime-full-two-horizon.json \
  --output reports/router-manifest-eval-market-macro-realized-vol-20-regime-full-two-horizon.json \
  --tolerance 1e-12
```

## Result

```text
passed: true
```

Late regime-full:

```text
selected_metric: 0.09688450101269377
fallback_metric: 0.09690805546426322
delta_vs_fallback: 0.00002355445156944358
expected_delta_vs_fallback: 0.00002355445156944358
delta_error: 0
positive/negative routed series: 3/4
```

Expanded regime-full:

```text
selected_metric: 0.09585991638935906
fallback_metric: 0.09587986396845877
delta_vs_fallback: 0.000019947579099705015
expected_delta_vs_fallback: 0.000019947579099705015
delta_error: 0
positive/negative routed series: 3/3
```

## Interpretation

Fact: The router candidate is now represented as a frozen manifest.

Fact: The manifest evaluator reproduced both required surfaces exactly within
`1e-12` tolerance.

Fact: Both required surfaces remain above the fallback baseline.

Inference: This candidate has moved from exploratory sweep result to
reproducible engineering checkpoint.

Recommendation: Keep status as `candidate`, not release. Next validation should
apply the same manifest pattern to a second financial target.

## Current Verdict

```text
manifest frozen: yes
manifest evaluator added: yes
late validation: passed
expanded validation: passed
promotion status: candidate
next step: second financial target validation
```
