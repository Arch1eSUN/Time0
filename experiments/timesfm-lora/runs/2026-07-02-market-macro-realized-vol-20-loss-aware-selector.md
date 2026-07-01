# 2026-07-02 Market Macro Realized Vol 20 Loss-Aware Selector

## Goal

Test whether a supervised loss-aware selector can improve over the previous
manual policy frontier.

Previous checkpoint:

```text
baseline validation-gated MAE delta vs fallback: 0.0002674001
best diagnostic knn_regret_no_series_k25 delta: 0.0004631997
promotion status: blocked by series stability
```

The question for this run:

```text
Can a linear selector trained on continuous regret beat one-hot softmax and
improve the validation-gated policy?
```

## Implementation

Changed:

```text
scripts/evaluate_prediction_router.py
scripts/summarize_router_attribution.py
scripts/sweep_router_policies.py
```

Added opt-in candidate set:

```text
--candidate-set loss-aware
```

Default behavior remains:

```text
--candidate-set baseline
```

New candidates:

```text
regret_softmax_raw_no_series
regret_softmax_relative_no_series
regret_softmax_raw_series
regret_softmax_relative_series
```

The regret-softmax objective optimizes expected regret from the per-row family
error vector. Raw regret keeps absolute error magnitude; relative regret divides
regret by the row mean error.

## Commands

Baseline reproducibility check:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-baseline-check-market-macro-realized-vol-20-h20-r4.json
```

Loss-aware run:

```bash
uv run python scripts/evaluate_prediction_router.py \
  --candidate-set loss-aware \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/no-leak-prediction-router-early-regime-ablate-alignment-normalized-loss-aware-market-macro-realized-vol-20-h20-r4.json
```

Loss-aware attribution:

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set loss-aware \
  --input reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-attribution-loss-aware-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Generated reports remain ignored local artifacts.

## Results

Routed cuts only, MAE:

| Selector | MAE | Delta vs fallback |
|---|---:|---:|
| `knn_regret_no_series_k25` | 0.0915600802 | 0.0004631997 |
| `knn_regret_series_k25` | 0.0916377215 | 0.0003855584 |
| `knn_regret_no_series_k100` | 0.0917805651 | 0.0002427147 |
| `knn_regret_series_k50` | 0.0917974896 | 0.0002257903 |
| `regret_softmax_raw_no_series` | 0.0918167750 | 0.0002065049 |
| `regret_softmax_raw_series` | 0.0918311609 | 0.0001921190 |
| `regret_softmax_relative_series` | 0.0918442535 | 0.0001790263 |
| `softmax` | 0.0919876795 | 0.0000356004 |
| `regret_softmax_relative_no_series` | 0.0920712010 | -0.0000479211 |
| `softmax_series` | 0.0922571457 | -0.0002338658 |

Gated policy comparison:

| Candidate set | Validation-gated MAE | Delta vs fallback |
|---|---:|---:|
| `baseline` | 0.0917558798 | 0.0002674001 |
| `loss-aware` | 0.0917866231 | 0.0002366568 |

Loss-aware attribution:

```text
positive routed series: 4
negative routed series: 6
top positive: DFF, DGS2, DEXUSEU
top negative: VIXCLS, SP500, DCOILWTICO
```

## Interpretation

Fact: default `baseline` behavior is preserved and reproduces the previous
`0.0002674001` validation-gated delta.

Fact: regret-softmax beats ordinary one-hot softmax, so the loss-aware objective
has signal.

Fact: regret-softmax does not beat KNN-regret diagnostics.

Fact: adding regret-softmax to the gated candidate set reduces validation-gated
delta from `0.0002674001` to `0.0002366568`.

Inference: the selector bottleneck is not only the objective. Linear
regret-softmax underfits the local market/regime structure that KNN-regret
captures more directly.

Recommendation: keep `--candidate-set loss-aware` as an opt-in diagnostic, but
do not promote it. The next useful experiment is calibrated KNN-regret gating or
a nonlinear/local selector with explicit per-series downside control.

## Current Verdict

```text
regret objective: useful signal
linear regret-softmax: negative result
baseline reproducibility: preserved
promotion status: blocked
next step: calibrated local selector, not more linear selector tuning
```
