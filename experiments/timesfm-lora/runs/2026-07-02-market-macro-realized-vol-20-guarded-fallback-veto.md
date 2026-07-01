# 2026-07-02 Market Macro Realized Vol 20 Guarded Fallback-Veto

## Goal

Add and test a guarded fallback-veto router policy that preserves aggregate
lift while reducing per-series downside on the expanded alignment-normalized
surface.

Previous diagnostic problem:

```text
policy: fallback_veto
min_validation_lift: 0.0
veto_k: 25
veto_regret_threshold: 0.00015
MAE delta vs fallback: 0.00003027209
positive/negative series: 3/7
```

The question for this run:

```text
Can a per-series downside guard keep aggregate lift positive while improving
the positive/negative series split?
```

## Implementation

Changed files:

```text
scripts/summarize_router_attribution.py
scripts/sweep_router_policies.py
```

New policy:

```text
fallback_veto_series_guarded
```

Behavior:

```text
1. Run the same aggregate fallback-veto selector.
2. Replay prior-cut fallback-veto selections causally.
3. Build a recency-weighted per-series downside gate from prior cuts.
4. Replace blocked current overrides with fallback family recent2000.
```

No-leak property:

```text
Current-cut labels and current-cut errors are not used for selection.
The guard sees only prior cuts and causal prior fallback-veto selections.
```

## Smoke Attribution

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto_series_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0 \
  --series-risk-decay 0.25 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-guarded-fallback-veto-smoke-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Smoke result:

```text
selected_mae: 0.09577650515059988
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.00010335881785888956
relative lift vs fallback: 0.0010780033844529767
positive/negative routed series: 4/6
```

## Guard Sweep

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-guarded-fallback-veto-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy fallback_veto_series_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift -0.001 \
  --min-series-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --min-series-validation-lift 0.0025 \
  --series-risk-decay 0.05 \
  --series-risk-decay 0.1 \
  --series-risk-decay 0.25 \
  --series-risk-decay 0.5 \
  --series-risk-decay 0.75 \
  --series-risk-decay 1.0 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015
```

Top rows:

| Rank | `min_series_validation_lift` | `series_risk_decay` | MAE delta | Split |
|---:|---:|---:|---:|---:|
| 1 | 0.000 | 0.25 | 0.0001033588 | 4 / 6 |
| 2 | -0.001 | 0.05 | 0.0001001340 | 4 / 6 |
| 3 | -0.001 | 0.10 | 0.0001001340 | 4 / 6 |
| 4 | -0.001 | 0.25 | 0.0000998175 | 5 / 5 |
| 5 | 0.000 | 0.50 | 0.0000981008 | 4 / 6 |
| 6 | 0.000 | 0.75 | 0.0000981008 | 4 / 6 |

## Balanced Candidate Attribution

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto_series_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift -0.001 \
  --series-risk-decay 0.25 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-guarded-fallback-veto-balanced-k25-thr00015-msvl-neg001-decay025-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Balanced candidate:

```text
selected_mae: 0.09578004644453712
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.00009981752392164422
relative lift vs fallback: 0.001041068685229683
positive/negative routed series: 5/5
```

Selected counts:

```text
full: 201
recent1500: 132
recent2000: 3044
recent3000: 317
zero-shot: 306
```

## Comparison

Routed cuts only:

| Policy | Delta vs fallback | Relative lift | Split | Selected MAE |
|---|---:|---:|---:|---:|
| Unguarded diagnostic fallback-veto | 0.0000302721 | 0.0003157294 | 3 / 7 | 0.0958495919 |
| Best guarded by delta | 0.0001033588 | 0.0010780034 | 4 / 6 | 0.0957765052 |
| Balanced guarded candidate | 0.0000998175 | 0.0010410687 | 5 / 5 | 0.0957800464 |

## Attribution

Balanced candidate top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `DGS2:realized_vol_20` | 0.0006113791 |
| `VIXCLS:realized_vol_20` | 0.0004381169 |
| `DFF:realized_vol_20` | 0.0001653772 |

Balanced candidate top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `BAMLH0A0HYM2:realized_vol_20` | -0.0001027449 |
| `DCOILWTICO:realized_vol_20` | -0.0000753733 |
| `SP500:realized_vol_20` | -0.0000474838 |

Recurring downside comparison:

| Series | Unguarded delta | Balanced guarded delta |
|---|---:|---:|
| `SP500:realized_vol_20` | -0.0004575981 | -0.0000474838 |
| `DGS10:realized_vol_20` | -0.0003117676 | no longer top-3 negative |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0000633409 | -0.0001027449 |

## Interpretation

Fact: The guarded policy improved aggregate lift over the unguarded diagnostic
fallback-veto.

Fact: The best aggregate row remained majority-negative by series, with a `4/6`
split.

Fact: The balanced candidate kept nearly the same aggregate lift and improved
the split to `5/5`.

Fact: SP500 and DGS10 downside were substantially reduced, but downside shifted
toward `BAMLH0A0HYM2` and `DCOILWTICO`.

Inference: Per-series downside control is the right next layer, but the current
guard is still a research candidate rather than a release policy.

Recommendation: Freeze the balanced candidate as the next policy to test on a
separate target or archive:

```text
policy: fallback_veto_series_guarded
candidate_set: knn-regret
min_validation_lift: 0
min_series_validation_lift: -0.001
series_risk_decay: 0.25
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.00015
```

## Current Verdict

```text
new policy implemented: yes
aggregate lift improved: yes
coverage improved: yes, 3/7 -> 5/5
promotion status: not yet
best research candidate: balanced guarded fallback-veto
next step: test balanced guarded policy on a separate target or later comparable archive
```

