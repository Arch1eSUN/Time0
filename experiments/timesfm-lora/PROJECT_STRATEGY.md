# Time0 TimesFM LoRA Project Strategy

Date: 2026-07-01

Purpose: define when the whole project can stop, when it should continue, and
how to publish a vertical-domain TimesFM LoRA adapter.

## Problem Framing

The project goal is not "keep training forever".

The goal is to produce a reproducible vertical-domain forecasting adapter, prove
that it improves over TimesFM zero-shot on future windows, and package it so
other people can evaluate or use it.

## Facts

Fact: the local Time0 repo remote is:

```text
git@github.com:Arch1eSUN/Time0.git
```

Fact: TimesFM upstream is Apache-2.0 licensed.

Fact: the TimesFM 2.5 Transformers checkpoint on Hugging Face is listed with an
`apache-2.0` license.

Fact: TimesFM upstream includes a LoRA fine-tuning example, so LoRA is an
expected adaptation path rather than an unsupported hack.

Sources:

```text
https://github.com/google-research/timesfm
https://huggingface.co/google/timesfm-2.5-200m-pytorch
https://github.com/google-research/timesfm/tree/master/experiments/finetuning
```

## Assumptions

Assumption: Time0 should specialize TimesFM for public market/macro risk
forecasting first.

Assumption: the first public release should avoid proprietary datasets and use
public reproducible inputs such as FRED series.

Assumption: the artifact should be a LoRA adapter plus evaluation report, not a
merged full base-model checkpoint.

## Project Stop Levels

| Level | Meaning | Project State |
|---|---|---|
| Research Stop | We know which target/settings work or do not work | stop experimenting blindly |
| Release Stop | We have a reproducible public adapter package | stop feature work; enter maintenance |
| Negative Stop | Scoped experiments fail to beat zero-shot | publish negative result or archive |
| Maintenance Mode | Adapter is released and only retrained on triggers | no continuous training loop |

## What Counts As Project Success

Project success requires all of:

1. At least one target passes Candidate Success from `SUCCESS_CRITERIA.md`.
2. The same adapter family passes at least 3 chronological holdout cut-points.
3. The adapter beats TimesFM zero-shot by at least 2% average primary-metric
   improvement across those cut-points.
4. The run is reproducible from public scripts, pinned dependencies, and public
   data sources.
5. The release includes a model card, evaluation report, training recipe, and
   base-model reference.
6. The artifact is published as a vertical-domain adapter, not presented as a
   general replacement for TimesFM.

After these are met, the main project can stop. Future work becomes
maintenance, not endless training.

## Current Finance Readiness Gate

Run the current release/stop gate with:

```bash
uv run python scripts/evaluate_finance_readiness.py
```

Current verdict as of 2026-07-02:

```text
continue_research
```

Reason:

```text
fixed recent2000 average MAE lift: 1.724% < 2.000% release gate
best router extra lift vs fallback: 0.316%
best router negative series: 3 > 0 release gate
zscore all-recent branch: fallback-sensitive
```

Interpretation: the finance direction has real signal, but it has not reached a
clean stopping point. Continue only with experiments that can move a failed gate:
average lift, per-series downside, or fallback sensitivity.

## What Counts As Project Failure

Stop the current research line if:

1. `level`, `log_change`, and `realized_vol_20` all fail Candidate Success.
2. For each promising target, `r=4` and one larger rank such as `r=8` both fail
   to beat TimesFM zero-shot on rolling holdout.
3. Longer training repeatedly makes holdout worse.
4. The adapter only wins because of one series and does not generalize across
   the 10-series market/macro set.

If this happens, the project should publish the eval harness and negative
result instead of forcing a model release.

## Should We Train Forever?

Recommendation: no.

Use event-triggered retraining:

| Trigger | Retrain? | Reason |
|---|---|---|
| New target family | Yes | new behavior needs adapter evidence |
| New public data window | Maybe | rerun rolling eval first |
| Metrics drift after release | Yes | adapter may be stale |
| New TimesFM base release | Yes | old adapter may not transfer |
| No data/model/eval change | No | repeated training adds little evidence |

Continuous training is expensive and can hide overfitting. Time0 should behave
like a reproducible research and release project: train, evaluate, release,
monitor, then retrain only when evidence changes.

## Publication Route

| Route | Use For | Not Good For | Recommendation |
|---|---|---|---|
| Google TimesFM upstream PR | bugfixes, reproducible fine-tuning scripts, docs, evaluation harness improvements | hosting our vertical finance adapter | contribute tooling only if generally useful |
| Arch1eSUN/Time0 GitHub | code, scripts, run notes, public eval reports, release recipe | large model artifacts | primary engineering repo |
| Hugging Face model repo | LoRA adapter, model card, eval table, intended-use notes | private data or unproven claims | primary adapter release channel |

