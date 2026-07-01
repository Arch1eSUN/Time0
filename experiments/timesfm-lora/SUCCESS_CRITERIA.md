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
method=prediction-level router instrumentation
candidate_adapters=full-history,recent1500,recent2000,recent3000
selection_data=pre-holdout validation windows
new_artifact=per-window prediction archive
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
```
