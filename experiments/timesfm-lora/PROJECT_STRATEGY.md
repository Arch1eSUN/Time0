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

Diagnose the first rolling validation result with per-series metrics:

```text
field=realized_vol_20
lora_r=4
lora_alpha=8
max_steps=200
balanced holdout cut-points: skip_windows=4000, 5000, 5500
next missing evidence: per-series metrics
```

The `realized_vol_20` adapter family improved all 3 balanced rolling
cut-points, but average MAE improvement was `1.5158489425955908%`, below the 2%
Promotion Ready threshold. Promotion remains blocked until per-series evidence
and stronger rolling improvement are available.