Best release shape:

```text
GitHub: Arch1eSUN/Time0
  - training scripts
  - eval scripts
  - run notes
  - success criteria
  - release recipe

Hugging Face: Arch1eSUN/timesfm-2.5-market-macro-risk-lora
  - LoRA adapter files
  - model card
  - base model reference
  - eval metrics
  - data source statement
```

## Why Not Only Send It Back To TimesFM?

Inference: Google TimesFM upstream is the right place for general improvements,
not for every downstream vertical adapter.

If we discover a bug in TimesFM, a better example script, or a generic
evaluation improvement, we should open a PR upstream.

If we train a market/macro-risk adapter, it should live under our own identity
because:

1. The domain choice is ours.
2. The evaluation responsibility is ours.
3. The release cadence is ours.
4. Users need a clear model card explaining this is a specialized adapter.

## Minimum Hugging Face Release Checklist

Before publishing:

1. Adapter passes Promotion Ready.
2. `adapter_config.json` and adapter weights are present.
3. Model card states base model, target domain, target field, context length,
   horizon length, data sources, metrics, limitations, and intended use.
4. Model card says this is not financial advice and not a trading signal.
5. Evaluation report includes naive baseline, TimesFM zero-shot, and LoRA
   adapter metrics across rolling cut-points.
6. Training recipe can be reproduced from `Arch1eSUN/Time0`.
7. License compatibility is checked again at release time.

## Immediate Next Step

Build a prediction archive joiner before increasing LoRA capacity:

```text
field=realized_vol_20
method=prediction archive joiner
candidate_adapters=full-history,recent1500,recent2000,recent3000
selection_data=pre-holdout validation windows
next missing evidence: no-leak router training/evaluation rows
```

The `realized_vol_20` adapter family improved all 3 balanced rolling
cut-points, but average MAE improvement was `1.5158489425955908%`, below the 2%
Promotion Ready threshold. Per-series attribution shows `DEXUSEU` and `DGS10`
negative on average, and `cut5500` only improved 3 of 10 series. Promotion
remains blocked. Distribution diagnostics show mixed cut5500 regime shift, so
per-series normalization was tested before larger LoRA rank.

The normalized target experiment did not fix the blocker:

```text
normalized rolling average MAE improvement: 0.978786%
cut5500 normalized MAE improvement: -0.185%
cut5500 per-series MAE wins: 3/10
```

Recent2000 did improve the blocker, but not enough for promotion:

```text
recent2000 rolling average MAE improvement: 1.723918%
cut5500 recent2000 MAE improvement: 2.011%
cut5500 per-series MAE wins: 5/10
```

Recent3000 did not improve the tradeoff:

```text
recent3000 rolling average MAE improvement: 1.507674%
cut5500 recent3000 MAE improvement: 0.500%
cut5500 per-series MAE wins: 4/10
```

Recent1500 completed the fixed-window sweep:

```text
recent1500 rolling average MAE improvement: 0.068585%
cut4000 best fixed window: recent1500
cut5000 best fixed window: full-history
cut5500 best fixed window: recent2000
```

The next controlled experiment should stop forcing one fixed-window adapter and
test no-leak regime-aware adapter routing.

First routing checkpoint:

```text
global_history_best routed-cuts MAE improvement: -1.265%
per_series_history_best routed-cuts MAE improvement: -0.069%
leaky_current_cut_best_global average MAE improvement: 2.453%
```

Conclusion:

```text
Historical aggregate metrics are not enough for routing. The leaky oracle shows
adapter choice can matter, but the valid next step is per-window prediction
instrumentation, not publication or r=8.
```

Prediction archive checkpoint:

```text
evaluate_timesfm.py --predictions-output implemented
zero-shot smoke archive: 20 aligned windows
recent2000 LoRA smoke archive: 20 aligned windows
archive join key: window_id = series_id:start_index
```

Conclusion:

```text
At this checkpoint, the router data interface became ready and the next missing
artifact was a full multi-adapter archive export.
```

Full archive checkpoint:

```text
full archives exported: 15
prediction records exported: 7500
cuts aligned by window_id: 4000, 5000, 5500
families per cut: zero-shot, full, recent1500, recent2000, recent3000
```

Router-row checkpoint:

```text
router rows generated: 1500
runtime feature no-leak check: passed
best fixed family by mean MAE: recent2000
leaky per-window oracle MAE improvement: 5.952245%
```

