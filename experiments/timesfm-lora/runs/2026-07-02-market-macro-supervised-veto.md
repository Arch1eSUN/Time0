# Supervised KNN-Regret Veto Under Multi-Fold Gate

Date: 2026-07-02

## Problem Framing

The score-vote experiment showed that wider hand-written rules can improve the
final holdout, but validation rejects the rule class. This run moves from
hand-written thresholds to a supervised fallback-veto policy. The model trains
on historical override windows where the realized outcome tells us whether the
router should have stayed with its selected adapter or fallen back to
`recent2000`.

This is still not a LoRA weight update. It is a learned router experiment on
top of the existing TimesFM LoRA adapter prediction surface.

## Commands

Default no-series run:

```bash
uv run python scripts/validate_multifold_supervised_veto.py
```

Series-aware sensitivity:

```bash
uv run python scripts/validate_multifold_supervised_veto.py \
  --include-series \
  --output reports/router-supervised-veto-multifold-validation-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Setup

```text
model: KNN regret veto
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
discovery_examples: 442
final_train_examples: 1022
candidate configs: 30
k values: 5, 10, 25, 50, 100
regret thresholds: -0.001, -0.0005, 0.0, 0.00025, 0.0005, 0.001
```

Training label:

```text
regret_vs_fallback = selected_adapter_error - fallback_error

positive regret:
  selected adapter was worse than fallback

negative regret:
  selected adapter was better than fallback
```

Decision rule:

```text
find k similar historical override windows
mean_regret = mean(neighbor.regret_vs_fallback)

if mean_regret > regret_threshold:
  selected_family = recent2000
```

## Default No-Series Result

Selected config:

```text
k: 25
regret_threshold: 0.001
selection_reason: robust_pass
```

Validation:

```text
validation_robust_pass_count: 5
validation_positive_count: 6
validation_strict_positive_count: 0
selected combined_metric_delta: +0.0004494389
selected combined_negative_series_delta: 0
selected fold_negative_regressions: 0
selected fold_metric_regressions: 2
```

Final holdout:

```text
windows: 2500
current_overrides: 138
changed_windows: 29
metric_delta: -0.0000276801
negative_series: 2 -> 2
```

Relative lift vs fallback:

```text
original router: -0.144159%
supervised veto: -0.173404%
```

Overall verdict:

```text
not_promotable
```

## Series-Aware Sensitivity

Selected config:

```text
k: 25
regret_threshold: -0.001
selection_reason: best_available_no_robust_pass
```

Validation:

```text
validation_robust_pass_count: 0
validation_positive_count: 0
validation_strict_positive_count: 0
selected combined_metric_delta: +0.0001150316
selected combined_negative_series_delta: 1
selected fold_metric_regressions: 2
```

Final holdout:

```text
windows: 2500
current_overrides: 138
changed_windows: 44
metric_delta: +0.0000228784
negative_series: 2 -> 2
```

Relative lift vs fallback:

```text
original router: -0.144159%
series-aware supervised veto: -0.119987%
```

Overall verdict:

```text
incremental_positive_but_below_fallback
```

## Interpretation

Fact: the no-series supervised router finds validation-positive configs, but
the selected validation winner fails final holdout.

Fact: `validation_strict_positive_count=0`, because every validation-positive
candidate still has fold-level metric regressions.

Fact: the series-aware sensitivity improves final holdout slightly, but it has
0 robust-pass candidates and 0 validation-positive candidates.

Inference: KNN-regret learns a real local regret signal, but the signal is not
stable enough across chronological regimes. The default result shows
validation-to-final transfer failure. The series-aware result shows a final-only
signal that validation does not support.

Recommendation: do not promote the supervised KNN-regret veto. The next useful
step is not more threshold tuning; it is either a stricter validation gate with
0 fold metric regressions required, or a genuinely trained probabilistic router
with calibrated uncertainty and per-series downside constraints.
