# TimesFM LoRA Success Criteria

Date: 2026-07-01

Purpose: define when a TimesFM LoRA run should stop, when it counts as useful,
and when an adapter is strong enough to become a Moirai/Time0 candidate.

## Problem Framing

Training completion is not success.

A LoRA run can finish, save an adapter, and still make the model worse. For
Time0, success means the adapter improves out-of-sample forecasting behavior on
the target domain, compared against both simple baselines and TimesFM zero-shot.

## Epistemic Split

Fact: current reports use a chronological holdout split with
`skip_windows=5000`, `max_windows=500`, and balanced coverage across 10 public
market/macro series.

Fact: the `level` LoRA adapters did not beat TimesFM zero-shot on holdout.

Fact: the `log_change` LoRA adapter improved MAE slightly but regressed SMAPE.

Assumption: Time0 wants a domain-specialized adapter for market/macro risk
forecasting, not a generic "training completed" artifact.

Inference: an adapter should not be promoted unless it beats TimesFM zero-shot
on future windows, not only the training split.

Recommendation: treat every adapter as experimental until it passes the
Candidate Success gate below. Treat Moirai integration as blocked until the
Promotion Ready gate is met.

## Success Levels

| Level | Meaning | Required Evidence |
|---|---|---|
| Run Valid | The training/evaluation job is technically valid | script exits 0, adapter/report exists, no NaN/inf metrics, expected target field, expected window counts |
| Experiment Useful | The run teaches us something | same holdout split as baseline, naive + TimesFM zero-shot comparison, one main lever changed, run note written |
| Candidate Success | The adapter looks better than zero-shot | primary metric improves by at least 1% vs zero-shot on holdout, secondary metric does not regress beyond the allowed threshold, naive baselines are beaten |
| Promotion Ready | The adapter is strong enough to wire behind a product seam | wins across at least 3 rolling holdout cut-points, average primary improvement at least 2%, per-series behavior is not dominated by one series, repeat run is stable |

Lower metric values are better for MAE and SMAPE.

Relative improvement:

```text
improvement = (zero_shot_metric - lora_metric) / zero_shot_metric
```

Example:

```text
zero-shot MAE = 0.01852
LoRA MAE      = 0.01834
improvement   = (0.01852 - 0.01834) / 0.01852
```

## Target-Specific Gates

| Target | Primary Metric | Secondary Metric | Gate |
|---|---|---|---|
| `level` | MAE | SMAPE | must improve both MAE and SMAPE vs zero-shot |
| `log_change` | MAE | SMAPE watch-only unless denominator-filtered | must improve MAE; raw SMAPE cannot be the only blocker because near-zero targets make SMAPE unstable |
| `realized_vol_20` | MAE | SMAPE | must improve MAE and avoid material SMAPE regression |

`log_change` needs special handling because the true value is often close to
zero. When the denominator is tiny, SMAPE can explode even when the absolute
forecast error is small. For this target, MAE is the hard gate; SMAPE is a
warning signal until we add denominator-filtered SMAPE or another return-aware
metric.

## Stop Conditions

Stop a training direction when any of these happens:

| Stop Type | Condition | Action |
|---|---|---|
| Technical stop | NaN/inf metrics, missing report, missing series, wrong target field | discard run and fix tooling/data |
| No-gain stop | 3 consecutive evaluation checkpoints fail to improve the primary holdout metric | stop this setting |
| Overfit stop | training loss improves while holdout metric worsens for 2 consecutive checkpoints | stop or reduce capacity/steps |
| Zero-shot loss stop | adapter is worse than TimesFM zero-shot by more than 1% on primary metric after warmup | stop this adapter |
| Target stop | target consistently gives unstable or non-actionable evaluation | change target instead of increasing LoRA size |
| Product stop | adapter passes metrics but lacks reproducibility, provenance, or seam-safe integration path | keep as research artifact only |

## Current Adapter Verdicts

