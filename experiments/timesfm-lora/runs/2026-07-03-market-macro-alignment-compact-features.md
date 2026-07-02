# Expected-Regret Compact Alignment Feature Surface

Date: 2026-07-03

## Problem Framing

The previous `alignment-risk` surface added 14 derived alignment features. It
had signal, but it did not pass strict validation and underperformed the base
surface in robust final diagnostics.

This run tests a narrower hypothesis:

```text
Maybe raw alignment-risk failed because the feature surface was too wide.
If so, a compact alignment surface should reduce noise and improve transfer.
```

## What Changed

Added a second opt-in surface:

```bash
--feature-surface alignment-compact
```

It appends only five derived features:

```text
selected_abs_predicted_trend_minus_past_trend
selected_abs_predicted_last_delta_from_past_last_over_std
selected_abs_predicted_mean_delta_from_past_last_over_std
selected_minus_fallback_abs_predicted_trend_minus_past_trend
selected_minus_fallback_abs_predicted_last_delta_from_past_last_over_std
```

Compared with `alignment-risk`, it removes:

```text
fallback-only absolute displacement
family max absolute displacement
sign mismatch indicators
selected-minus-fallback mean displacement
```

## Commands

Compact strict validation:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --feature-surface alignment-compact \
  --output reports/router-expected-regret-veto-alignment-compact-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --feature-surface alignment-compact \
  --output reports/router-expected-regret-veto-alignment-compact-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Compact robust diagnostic:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --feature-surface alignment-compact \
  --selection-gate robust \
  --output reports/router-expected-regret-veto-alignment-compact-robust-diagnostic-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --feature-surface alignment-compact \
  --selection-gate robust \
  --output reports/router-expected-regret-veto-alignment-compact-robust-diagnostic-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Strong-L2 compact diagnostic:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --feature-surface alignment-compact \
  --l2 1 --l2 10 --l2 100 --l2 1000 \
  --output reports/router-expected-regret-veto-alignment-compact-strong-l2-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --feature-surface alignment-compact \
  --l2 1 --l2 10 --l2 100 --l2 1000 \
  --output reports/router-expected-regret-veto-alignment-compact-strong-l2-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Fold attribution:

```bash
uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-alignment-compact-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-alignment-compact-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-alignment-compact-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-alignment-compact-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Strict Validation Results

| Surface | Include series | Robust-pass candidates | Utility-positive candidates | Strict-positive candidates | Verdict |
|---|---:|---:|---:|---:|---|
| alignment-risk | no | 16 | 0 | 0 | strict_gate_no_candidate |
| alignment-compact | no | 10 | 0 | 0 | strict_gate_no_candidate |
| alignment-risk | yes | 6 | 0 | 0 | strict_gate_no_candidate |
| alignment-compact | yes | 11 | 0 | 0 | strict_gate_no_candidate |

Compact alignment does not produce a strict promotion candidate.

## Robust Final Diagnostics

| Surface | Include series | Final metric delta | Final relative lift | Final negative series | Changed windows | Verdict |
|---|---:|---:|---:|---:|---:|---|
| base | no | +0.0002280509 | +0.0009678327 | 1 | 77 | future_validated_positive |
| alignment-risk | no | +0.0001021934 | -0.0003618867 | 2 | 85 | incremental_positive_but_below_fallback |
| alignment-compact | no | +0.0001788929 | +0.0004484648 | 1 | 80 | future_validated_positive |
| base | yes | +0.0001617361 | +0.0002671987 | 1 | 67 | future_validated_positive |
| alignment-risk | yes | +0.0001575894 | +0.0002233868 | 1 | 81 | future_validated_positive |
| alignment-compact | yes | +0.0001521865 | +0.0001663039 | 2 | 84 | future_validated_positive |

Compact no-series improves over raw alignment-risk no-series, but it still does
not beat base no-series. Compact include-series is weaker than both base and raw
alignment-risk include-series.

## Strong-L2 Diagnostic

| Surface | Include series | Candidate count | Robust-pass candidates | Positive candidates | Strict-positive candidates |
|---|---:|---:|---:|---:|---:|
| alignment-compact strong L2 | no | 84 | 1 | 1 | 0 |
| alignment-compact strong L2 | yes | 84 | 0 | 0 | 0 |

Strong L2 does not solve the fold-regression blocker. It mostly removes useful
exposure.

## Fold Attribution

No-series compact:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | -0.0001093711 | 173 | 89 | 84 | fold_regresses |
| 4000 | -0.0004609448 | 92 | 36 | 56 | fold_regresses |
| 4250 | +0.0037927109 | 73 | 49 | 24 | fold_improves |

Worst no-series compact fold:

```text
cut: 4000
metric_delta: -0.0004609448
main series harm: DFF:realized_vol_20, sum_delta -0.1974912665
main family harm: recent1500, sum_delta -0.1736482605
```

Include-series compact:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | +0.0000120104 | 171 | 89 | 82 | fold_improves |
| 4000 | -0.0000201786 | 105 | 43 | 62 | fold_regresses |
| 4250 | +0.0012210300 | 118 | 68 | 50 | fold_improves |

Worst include-series compact fold:

```text
cut: 4000
metric_delta: -0.0000201786
main series harm: VIXCLS:realized_vol_20, sum_delta -0.0496361358
main family harm: zero-shot, sum_delta -0.0509086592
```

## Conclusion

Fact: `alignment-compact` does not pass strict validation. Strict-positive
candidates remain `0`.

Fact: compact no-series is better than raw alignment-risk no-series on robust
final holdout, but still worse than base.

Fact: compact include-series increases loose validation candidates but worsens
final negative series from `1` to `2`.

Fact: strong L2 makes the candidate pool weaker instead of cleaner.

Inference: the blocker is not simply "too many raw alignment columns" or "not
enough ridge regularization." The remaining failure is localized to specific
cut4000 veto errors, especially VIXCLS/zero-shot and DFF/recent1500 patterns.

Recommendation: stop expanding alignment feature surfaces in this expected-
regret ridge form. The next useful step is either a fold-conditioned abstention
rule for cut4000-like contexts or a different target that learns "do not veto"
rather than only expected regret magnitude.
