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

Recommendation: stop increasing steps on `level`. For `log_change`, run at most
one repeat or one small capacity check, then prioritize `realized_vol_20`.

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

Next target:

```text
field=realized_vol_20
```

Reason:

```text
It is closer to market/macro risk behavior than raw level.
It avoids some near-zero SMAPE instability from log_change.
It is more useful as a downstream risk feature for Moirai-style temporal simulation.
```
