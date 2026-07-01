# Market Macro Realized Vol 20 Z-Score Recent2000

Date: 2026-07-02

## Goal

Add a recent-window adapter family to the `realized_vol_20_zscore` second target
and test whether the wider candidate pool improves no-leak routing.

Previous zscore candidate pool:

```text
zero-shot
full
```

This run adds:

```text
recent2000
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
  --family recent2000
```

Produced ignored local adapters:

```text
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train4000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train5000
adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train5500
```

Each adapter used 2000 training windows:

| Cut | Max windows | Skip windows |
|---|---:|---:|
| 4000 | 2000 | 2000 |
| 5000 | 2000 | 3000 |
| 5500 | 2000 | 3500 |

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
  --family recent2000
```

Holdout results:

| Cut | MAE | SMAPE |
|---|---:|---:|
| 4000 | 0.4934044260 | 0.7650339744 |
| 5000 | 0.4470375563 | 1.0833945210 |
| 5500 | 0.5202477033 | 0.8639488587 |

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
  --family recent2000 \
  --output reports/router-rows-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json
```

Result:

| Metric | Value |
|---|---:|
| Rows | 1500 |
| Full wins | 495 |
| Recent2000 wins | 474 |
| Zero-shot wins | 531 |
| Fixed zero-shot MAE | 0.4908455409 |
| Fixed full MAE | 0.4862193132 |
| Fixed recent2000 MAE | 0.4868965619 |
| Leaky oracle MAE | 0.4738384752 |
| Leaky oracle MAE improvement vs zero-shot | 3.4648507971% |

## MAE Router

Command:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json \
  --metric mae \
  --cold-start-family full \
  --fallback-family full \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Best chronological diagnostic | `knn_regret_no_series_k25` |
| Best diagnostic routed MAE | 0.4838786046 |
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

Command:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-recent2000-smape-h20-r4.json \
  --metric smape \
  --cold-start-family zero-shot \
  --fallback-family zero-shot \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Result:

| Metric | Value |
|---|---:|
| Best chronological diagnostic | `knn_regret_no_series_k100` |
| Best diagnostic routed SMAPE | 0.9679270536 |
| Fixed zero-shot fallback routed SMAPE | 0.9734419740 |
| Validation-gated routed SMAPE | 0.9728359861 |
| Delta vs fallback | 0.0006059880 |

## Interpretation

Fact: `recent2000` increased the leaky oracle headroom from the prior zscore
two-family run.

Fact: fixed `full` remains the best fixed MAE family.

Fact: no-leak MAE routing still fails closed to fixed `full`.

Fact: no-leak SMAPE routing has a small positive validation-gated delta over
zero-shot fallback.

Inference: recent-window zscore adapters add useful diversity, but the MAE
serving policy is still not promotable.

Recommendation: do not publish a zscore router yet. The next useful step is a
larger zscore candidate pool or more cuts, then a two-metric promotion gate.