| Adapter | Target | Verdict | Reason |
|---|---|---|---|
| `market-macro-level-h20-r4-step200-balanced` | `level` | Failed Candidate Success | worse than TimesFM zero-shot on MAE and SMAPE |
| `market-macro-level-h20-r4-step1000-balanced` | `level` | Failed Candidate Success | worse than step200; likely overfit or over-trained |
| `market-macro-log-change-h20-r4-step200-balanced` | `log_change` | Partial signal, not success | MAE improves slightly, SMAPE regresses |
| `market-macro-realized-vol-20-h20-r4-step200-*` | `realized_vol_20` | Rolling positive, not Promotion Ready | improves all 3 balanced cut-points, but average MAE gain is 1.52%; per-series average is negative for DEXUSEU and DGS10 |
| `market-macro-realized-vol-20-zscore-h20-r4-step200-*` | `realized_vol_20_zscore_train*` | Diagnostic failed to promote | normalized average MAE gain is 0.98%; cut5500 regresses and only improves 3 of 10 series |
| `market-macro-realized-vol-20-h20-r4-step200-recent2000-*` | `realized_vol_20` | Direction useful, not Promotion Ready | average MAE gain is 1.72%; cut5500 improves to 2.01%, but cut4000/cut5000 gains shrink |
| `market-macro-realized-vol-20-h20-r4-step200-recent3000-*` | `realized_vol_20` | Negative window result | average MAE gain is 1.51%; cut4000 improves to 3.39%, but cut5500 drops to 0.50% |
| `market-macro-realized-vol-20-h20-r4-step200-recent1500-*` | `realized_vol_20` | Fixed-window sweep stop | average MAE gain is 0.07%; cut4000 is best so far, but cut5000 and cut5500 regress vs zero-shot |
| `history-best adapter router` | `realized_vol_20` | No-leak router failed | global routed cuts regress by 1.27%; per-series routed cuts regress by 0.07%; leaky oracle reaches 2.45% but is invalid |
| `prediction archive instrumentation` | `realized_vol_20` | Data interface ready | zero-shot and LoRA smoke archives align by `window_id`; each record stores pre-forecast features, actuals, predictions, MAE, and SMAPE |
| `full prediction archive export` | `realized_vol_20` | Router source data ready | 15 local archives, 7500 prediction records, and all 3 cuts align by `window_id` across 5 families |
| `prediction archive joiner` | `realized_vol_20` | Router training data ready | 1500 no-leak checked rows; leaky per-window oracle reaches 5.95% MAE improvement but remains invalid for deployment |
| `prediction-level router` | `realized_vol_20` | Learned router not promotion-ready | best learned routed-cuts MAE gain is 1.20%, below fixed recent2000 at 1.51%; validation-gated policy correctly stays on fallback |
| `expanded rolling prediction router` | `realized_vol_20` | Promising, not Promotion Ready | expanded grid has 4500 rows across 9 cuts; validation-gated routed MAE gain is 2.12% vs zero-shot, but extra lift over fixed recent2000 is only 0.000126 MAE |
| `expanded router attribution` | `realized_vol_20` | Promotion still blocked | DFF contributes 148.70% of net router delta, while DGS10 and SP500 regress vs fallback; gain is concentrated rather than broad |
| `series-aware router guard` | `realized_vol_20` | Best router policy so far, not Promotion Ready | per-series guard improves routed MAE delta over fixed recent2000 to 0.0002025053, but still leaves negative series and uses only one prior validation cut |
| `multi-cut series guard` | `realized_vol_20` | Useful negative result | aggregate multi-cut does not improve over validation-gated; worst-cut reaches 0.0001749690 MAE delta over fallback but underperforms latest-cut series guard |
| `recency-weighted series risk` | `realized_vol_20` | Diagnostic tie, not Promotion Ready | decay 0.1 ties the latest-cut series guard at 0.0002025053 MAE delta over fallback; higher decay degrades as older evidence hides recent failures |
| `early rolling grid` | `realized_vol_20` | Useful negative result | adding cuts 3000/3250 creates 5500 rows and 6.99% leaky oracle headroom, but validation-gated policies underperform fixed recent2000 |
| `no-leak regime features` | `realized_vol_20` | First positive MAE router milestone, not Promotion Ready | validation-gated routed MAE improves fixed recent2000 by 0.0002508807 on early grid, but SMAPE and series-aware guards still regress |
| `feature ablation alignment-normalized` | `realized_vol_20` | Best router feature surface so far, not Promotion Ready | alignment-normalized improves fixed recent2000 on MAE, SMAPE, and series-guarded MAE, but series-aware lift is only 0.0000148190 |

Recommendation: stop increasing steps on `level`. Treat `realized_vol_20` as
the first clean target signal, but do not promote it until distribution shift
and weak-series behavior are handled.

