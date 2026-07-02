# Market Macro Finance Readiness Gate

Date: 2026-07-02

## Goal

Answer when the finance LoRA direction can stop and what final effect it should deliver.

## Current Verdict

Verdict: `continue_research`

Recommendation: do not publish yet; continue only on router downside control or a clearly scoped new target/rank test.

## Intended Final Effect

specialize TimesFM 2.5 for 20-step market/macro realized-volatility forecasting as a risk input, not as financial advice or a trading signal

## Gate Results

| Gate | Required | Actual | Pass |
|---|---:|---:|---|
| `fixed_average_mae_lift` | 2.000% | 1.724% | False |
| `fixed_positive_cut_count` | 3 | 3 | True |
| `router_extra_lift_vs_fallback` | 0.200% | 0.319% | True |
| `router_negative_series` | 0 | 2 | False |
| `zscore_fallback_sensitivity` | no fallback_sensitive verdicts in checked zscore reports | partial_positive, fallback_sensitive, fallback_sensitive | False |

## Fixed Adapter Evidence

Family: `recent2000`

| Cut | MAE lift vs zero-shot | SMAPE lift vs zero-shot | Series MAE wins |
|---:|---:|---:|---:|
| 4000 | 2.482% | 0.881% | 6/10 |
| 5000 | 0.679% | 1.377% | 7/10 |
| 5500 | 2.011% | 0.335% | 5/10 |

Average MAE lift: 1.724%

## Router Evidence

Rows: 5500

Cuts: [3000, 3250, 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500]

Fallback family: `recent2000`

| Router checkpoint | Value |
|---|---:|
| extra lift vs fallback | 0.319% |
| delta vs fallback | 0.0002931205 |
| positive / negative series | 8 / 2 |
| vetoed windows | 1378 |

## Sensitivity Evidence

| Report | Metric | Verdict | Negative fallbacks |
|---|---|---|---|
| `reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-recent2000-smape-h20-r4.json` | smape | `partial_positive` | none |
| `reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-all-recent-smape-h20-r4.json` | smape | `fallback_sensitive` | zero-shot, full, recent3000 |
| `reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-all-recent-mae-h20-r4.json` | mae | `fallback_sensitive` | zero-shot |

## Interpretation

Fact: the current fixed `recent2000` adapter improves all three checked MAE cut-points but averages below the 2% release threshold.

Fact: the current best router adds a small lift over fixed `recent2000` but still has negative routed series.

Fact: the zscore all-recent branch remains fallback-sensitive and cannot be used as release evidence.

Inference: the finance direction has a real signal, but it has not reached a clean stopping point.

Recommendation: keep the finance line open, but only for targeted downside control or one scoped rank/target comparison. Do not keep training without a gate-moving hypothesis.
