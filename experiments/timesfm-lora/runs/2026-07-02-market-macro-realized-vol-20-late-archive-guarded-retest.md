# 2026-07-02 Market Macro Realized Vol 20 Late Archive Guarded Retest

## Goal

Freeze the balanced guarded fallback-veto candidate from the expanded
alignment-normalized surface and retest it on a later chronological subset.

Frozen candidate:

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

Previous expanded result:

```text
MAE delta vs fallback: 0.00009981752392164422
positive/negative routed series: 5/5
```

The question for this run:

```text
Does the same frozen policy remain positive on later cuts only?
```

## Late Surface Build

Build late full-feature rows:

```bash
uv run python scripts/join_prediction_archives.py \
  --grid expanded \
  --cut 4500 \
  --cut 4750 \
  --cut 5000 \
  --cut 5250 \
  --cut 5500 \
  --output reports/router-rows-late-regime-full-market-macro-realized-vol-20-h20-r4.json
```

Output:

```text
rows: 2500
cuts: 4500, 4750, 5000, 5250, 5500
families: zero-shot, full, recent1500, recent2000, recent3000
best fixed family by MAE: recent2000
fixed recent2000 MAE: 0.09464968320750643
leaky oracle MAE: 0.0905343793634257
```

Create comparable alignment-normalized rows:

```bash
uv run python scripts/ablate_router_features.py \
  --preset alignment-normalized \
  --input reports/router-rows-late-regime-full-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Kept groups:

```text
context
prediction_context_alignment
prediction_disagreement
prediction_disagreement_normalized
prediction_summaries
```

## Frozen Retest

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
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-frozen-balanced-guarded-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Frozen guarded result, routed cuts only:

```text
windows: 2000
selected_mae: 0.0969406774046013
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.000032621940338081745
relative lift vs fallback: -0.00033662774659751313
positive/negative routed series: 7/3
```

Verdict:

```text
frozen late retest: failed
reason: selected MAE is still above fixed recent2000 fallback MAE
```

## Unguarded Comparison

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-frozen-unguarded-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Unguarded result, routed cuts only:

```text
windows: 2000
selected_mae: 0.09698674797866653
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.00007869251440331682
positive/negative routed series: 7/3
```

Comparison:

| Policy | MAE delta vs fallback | Split |
|---|---:|---:|
| unguarded fallback-veto | -0.0000786925 | 7 / 3 |
| frozen balanced guarded | -0.0000326219 | 7 / 3 |

## Diagnostic Sweep

Diagnostic only. This does not count as promotion evidence because it tunes on
the late surface.

Command:

```bash
uv run python scripts/sweep_router_policies.py \
  --candidate-set knn-regret \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-policy-sweep-diagnostic-guarded-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
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

Best diagnostic row:

```text
policy: fallback_veto_series_guarded
min_validation_lift: 0.0
min_series_validation_lift: 0.001
series_risk_decay: 0.05
veto_k: 25
veto_regret_threshold: 0.00015
selected_mae: 0.09691135269292628
fallback_mae: 0.09690805546426322
MAE delta vs fallback: -0.0000032972286630600367
positive/negative routed series: 3/3
```

## Best Diagnostic Attribution

Command:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto_series_guarded \
  --min-validation-lift 0 \
  --min-series-validation-lift 0.001 \
  --series-risk-decay 0.05 \
  --veto-feature-mode global \
  --veto-k 25 \
  --veto-regret-threshold 0.00015 \
  --input reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-diagnostic-guarded-fallback-veto-msvl001-decay005-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Best diagnostic top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0002044349 |
| `BAMLH0A0HYM2:realized_vol_20` | 0.0000604188 |
| `DEXJPUS:realized_vol_20` | 0.0000018838 |

Best diagnostic top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `DCOILWTICO:realized_vol_20` | -0.0001289754 |
| `DGS10:realized_vol_20` | -0.0000978585 |
| `SP500:realized_vol_20` | -0.0000728759 |

## Frozen Failure Attribution

Frozen guarded top positives:

| Series | MAE delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0005613355 |
| `DGS10:realized_vol_20` | 0.0001616912 |
| `BAMLH0A0HYM2:realized_vol_20` | 0.0001265247 |

Frozen guarded top negatives:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | -0.0012531175 |
| `DGS2:realized_vol_20` | -0.0000738041 |
| `DTWEXBGS:realized_vol_20` | -0.0000415819 |

## Interpretation

Fact: The frozen balanced guarded policy failed on the late surface.

Fact: The per-series guard still improved over unguarded fallback-veto, reducing
loss from `-0.0000786925` to `-0.0000326219`.

Fact: A late-specific diagnostic sweep reached near break-even at
`-0.0000032972`, but still did not clear fallback.

Fact: The frozen failure pattern is dominated by `DFF`, not by the same
SP500/DGS10/BAMLH0A0HYM2 downside pattern seen earlier.

Inference: The guarded policy helps, but it is not temporally robust enough.
The failure appears regime-sensitive rather than a fixed-series blocklist
problem.

Recommendation: Do not promote the balanced guarded policy. The next router
step should test a latest-cut downside guard or temporal-regime guard that can
block overrides when the latest prior cut shows concentrated downside.

## Current Verdict

```text
late comparable archive: built
frozen balanced guarded retest: failed
guard helped vs unguarded: yes
diagnostic sweep: near break-even, still negative
promotion status: blocked
next step: latest-cut or temporal-regime downside guard
```

