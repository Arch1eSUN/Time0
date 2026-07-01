# 2026-07-02 Market Macro Realized Vol 20 Expanded Alignment-Normalized Fallback-Veto

## Goal

Rebuild the expanded router-row surface with the same `alignment-normalized`
feature groups used by the previous best fallback-veto result, then retest
whether formal fallback-veto generalizes.

The previous expanded test was not fully comparable because the old expanded
router rows lacked:

```text
prediction_context_alignment
prediction_disagreement_normalized
```

## Surface Rebuild

Build full-feature expanded rows from existing prediction archives:

```bash
uv run python scripts/join_prediction_archives.py \
  --grid expanded \
  --output reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json
```

Output:

```text
rows: 4500
cuts: 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500
families: zero-shot, full, recent1500, recent2000, recent3000
best fixed family by MAE: recent2000
recent2000 fixed MAE: 0.09280977997668428
leaky oracle MAE: 0.08769205170905402
```

Create the comparable feature surface:

```bash
uv run python scripts/ablate_router_features.py \
  --preset alignment-normalized \
  --input reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Kept groups:

```text
context
prediction_context_alignment
prediction_disagreement
prediction_disagreement_normalized
prediction_summaries
```

## Frozen Formal Policy

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-frozen-fallback-veto-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy validation_gated \
  --policy fallback_veto \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.0002
```

Frozen formal result:

```text
policy: fallback_veto
candidate_set: knn-regret
min_validation_lift: 0.005
veto_feature_mode: global
veto_k: 50
veto_regret_threshold: 0.0002
routed_windows: 4000
selected_mae: 0.09592025094820161
fallback_mae: 0.09587986396845877
MAE delta vs fallback: -0.000040386979742845774
relative lift vs fallback: -0.00042122483357018243
positive/negative routed series: 6/4
```

Verdict:

```text
frozen formal policy: failed
reason: still below fixed recent2000 fallback baseline
```

## Frozen Attribution

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.0002 \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-frozen-fallback-veto-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | 0.0000883605 |
| `DGS2:realized_vol_20` | 0.0000830379 |
| `DCOILWTICO:realized_vol_20` | 0.0000429513 |

Top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `SP500:realized_vol_20` | -0.0002886293 |
| `DGS10:realized_vol_20` | -0.0002574667 |
| `VIXCLS:realized_vol_20` | -0.0000665578 |

## Diagnostic Sensitivity Sweep

This sweep is diagnostic only. It is not promotion evidence because it tunes on
the same surface being evaluated.

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-diagnostic-fallback-veto-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --policy validation_gated \
  --policy fallback_veto \
  --min-validation-lift 0 \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-k 50 \
  --veto-k 75 \
  --veto-regret-threshold 0.0001 \
  --veto-regret-threshold 0.00015 \
  --veto-regret-threshold 0.0002 \
  --veto-regret-threshold 0.00025
```

Best diagnostic row:

```text
policy: fallback_veto
min_validation_lift: 0.0
veto_feature_mode: global
veto_k: 25
veto_regret_threshold: 0.00015
routed_windows: 4000
selected_mae: 0.09584959187873444
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.000030272089724323048
relative lift vs fallback: 0.0003157293770700545
positive/negative routed series: 3/7
```

Top diagnostic rows:

| Rank | `mvl` | `k` | Threshold | MAE delta | Split |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.000 | 25 | 0.00015 | 0.0000302721 | 3 / 7 |
| 2 | 0.000 | 25 | 0.00020 | 0.0000286664 | 3 / 7 |
| 3 | 0.000 | 25 | 0.00025 | 0.0000256533 | 4 / 6 |
| 4 | 0.000 | 25 | 0.00010 | 0.0000232337 | 3 / 7 |
| 5 | 0.005 | 75 | 0.00010 | 0.0000131057 | 5 / 5 |

## Diagnostic Attribution

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-diagnostic-fallback-veto-k25-thr00015-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Routed cuts only:

```text
windows: 4000
selected_mae: 0.09584959187873444
fallback_mae: 0.09587986396845877
MAE delta vs fallback: 0.000030272089724323048
relative lift vs fallback: 0.0003157293770700545
positive/negative routed series: 3/7
positive delta windows: 579
negative delta windows: 639
```

Top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `DGS2:realized_vol_20` | 0.0006113791 |
| `VIXCLS:realized_vol_20` | 0.0004381169 |
| `DFF:realized_vol_20` | 0.0001653772 |

Top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `SP500:realized_vol_20` | -0.0004575981 |
| `DGS10:realized_vol_20` | -0.0003117676 |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0000633409 |

## Interpretation

Fact: Rebuilding the expanded surface with alignment-normalized features
improved the evaluation relative to the old expanded surface.

Fact: The frozen formal fallback-veto policy still failed promotion because its
delta remained negative: `-0.00004038698`.

Fact: A diagnostic nearby configuration produced positive aggregate delta:
`0.00003027209`.

Fact: The diagnostic winner had weak cross-series robustness: only `3/10`
series were positive.

Inference: The router is close enough to justify more research, but the current
aggregate objective can hide series-level downside.

Recommendation: Do not promote the diagnostic winner. The next policy should
combine fallback-veto with a per-series downside guard, especially for recurring
negative contributors such as `SP500` and `DGS10`.

## Current Verdict

```text
comparable alignment-normalized expanded surface: built
frozen formal fallback-veto: failed, -0.00004038698
diagnostic best fallback-veto: aggregate positive, 0.00003027209
diagnostic robustness: weak, 3/7 series split
promotion status: still blocked
next step: guarded fallback-veto with per-series downside control
```

