# 2026-07-02 Market Macro Realized Vol 20 KNN Downside Budget

## Goal

Test whether per-series downside budgets improve the current KNN-regret router
frontier.

Previous checkpoint:

```text
best aggregate: knn-regret validation_gated, min_validation_lift=0.0
MAE delta: 0.0002705342
positive/negative routed series: 6/4

best risk-balanced: knn-regret validation_gated, min_validation_lift=0.005
MAE delta: 0.0002687244
positive/negative routed series: 7/3
```

The question for this run:

```text
If KNN-regret still hurts some series, can a per-series downside budget block
the risky overrides while preserving most of the aggregate lift?
```

## Method

No new LoRA adapter was trained in this run.

This run reuses the existing prediction archive and causal router replay. The
new thing is the policy sweep range:

```text
candidate set: knn-regret
policies: validation_gated, series_guarded, series_risk_penalized
min_validation_lift: 0, 0.005
min_series_validation_lift: -0.005, -0.0025, -0.001, -0.0005, 0
series_risk_decay: 0.05, 0.1, 0.25
```

Negative `min_series_validation_lift` means a controlled downside budget:

```text
required_metric = fallback_metric * (1 - min_series_validation_lift)

min_series_validation_lift = -0.0025
required_metric = fallback_metric * 1.0025
```

So the candidate may be up to 0.25% worse than fallback on that series'
validation evidence before the router blocks it.

## Commands

Policy sweep:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-knn-regret-downside-budget-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy validation_gated \
  --policy series_guarded \
  --policy series_risk_penalized \
  --min-validation-lift 0 \
  --min-validation-lift 0.005 \
  --min-series-validation-lift -0.005 \
  --min-series-validation-lift -0.0025 \
  --min-series-validation-lift -0.001 \
  --min-series-validation-lift -0.0005 \
  --min-series-validation-lift 0 \
  --series-risk-decay 0.05 \
  --series-risk-decay 0.1 \
  --series-risk-decay 0.25
```

Attribution for the best 8/2 risk candidate:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy series_risk_penalized \
  --min-validation-lift 0.005 \
  --min-series-validation-lift -0.0025 \
  --series-risk-decay 0.25 \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-knn-regret-downside-budget-mvl005-msvl-0025-decay025-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Generated JSON reports remain ignored local artifacts.

## Results

Top rows by MAE delta:

| Rank | Policy | Min validation | Min series | Decay | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `validation_gated` | 0.000 | 0.0000 | 0.10 | 0.0002705342 | 6 / 4 |
| 2 | `validation_gated` | 0.005 | 0.0000 | 0.10 | 0.0002687244 | 7 / 3 |
| 3 | `series_guarded` | 0.000 | -0.0050 | 0.10 | 0.0002678626 | 6 / 4 |
| 4 | `series_risk_penalized` | 0.000 | -0.0050 | 0.05 | 0.0002678626 | 6 / 4 |
| 5 | `series_risk_penalized` | 0.000 | -0.0050 | 0.25 | 0.0002606529 | 6 / 4 |
| 6 | `series_guarded` | 0.005 | -0.0050 | 0.10 | 0.0002527602 | 7 / 3 |
| 11 | `series_risk_penalized` | 0.005 | -0.0025 | 0.25 | 0.0002451542 | 8 / 2 |

Best aggregate remains:

```text
policy: validation_gated
min_validation_lift: 0.0
MAE delta: 0.0002705342
positive/negative routed series: 6/4
```

Best current risk-spread candidate:

```text
policy: series_risk_penalized
min_validation_lift: 0.005
min_series_validation_lift: -0.0025
series_risk_decay: 0.25
MAE delta: 0.0002451542
positive/negative routed series: 8/2
```

## Risk Candidate Attribution

Routed cuts only:

```text
windows: 5000
selected_counts:
  full: 307
  recent1500: 409
  recent2000: 3116
  recent3000: 483
  zero-shot: 685

selected_mae: 0.0917781256
fallback_mae: 0.0920232799
MAE delta vs fallback: 0.0002451542
relative lift vs fallback: 0.0026640459
positive/negative routed series: 8/2
```

Top positive series:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | 0.0011800863 |
| `VIXCLS:realized_vol_20` | 0.0006898982 |
| `DGS2:realized_vol_20` | 0.0004900040 |

Top negative series:

| Series | MAE delta vs fallback |
|---|---:|
| `BAMLH0A0HYM2:realized_vol_20` | -0.0001815629 |
| `DEXJPUS:realized_vol_20` | -0.0000600526 |

Compared with `validation_gated mvl=0.005`:

```text
validation_gated mvl=0.005:
  MAE delta: 0.0002687244
  positive/negative series: 7/3
  negative series: SP500, BAMLH0A0HYM2, DEXJPUS

downside budget candidate:
  MAE delta: 0.0002451542
  positive/negative series: 8/2
  negative series: BAMLH0A0HYM2, DEXJPUS
```

## Interpretation

Fact: The downside-budget sweep did not beat the best aggregate policy.

Fact: The strongest aggregate downside-budget row reached MAE delta
`0.0002678626`, slightly below `validation_gated mvl=0.005` at `0.0002687244`.

Fact: The best risk-spread row improved the series split to `8/2`, but lowered
MAE delta to `0.0002451542`.

Inference: Per-series risk control is useful as a release safety dial, not yet
as the primary frontier policy.

Recommendation: Keep `knn-regret validation_gated mvl=0.005` as the current
best risk-balanced research checkpoint. Keep the `series_risk_penalized
mvl=0.005, min_series=-0.0025, decay=0.25` row as a conservative candidate for
future release review when the project prioritizes fewer harmed series over
maximum aggregate lift.

## Current Verdict

```text
frontier moved: no
risk surface improved: yes
best aggregate remains: knn-regret validation_gated mvl0
best current research checkpoint remains: knn-regret validation_gated mvl0.005
best conservative risk candidate: series_risk_penalized mvl0.005 msvl-0.0025 decay0.25
promotion status: blocked
next step: inspect which series repeatedly require fallback and whether a learned no-leak blocklist signal can predict that before routing
```
