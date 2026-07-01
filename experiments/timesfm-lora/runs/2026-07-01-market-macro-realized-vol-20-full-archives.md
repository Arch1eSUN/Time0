# 2026-07-01 Market Macro Realized Vol 20 Full Prediction Archives

## Goal

Export full prediction archives for the router candidate set:

```text
cuts=4000,5000,5500
families=zero-shot,full,recent1500,recent2000,recent3000
windows_per_run=500
```

This run creates the local evidence needed for the next step:

```text
prediction archive joiner -> no-leak router training rows
```

## Implementation

Added:

```text
scripts/export_prediction_archives.py
```

Purpose:

```text
Run evaluate_timesfm.py repeatedly with --predictions-output for the fixed
candidate matrix.
```

Default matrix:

| Cut | Families |
|---:|---|
| 4000 | `zero-shot`, `full`, `recent1500`, `recent2000`, `recent3000` |
| 5000 | `zero-shot`, `full`, `recent1500`, `recent2000`, `recent3000` |
| 5500 | `zero-shot`, `full`, `recent1500`, `recent2000`, `recent3000` |

The script skips jobs when both the aggregate report and prediction archive
already exist. Use `--overwrite` to regenerate.

## Command

```bash
uv run python scripts/export_prediction_archives.py
```

Dry-run example:

```bash
uv run python scripts/export_prediction_archives.py \
  --dry-run \
  --cut 4000 \
  --family zero-shot \
  --family recent2000
```

## Local Outputs

Aggregate reports:

```text
reports/archive-export-timesfm-market-macro-realized-vol-20-h20-r4-{family}-holdout500-skip{cut}.json
```

Prediction archives:

```text
reports/predictions-timesfm-market-macro-realized-vol-20-h20-r4-{family}-holdout500-skip{cut}.json
```

These files are local generated artifacts and remain ignored by Git.

## Validation

Validation checked:

```text
15 aggregate reports exist
15 prediction archives exist
each archive has 500 records
each record has horizon_len=20 actual values and 20 predicted values
each cut has identical window_id order across all 5 families
archive-export MAE/SMAPE match the previous official aggregate reports
feature keys match the router feature contract
```

Observed:

```text
validated_reports 15
validated_prediction_records 7500
cut_aligned 4000 families 5 windows_per_family 500
cut_aligned 5000 families 5 windows_per_family 500
cut_aligned 5500 families 5 windows_per_family 500
feature_keys past_last,past_max,past_mean,past_min,past_std,past_trend
```

## Interpretation

Fact: full prediction archives now exist locally for all 15 candidate
family/cut combinations.

Fact: every archive has 500 aligned forecast windows.

Fact: metrics from the newly exported aggregate reports match the prior
official reports, so archive export did not change model behavior.

Fact: each cut can now be joined across `zero-shot`, `full`, `recent1500`,
`recent2000`, and `recent3000` by `window_id`.

Inference: the project now has enough local evidence to build a prediction
archive joiner.

Recommendation: next build a joiner that creates one row per `cut/window_id`
with:

```text
pre-forecast features
all family predictions
adapter disagreement features
future-error labels
best valid family label
```

## Next Experiment Direction

Next controlled step:

```text
method=prediction archive joiner
input=15 aligned prediction archives
output=router training/evaluation rows
label=best family by future MAE
guardrail=router feature columns cannot include actual future values
```

After the joiner:

```text
method=no-leak router evaluation
train=prior cuts only
evaluate=current cut
compare=fixed recent2000 and leaky oracle upper bound
```