Conclusion:

```text
The current adapter family has enough per-window selection headroom to justify
a no-leak router experiment, but not enough valid evidence for publication.
The next step is chronological router training/evaluation, not r=8 or release.
```

Prediction-router checkpoint:

```text
best learned routed-cuts MAE improvement: 1.198444%
fixed recent2000 routed-cuts MAE improvement: 1.507294%
validation-gated routed-cuts MAE improvement: 1.507294%
leaky per-window oracle routed-cuts MAE improvement: 4.719363%
```

Conclusion:

```text
The learned router has not beaten the fixed recent2000 fallback. The
validation-gated policy correctly failed closed and preserved the fallback.
Promotion remains blocked. The next useful experiment is more chronological
router supervision through an expanded rolling cut grid.
```

Expanded rolling grid checkpoint:

```text
expanded router rows generated: 4500
expanded cuts: 3500,3750,4000,4250,4500,4750,5000,5250,5500
fixed recent2000 routed-cuts MAE improvement: 1.987592%
validation-gated routed-cuts MAE improvement: 2.116398%
extra MAE delta over fallback: 0.0001260041
leaky per-window oracle all-cuts MAE improvement: 7.289511%
```

Conclusion:

```text
The expanded grid makes the router signal more credible, but the publishable
gain is still too small. The project should inspect per-series expanded router
attribution before Moirai integration, Hugging Face publication, or larger LoRA
rank.
```

Expanded router-attribution checkpoint:

```text
routed windows: 4000
validation-gated MAE delta over fixed recent2000: 0.0001260041
positive routed series: 5
negative routed series: 5
largest positive contributor: DFF, 148.703165% of net delta
largest negative contributors: DGS10 and SP500
```

Conclusion:

```text
The router has localized signal but not broad reliability. Publication remains
blocked. The next experiment should test a series-aware validation gate that
prevents learned routing on series with negative prior-validation behavior.
```

Series-aware router-guard checkpoint:

```text
best tested policy: series_guarded
best min_series_validation_lift: 0.0
routed MAE delta over fixed recent2000: 0.0002025053
routed improvement vs zero-shot: 2.194601%
validation-gated routed MAE delta over fallback: 0.0001260041
blocked at cut4250: DGS10, SP500
```

Conclusion:

```text
Series-aware gating improves the router and is the best valid policy so far,
but it is still not publishable. A one-cut series gate is too thin: it blocks
DGS10/SP500 at cut4250, but does not catch all series risk earlier. The next
experiment should test multi-cut series validation or a series-risk penalty.
```

Multi-cut series-guard checkpoint:

```text
aggregate multi-cut MAE delta over fallback: 0.0001260041
worst-cut multi-cut MAE delta over fallback: 0.0001749690
latest-cut series_guarded MAE delta over fallback: 0.0002025053
worst-cut blocked at cut4250: DFF, DGS10, SP500
```

Conclusion:

```text
Multi-cut validation is a useful negative result. Aggregating prior validation
cuts diluted local series failures and matched validation-gated performance.
Worst-cut validation reduced risk but over-blocked DFF, the main positive
contributor. The best policy remains latest-cut series_guarded with
min_series_validation_lift=0.0. The next experiment should test a
recency-weighted series-risk penalty, not a stricter hard gate.
```

Recency-weighted series-risk checkpoint:

```text
series_risk_penalized decay 0.05 MAE delta over fallback: 0.0002025053
series_risk_penalized decay 0.10 MAE delta over fallback: 0.0002025053
series_risk_penalized decay 0.25 MAE delta over fallback: 0.0001436530
series_risk_penalized decay 0.50 MAE delta over fallback: 0.0001260041
latest-cut series_guarded MAE delta over fallback: 0.0002025053
```

Conclusion:

```text
Recency-weighted series risk confirms that recent validation evidence must
dominate older cut evidence. With decay 0.1, the risk policy keeps DFF and blocks
DGS10/SP500 at cut4250, tying the latest-cut guard. It does not create new net
lift. Further hard-gate tuning is low leverage until the grid has more early
chronological supervision or richer no-leak runtime features.
```

Early rolling-grid checkpoint:

```text
early grid cuts: 3000,3250,3500,3750,4000,4250,4500,4750,5000,5250,5500
joined router rows: 5500
fixed recent2000 routed MAE: 0.0920232799
best chronological diagnostic routed MAE: 0.0919644635
validation-gated routed MAE: 0.0921934286
series-risk routed MAE: 0.0921345873
```

Conclusion:

