# 2026-07-01 Market Macro Realized Vol 20 Prediction Router

## Goal

Evaluate a no-leak prediction-level adapter router on the router rows produced
from prediction archives.

Question:

```text
Can runtime-safe context and prediction-disagreement features select a better
adapter family than fixed recent2000 on future cuts?
```

## Implementation

Added:

```text
scripts/evaluate_prediction_router.py
```

Input:

```text
reports/router-rows-market-macro-realized-vol-20-h20-r4.json
```

Output:

```text
reports/no-leak-prediction-router-market-macro-realized-vol-20-h20-r4.json
```

The output report is a generated local artifact and remains ignored by Git.

## Router Policies

Evaluated policies:

| Policy | Meaning | No-leak rule |
|---|---|---|
| fixed family | Always choose one family | no training |
| softmax | Linear classifier from runtime features to best-family label | train only on prior cuts |
| kNN regret | Find similar prior windows and choose lowest historical family error | train/search only prior cuts |
| validation-gated router | Use learned router only if it beats fallback on latest prior validation cut | validation is prior cut only |

Default fallback:

```text
fallback_family=recent2000
min_validation_lift=0.01
```

## Command

```bash
uv run python -m py_compile \
  scripts/evaluate_prediction_router.py \
  scripts/join_prediction_archives.py

uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-market-macro-realized-vol-20-h20-r4.json
```

## Results

Routed cuts only:

| Policy | MAE | MAE improvement vs zero-shot |
|---|---:|---:|
| fixed `recent2000` | 0.1037657315 | 1.507294% |
| best learned diagnostic: `knn_regret_series_k100` | 0.1040911166 | 1.198444% |
| validation-gated router | 0.1037657315 | 1.507294% |
| leaky per-window oracle | 0.1003816976 | 4.719363% |

Validation gate for cut5500:

| Item | MAE |
|---|---:|
| fallback `recent2000` on validation cut5000 | 0.0790878921 |
| best learned candidate on validation cut5000 | 0.0785417045 |
| required MAE to switch with 1% lift | 0.0782970132 |

The best learned candidate improved validation cut5000, but not enough to clear
the 1% lift threshold. The validation-gated policy therefore stayed on
`recent2000` for cut5500.

## Interpretation

Fact: the best learned chronological diagnostic did not beat fixed
`recent2000` on routed cuts.

Fact: the validation-gated router matched fixed `recent2000` because it refused
to switch without enough prior-cut evidence.

Fact: the leaky per-window oracle still shows 4.72% routed-cut MAE headroom.

Inference: the current runtime feature set contains useful signal, but the
available chronological supervision is too thin for a reliable learned router.

Inference: fail-closed routing is working. It prevents a plausible but weaker
learned router from replacing the strongest fixed adapter.

Recommendation: do not publish a router and do not promote this adapter family
to Moirai yet.

## Next Experiment Direction

Next controlled step:

```text
method=expanded rolling cut grid
purpose=more chronological router supervision
candidate_cuts=3500,3750,4250,4500,4750,5250
families=zero-shot,full,recent1500,recent2000,recent3000
```

Reason:

```text
The router currently has only 3 cuts. That gives only one real prior-validation
decision for a validation-gated selector. More rolling cuts are needed before
we can tell whether the router is weak or the dataset is too small.
```
