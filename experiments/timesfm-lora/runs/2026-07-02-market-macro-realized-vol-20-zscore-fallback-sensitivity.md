# Market Macro Realized Vol 20 Z-Score Fallback Sensitivity

Date: 2026-07-02

## Goal

Turn the previous zscore observation into a reusable promotion guard:

```text
A router win is not robust if it wins against one fallback but loses against
another reasonable fallback.
```

This run adds a fallback-sensitivity evaluator and applies it to zscore router
rows.

## Script

Added:

```text
scripts/evaluate_router_fallback_sensitivity.py
```

The script reuses `evaluate_prediction_router.build_report()` and runs the
same no-leak router evaluation across multiple fallback families.

Verdict classes:

| Verdict | Meaning |
|---|---|
| `robust_positive` | positive against every checked fallback |
| `partial_positive` | positive against at least one fallback and negative against none |
| `fallback_sensitive` | positive against some fallbacks and negative against others |
| `fail_closed_all` | zero delta against every fallback |
| `not_promotable` | no positive deltas and at least one negative delta |

## Commands

All-recent SMAPE:

```bash
uv run python scripts/evaluate_router_fallback_sensitivity.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json \
  --output reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-all-recent-smape-h20-r4.json \
  --metric smape \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

All-recent MAE:

```bash
uv run python scripts/evaluate_router_fallback_sensitivity.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json \
  --output reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-all-recent-mae-h20-r4.json \
  --metric mae \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Recent2000 SMAPE comparison:

```bash
uv run python scripts/evaluate_router_fallback_sensitivity.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json \
  --output reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-recent2000-smape-h20-r4.json \
  --metric smape \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

Two-family SMAPE comparison:

```bash
uv run python scripts/evaluate_router_fallback_sensitivity.py \
  --input reports/router-rows-market-macro-realized-vol-20-zscore-h20-r4.json \
  --output reports/router-fallback-sensitivity-market-macro-realized-vol-20-zscore-two-family-smape-h20-r4.json \
  --metric smape \
  --candidate-set knn-regret \
  --min-validation-lift 0
```

## Results

| Surface | Metric | Verdict | Positive fallbacks | Negative fallbacks | Zero fallbacks | Min delta | Max delta |
|---|---|---|---:|---:|---:|---:|---:|
| all-recent | SMAPE | `fallback_sensitive` | 2 | 3 | 0 | -0.0017006988 | 0.0029060640 |
| all-recent | MAE | `fallback_sensitive` | 1 | 1 | 3 | -0.0004458839 | 0.0014738528 |
| recent2000 | SMAPE | `partial_positive` | 2 | 0 | 1 | 0 | 0.0017566489 |
| two-family | SMAPE | `not_promotable` | 0 | 1 | 1 | -0.0004501663 | 0 |

## Interpretation

Fact: the all-recent zscore pool is fallback-sensitive on both MAE and SMAPE.

Fact: the recent2000-only zscore pool is partial-positive on SMAPE, not robust
positive.

Fact: the two-family zscore pool is not promotable on SMAPE.

Inference: expanding the zscore candidate pool raised oracle headroom but also
introduced fallback sensitivity.

Recommendation: do not promote any zscore router until the sensitivity verdict
is at least `partial_positive` with no negative fallback, and preferably
`robust_positive` across all reasonable fallback families.
