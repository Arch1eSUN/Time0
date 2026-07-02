# Strict Gate For Supervised KNN-Regret Veto

Date: 2026-07-02

## Problem Framing

The previous supervised KNN-regret run found validation-positive candidates, but
the selected no-series policy failed final holdout. The failure mode was clear:
combined validation looked good while individual validation folds still
regressed. This run adds a strict selection gate before final evaluation.

The goal is not to find a better final number. The goal is to prevent weak
validation evidence from reaching final holdout selection.

## Commands

Default supervised run, kept for reproducibility:

```bash
uv run python scripts/validate_multifold_supervised_veto.py
```

Strict no-series gate:

```bash
uv run python scripts/validate_multifold_supervised_veto.py \
  --selection-gate strict \
  --output reports/router-supervised-veto-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strict series-aware sensitivity:

```bash
uv run python scripts/validate_multifold_supervised_veto.py \
  --selection-gate strict \
  --include-series \
  --output reports/router-supervised-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Strict Gate Definition

A candidate must satisfy all of:

```text
combined_metric_delta > 0
combined_negative_series_delta <= 0
fold_negative_regressions == 0
fold_metric_regressions == 0
fold_no_exposure <= max_fold_no_exposure
```

If no candidate passes, the script returns:

```text
verdict: strict_gate_no_candidate
selected_config: null
final_holdout_evaluated: false
```

## No-Series Result

```text
selection_gate: strict
validation_candidate_count: 30
validation_robust_pass_count: 5
validation_positive_count: 6
validation_strict_positive_count: 0
selected_config: null
selection_reason: strict_gate_no_candidate
final_holdout_evaluated: false
verdict: strict_gate_no_candidate
```

Interpretation:

```text
The old loose gate finds candidates, but the strict gate rejects all of them.
The previous final failure is now caught before final holdout selection.
```

## Series-Aware Result

```text
selection_gate: strict
include_series: true
validation_candidate_count: 30
validation_robust_pass_count: 0
validation_positive_count: 0
validation_strict_positive_count: 0
selected_config: null
selection_reason: strict_gate_no_candidate
final_holdout_evaluated: false
verdict: strict_gate_no_candidate
```

Interpretation:

```text
The series-aware branch had a final-only positive signal in the previous run,
but strict validation correctly blocks it before final holdout.
```

## What Changed In The Script

The script now supports:

```text
--selection-gate robust
--selection-gate strict
```

`robust` keeps the previous behavior for reproducibility.

`strict` requires zero fold metric regressions and fails closed when no
candidate passes.

## Interpretation

Fact: strict gate rejects all supervised KNN-regret candidates on both no-series
and series-aware surfaces.

Fact: strict mode does not evaluate final holdout when validation has no strict
candidate.

Fact: the previous no-series final failure is explained by the new diagnostic:
`validation_strict_positive_count=0`.

Inference: the supervised router direction still has signal, but no current
candidate deserves final promotion. The selection gate is now aligned with the
observed failure mode.

Recommendation: keep strict validation as the default promotion criterion for
future supervised router work. The next model experiment should improve
candidate quality, not relax the gate.