## Promotion Requirements For Moirai

An adapter can be considered for Moirai only after:

1. It passes Candidate Success.
2. It passes at least 3 chronological holdout cut-points.
3. It has a run note with data source, field, context length, horizon length,
   LoRA rank, alpha, step count, and report paths.
4. It has no direct product dependency on the training script.
5. It is exposed only through a future `ForecastRequest -> ForecastResult`
   adapter seam.

The adapter file itself is not a product interface. The product interface is
the forecasting seam that hides whether the backend uses zero-shot TimesFM,
LoRA TimesFM, Moirai, or another model.

## Next Evaluation Direction

Next validation:

```text
field=realized_vol_20
method=prediction archive joiner
candidate_adapters=full-history,recent1500,recent2000,recent3000
selection_data=pre-holdout validation windows
new_artifact=joined router training/evaluation rows
```

Reason:

```text
The realized_vol_20 adapter family improved all 3 balanced rolling cut-points,
but the average gain stayed below the 2% Promotion Ready threshold.
Per-series evidence shows that cut5500 only improved 3 of 10 series.
Distribution diagnostics show mixed regime shift at cut5500.
Per-series z-score normalization did not fix cut5500 and lowered average MAE
improvement to 0.98%.
Recent2000 fine-tuning improved cut5500 to 2.01% MAE gain and raised average
MAE improvement to 1.72%, but still missed the 2% Promotion Ready threshold.
Recent3000 fine-tuning did not recover the tradeoff: average MAE improvement
fell to 1.51% and cut5500 dropped to 0.50%.
Recent1500 completed the fixed-window sweep: cut4000 became best so far, but
cut5000 and cut5500 regressed vs zero-shot.
The first no-leak historical routing baseline failed: aggregate historical
performance did not select future adapters reliably. The leaky current-cut
oracle reached 2.45% average MAE gain, which shows adapter selection has upside
but cannot count as evidence. The next decision should add prediction-level
archives and train/evaluate a valid router before changing rank or publishing.
Prediction archive instrumentation is now available through
`evaluate_timesfm.py --predictions-output`; the next step is full archive export
and a joiner/router, not more fixed-window adapter training.
Full prediction archive export is now complete: 15 archives and 7500 records
are available locally. The joiner now creates 1500 no-leak checked router rows.
The first no-leak prediction-level router did not beat fixed `recent2000`, so
the next step was an expanded rolling cut grid, not publication or larger LoRA
rank. The expanded grid improved the validation-gated policy to 2.116398%
routed-cut MAE gain vs zero-shot, but the extra lift over fixed `recent2000`
is only 0.000126 MAE. Promotion remains blocked until per-series behavior and
future-cut stability prove the router gain is not noise. Per-series attribution
shows the current lift is concentrated: `DFF` contributes more than the total
net gain, while `DGS10` and `SP500` regress vs fallback. The next policy test
should add a series-aware validation gate. The first series-aware guard improves
the routed MAE delta over fallback from 0.0001260041 to 0.0002025053 and blocks
`DGS10`/`SP500` at cut4250, but it still misses some series risk at cut4000.
Promotion remains blocked; the next router policy should use multi-cut series
validation or an explicit series-risk penalty. Multi-cut validation was tested
next: aggregate multi-cut diluted local failures, while worst-cut over-blocked
DFF. The best policy remains latest-cut `series_guarded`; the next router policy
should use a recency-weighted series-risk penalty. That penalty was tested and
tied, but did not beat, latest-cut `series_guarded`. The next useful step is
more early chronological supervision or richer no-leak runtime features. Early
chronological supervision was tested next with cuts 3000/3250. It increased
router rows to 5500 but fail-closed learned routing still underperformed fixed
`recent2000`, so the next useful step is richer no-leak runtime features. Those
features were added next through context-regime, normalized disagreement, and
prediction-context alignment features. They produced the first positive default
MAE validation-gated router on the early grid, but SMAPE and series-aware guards
remain negative. The next useful step is feature ablation plus a risk policy that
preserves MAE lift without series-level regressions. Feature ablation showed
`alignment-normalized` is the best surface: it improves MAE, SMAPE, and
series-guarded MAE over fixed `recent2000`, but the series-aware lift remains
too small for promotion. The next useful step is series-risk tuning on
`alignment-normalized`, not more raw context features.
```
