# Market Macro Realized Vol 20 Z-Score Second Target

Date: 2026-07-02

## Goal

Validate the existing `realized_vol_20_zscore` LoRA adapters as a second
financial target using prediction archives and a no-leak router evaluation.

This is not a new weight-training run. The adapters already existed. This run
promotes them from summary-metric artifacts into aligned per-window prediction
archives so they can be evaluated at the serving-policy seam.

## Script Change

`rolling_grid.py`, `export_prediction_archives.py`, and
`join_prediction_archives.py` now accept target-specific naming:

```text
target_slug: controls report/prediction archive names
adapter_prefix: controls adapter directory prefix
full_balanced_adapter: keeps the original realized_vol_20 cut5000 balanced adapter default
csv-template: lets zscore use one normalized CSV per cut
field-template: lets zscore use one normalized field per cut
```

The original realized-volatility defaults are unchanged.

## Archive Export

Command:

```bash
uv run python scripts/export_prediction_archives.py \
  --target-slug market-macro-realized-vol-20-zscore-h20-r4 \
  --adapter-prefix market-macro-realized-vol-20-zscore-h20-r4-step200 \
  --no-full-balanced-adapter \
  --csv-template 'data/market/normalized-realized-vol-20-zscore-train{cut}.csv' \
  --field-template 'realized_vol_20_zscore_train{cut}' \
  --grid base \
  --family zero-shot \
  --family full
```

Produced six ignored local JSON artifacts:

```text
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-zero-shot-holdout500-skip4000.json
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-full-holdout500-skip4000.json
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-zero-shot-holdout500-skip5000.json
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-full-holdout500-skip5000.json
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-zero-shot-holdout500-skip5500.json
archive-export-timesfm-market-macro-realized-vol-20-zscore-h20-r4-full-holdout500-skip5500.json
```

Each archive contains 500 windows across 10 public market/macro series.

## Router Rows

Command:

```bash
uv run python scripts/join_prediction_archives.py \
  --target-slug market-macro-realized-vol-20-zscore-h20-r4 \
  --adapter-prefix market-macro-realized-vol-20-zscore-h20-r4-step200 \
  --no-full-balanced-adapter \
  --grid base \
  --family zero-shot \
  --family full \
  --output reports/router-rows-market-macro-realized-vol-20-zscore-h20-r4.json
```

Result:

| Metric | Value |
|---|---:|
| Rows | 1500 |
| Cuts | 4000, 5000, 5500 |
| Families | zero-shot, full |
| Full wins | 814 |
| Zero-shot wins | 686 |
| Fixed full MAE | 0.4862193132 |
| Fixed zero-shot MAE | 0.4908455409 |
| Leaky oracle MAE | 0.4801193792 |
| Leaky oracle MAE improvement vs zero-shot | 2.1852417499% |

## No-Leak Router

Command:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-h20-r4.json \
  --metric mae \
  --cold-start-family full \
  --fallback-family full \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Rows | 1500 |
| Best chronological diagnostic | `knn_regret_no_series_k100` |
| Best diagnostic routed MAE | 0.4849968548 |
| Fixed full fallback routed MAE | 0.4836954085 |
| Validation-gated routed MAE | 0.4836954085 |
| Delta vs fallback | 0 |

Verdict:

```text
No learned prediction-level router is promotion-ready. The validation-gated
policy kept the fallback because learned routing did not clear the prior-cut
validation lift requirement.
```

## Interpretation

Fact: the zscore full LoRA adapter has a small MAE advantage over zero-shot on
the base 3-cut archive.

Fact: a leaky per-window oracle shows selection headroom, but that headroom is
not available at inference time.

Fact: the no-leak learned router did not beat fixed `full` fallback under
chronological validation.

Inference: zscore is useful as a second target validation surface, but not yet
as a promoted router policy.

Recommendation: keep `realized_vol_20_zscore` as a secondary adapter target and
extend it only after adding more cuts or recent-window zscore adapters.
