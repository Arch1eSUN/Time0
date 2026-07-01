# 2026-07-01 Market Macro Realized Vol 20 Router Rows

## Goal

Build the first prediction-level dataset for a future no-leak adapter router.

Input:

```text
15 aligned prediction archives
3 cuts: 4000,5000,5500
5 families: zero-shot,full,recent1500,recent2000,recent3000
500 windows per cut/family
```

Output:

```text
one row per cut/window_id
runtime_features: pre-forecast context + prediction-derived summaries
label: best family by future MAE
```

## Implementation

Added:

```text
scripts/join_prediction_archives.py
```

Purpose:

```text
Join aligned prediction archives into supervised router rows while enforcing
that future actuals and error metrics stay out of runtime_features.
```

The script validates:

```text
archive exists for every selected cut/family
archive windows count matches record count
window_id order matches across families
actual arrays match across families for the same window
field and horizon_len are stable
runtime_features do not contain actual/mae/smape/best_family/family_errors/label
```

## Command

```bash
uv run python -m py_compile \
  scripts/join_prediction_archives.py \
  scripts/export_prediction_archives.py \
  scripts/evaluate_timesfm.py

uv run python scripts/join_prediction_archives.py \
  --output reports/router-rows-market-macro-realized-vol-20-h20-r4.json
```

## Local Output

```text
reports/router-rows-market-macro-realized-vol-20-h20-r4.json
```

This file is a generated local artifact and remains ignored by Git.

## Observed Summary

```text
router_rows: 1500
best_fixed_family_by_mae: recent2000
leaky_oracle_per_window_mae_improvement_vs_zero_shot: 5.952245%
leaky_oracle_per_window_smape_improvement_vs_zero_shot: 4.726858%
```

Label counts:

| Family | Best-window labels |
|---|---:|
| `zero-shot` | 379 |
| `full` | 328 |
| `recent1500` | 419 |
| `recent2000` | 197 |
| `recent3000` | 177 |

Label counts by cut:

| Cut | zero-shot | full | recent1500 | recent2000 | recent3000 |
|---:|---:|---:|---:|---:|---:|
| 4000 | 144 | 144 | 128 | 16 | 68 |
| 5000 | 83 | 152 | 176 | 49 | 40 |
| 5500 | 152 | 32 | 115 | 132 | 69 |

Fixed-family mean MAE:

| Family | Mean MAE |
|---|---:|
| `zero-shot` | 0.1094328925 |
| `full` | 0.1078023118 |
| `recent1500` | 0.1089190985 |
| `recent2000` | 0.1074011875 |
| `recent3000` | 0.1077175134 |

## Interpretation

Fact: the joiner produced 1500 router rows.

Fact: `runtime_features` passed the no-leak key check.

Fact: the best fixed family by mean MAE is still `recent2000`.

Fact: the per-window leaky oracle reaches 5.95% MAE improvement versus
zero-shot.

Inference: adapter choice has more upside at the individual-window level than
the previous aggregate cut-level oracle showed.

Inference: the labels are not dominated by one family. `zero-shot`,
`recent1500`, and `full` each win hundreds of windows, while `recent2000`
becomes more important on cut5500.

Recommendation: do not publish a router yet. The oracle uses future errors and
is invalid as a production policy. The next valid experiment is a no-leak
router that trains only on prior cuts and evaluates on the next chronological
cut.

## Next Experiment Direction

Next controlled step:

```text
method=no-leak prediction-level router
train=prior cuts only
evaluate=current cut
features=context summaries + prediction disagreement
label=best_family_by_mae
compare=zero-shot,fixed recent2000,leaky per-window oracle
```

Promotion remains blocked until a no-leak router beats fixed `recent2000` on
future cuts.
