# Market Macro Realized Vol 20 Z-Score All Recent Families

Date: 2026-07-02

## Goal

Complete the base zscore recent-window family sweep by adding `recent1500` and
`recent3000`, then test whether the full candidate pool improves no-leak
routing.

Previous zscore candidate pool:

```text
zero-shot
full
recent2000
```

This run adds:

```text
recent1500
recent3000
```

## Training

Command:

```bash
uv run python scripts/train_rolling_grid_adapters.py \
  --adapter-prefix market-macro-realized-vol-20-zscore-h20-r4-step200 \
  --no-full-balanced-adapter \
  --csv-template 'data/market/normalized-realized-vol-20-zscore-train{cut}.csv' \
  --field-template 'realized_vol_20_zscore_train{cut}' \
  --grid base \
  --family recent1500 \
  --family recent3000
```

Produced ignored local adapters:

```text
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent1500-train4000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent3000-train4000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent1500-train5000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent3000-train5000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent1500-train5500
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent3000-train5500
```

## Prediction Archives

Command:

```bash
uv run python scripts/export_prediction_archives.py \
  --target-slug market-macro-realized-vol-20-zscore-h20-r4 \
  --adapter-prefix market-macro-realized-vol-20-zscore-h20-r4-step200 \
  --no-full-balanced-adapter \
  --csv-template 'data/market/normalized-realized-vol-20-zscore-train{cut}.csv' \
  --field-template 'realized_vol_20_zscore_train{cut}' \
  --grid base \
  --family recent1500 \
  --family recent3000
```

Holdout results:

| Family | Cut | MAE | SMAPE |
|---|---:|---:|---:|
| recent1500 | 4000 | 0.4933889390 | 0.7657172920 |
| recent3000 | 4000 | 0.4912908370 | 0.7692536909 |
| recent1500 | 5000 | 0.4614506425 | 1.0845968209 |
| recent3000 | 5000 | 0.4491097150 | 1.0883109443 |
| recent1500 | 5500 | 0.5239718838 | 0.8586003483 |
| recent3000 | 5500 | 0.5212301058 | 0.8565083904 |

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
  --family recent1500 \
  --family recent2000 \
  --family recent3000 \
  --output reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json
```

Result:

| Metric | Value |
|---|---:|
| Rows | 1500 |
| zero-shot wins | 379 |
| full wins | 328 |
| recent1500 wins | 419 |
| recent2000 wins | 197 |
| recent3000 wins | 177 |
| Fixed zero-shot MAE | 0.4908455409 |
| Fixed full MAE | 0.4862193132 |
| Fixed recent1500 MAE | 0.4929371551 |
| Fixed recent2000 MAE | 0.4868965619 |
| Fixed recent3000 MAE | 0.4872102193 |
| Leaky oracle MAE | 0.4665912068 |
| Leaky oracle MAE improvement vs zero-shot | 4.9413373547% |
| Leaky oracle SMAPE | 0.8718166645 |
| Leaky oracle SMAPE improvement vs zero-shot | 3.5249489648% |

## MAE Router

Command:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-all-recent-mae-h20-r4.json \
  --metric mae \
  --cold-start-family full \
  --fallback-family full \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Best chronological diagnostic | `knn_regret_no_series_k100` |
| Best diagnostic routed MAE | 0.4848657808 |
| Fixed full fallback routed MAE | 0.4836954085 |
| Validation-gated routed MAE | 0.4836954085 |
| Delta vs fallback | 0 |

Verdict:

```text
No learned prediction-level router is promotion-ready. The validation-gated
policy kept the fallback because learned routing did not clear the prior-cut
validation lift requirement.
```

## SMAPE Router

Best fixed SMAPE fallback:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-all-recent-smape-h20-r4.json \
  --metric smape \
  --cold-start-family recent1500 \
  --fallback-family recent1500 \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Best chronological diagnostic | `knn_regret_no_series_k50` |
| Best diagnostic routed SMAPE | 0.9647456805 |
| Fixed recent1500 fallback routed SMAPE | 0.9715985846 |
| Validation-gated routed SMAPE | 0.9713667758 |
| Delta vs fallback | 0.0002318088 |

Zero-shot fallback comparison:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-all-recent-smape-zero-fallback-h20-r4.json \
  --metric smape \
  --cold-start-family zero-shot \
  --fallback-family zero-shot \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Fixed zero-shot fallback routed SMAPE | 0.9734419740 |
| Validation-gated routed SMAPE | 0.9751426728 |
| Delta vs fallback | -0.0017006988 |

## Interpretation

Fact: adding `recent1500` and `recent3000` increased leaky oracle headroom.

Fact: fixed `full` remains the best fixed MAE family.

Fact: MAE no-leak routing still fails closed to fixed `full`.

Fact: SMAPE routing improves slightly over fixed `recent1500`, but underperforms
fixed `zero-shot` when zero-shot is used as the fallback.

Inference: the larger zscore candidate pool increases theoretical upside but
also increases routing instability.

Recommendation: do not promote the all-recent zscore router. Keep the local
adapters as diagnostic artifacts and next test a stricter SMAPE guard or more
validation cuts before widening the pool further.