```text
The early grid adds useful coverage but is a negative deployability result.
Leaky selection headroom remains large, and one chronological diagnostic barely
beats fixed recent2000, but all fail-closed learned routing policies underperform
the fallback. Further hard-gate or cut-density tuning is lower leverage than
adding richer no-leak runtime features for regime detection.
```

No-leak regime feature checkpoint:

```text
feature_set: context_prediction_regime_v2
joined router rows: 5500
fixed recent2000 routed MAE: 0.0920232799
best chronological diagnostic routed MAE: 0.0916329967
validation-gated routed MAE: 0.0917723992
validation-gated delta vs fallback: 0.0002508807
SMAPE validation-gated delta vs fallback: -0.0001982436
series-guarded routed MAE delta vs fallback: -0.0000320558
```

Conclusion:

```text
Richer no-leak runtime features are the first router change to make default
validation-gated MAE positive on the early grid. This confirms the feature seam
is higher leverage than more cut density. Promotion is still blocked because
SMAPE and series-aware guards remain negative, so the next step is feature
ablation followed by a risk policy that preserves MAE lift without series-level
regressions.
```

Feature ablation checkpoint:

```text
best feature preset: alignment-normalized
validation-gated routed MAE: 0.0917558798
validation-gated MAE delta vs fallback: 0.0002674001
validation-gated SMAPE delta vs fallback: 0.0001627004
series-guarded routed MAE delta vs fallback: 0.0000148190
best diagnostic routed MAE delta vs fallback: 0.0004631997
```

Conclusion:

```text
The useful signal comes from prediction-context alignment plus normalized
prediction disagreement, not from using every runtime feature. Standalone
normalized disagreement is harmful, and context_regime reduces the best
alignment-normalized result when added back. The current best feature seam is
alignment-normalized. Promotion remains blocked because series-aware lift is
positive but too small; tune series-risk policy around this feature surface
before training more LoRA adapters.
```

Policy-sweep checkpoint:

```text
configs tested: 27
best aggregate policy: validation_gated, min_validation_lift=0.01
best aggregate MAE delta vs fallback: 0.0002674001
best aggregate positive/negative routed series: 4/6
best risk-balanced aggregate policy: validation_gated, min_validation_lift=0.005
best risk-balanced aggregate MAE delta vs fallback: 0.0002611555
best risk-balanced aggregate positive/negative routed series: 7/3
best series_guarded MAE delta vs fallback: 0.0000363414
best 8/2 series split MAE delta vs fallback: 0.0000212628
```

Conclusion:

```text
Manual hard-gate and series-risk tuning has reached a stop signal. The sweep
can trade aggregate lift for series stability, but it does not create a
publishable policy frontier. The next useful research step is a supervised
selector objective or richer loss-aware router training, not more manual
threshold sweeps or additional raw context features.
```

Loss-aware selector checkpoint:

```text
candidate set: loss-aware
baseline candidate set validation-gated delta vs fallback: 0.0002674001
loss-aware candidate set validation-gated delta vs fallback: 0.0002366568
best diagnostic remains: knn_regret_no_series_k25
best diagnostic delta vs fallback: 0.0004631997
best regret-softmax: regret_softmax_raw_no_series
best regret-softmax delta vs fallback: 0.0002065049
loss-aware positive/negative routed series: 4/6
```

Conclusion:

```text
The regret objective is directionally useful because it beats ordinary softmax,
but the linear regret-softmax selector does not improve the frontier. KNN-regret
still captures local behavior better. Keep the loss-aware candidate set as an
opt-in diagnostic, preserve baseline reproducibility, and move next to
calibrated KNN-regret gating or a nonlinear/local selector with explicit
per-series downside control.
```

Calibrated KNN-regret checkpoint:

```text
candidate set: knn-regret
old strict gate mvl0.01 MAE delta vs fallback: -0.0000393438
best aggregate mvl0.0 MAE delta vs fallback: 0.0002705342
best aggregate mvl0.0 SMAPE delta vs fallback: 0.0004127764
best risk-balanced mvl0.005 MAE delta vs fallback: 0.0002687244
best risk-balanced mvl0.005 SMAPE delta vs fallback: 0.0005225268
best risk-balanced positive/negative routed series: 7/3
extra MAE delta over baseline mvl0.01: 0.0000013244
```

Conclusion:

```text
KNN-regret needs lighter calibration than the mixed baseline candidate set. The
0.005 gate is the current best risk-balanced checkpoint because it improves MAE,
SMAPE, and series coverage together. The gain over baseline is still too small
for promotion, so the next step is per-series downside control on top of the
KNN-regret surface.
```
