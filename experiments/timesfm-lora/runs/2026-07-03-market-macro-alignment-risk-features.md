# Expected-Regret Alignment-Risk Feature Surface

Date: 2026-07-03

## Problem Framing

The previous fold-regression attribution showed that harmed and helped veto
windows separate on prediction-context alignment features. This run tests that
idea directly by adding a switchable `alignment-risk` feature surface to the
expected-regret veto.

The default remains `base`. The new surface is opt-in through:

```bash
--feature-surface alignment-risk
```

## What Changed

`router_fallback_veto.py` now supports an extra feature surface. It appends 14
derived features built from already available runtime features:

```text
selected adapter absolute alignment displacement
fallback adapter absolute alignment displacement
selected-minus-fallback alignment displacement
maximum family absolute alignment displacement
selected trend/sign mismatch indicators
```

The validation script records the active feature surface in every report, and
the fold-regression diagnostic reads it back from the source report. This keeps
training and diagnosis aligned.

## Commands

Base smoke checks:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --output reports/router-expected-regret-veto-base-smoke-alignment-risk-change-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --output reports/router-expected-regret-veto-base-smoke-include-series-alignment-risk-change-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Alignment-risk strict validation:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --feature-surface alignment-risk \
  --output reports/router-expected-regret-veto-alignment-risk-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --feature-surface alignment-risk \
  --output reports/router-expected-regret-veto-alignment-risk-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Robust diagnostic only:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --feature-surface alignment-risk \
  --selection-gate robust \
  --output reports/router-expected-regret-veto-alignment-risk-robust-diagnostic-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --feature-surface alignment-risk \
  --selection-gate robust \
  --output reports/router-expected-regret-veto-alignment-risk-robust-diagnostic-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Alignment-risk fold attribution:

```bash
uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-alignment-risk-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-alignment-risk-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

uv run python scripts/diagnose_expected_regret_fold_regressions.py \
  --report reports/router-expected-regret-veto-alignment-risk-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json \
  --output reports/router-expected-regret-fold-regression-attribution-alignment-risk-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Strict Validation Results

| Surface | Include series | Robust-pass candidates | Utility-positive candidates | Strict-positive candidates | Verdict |
|---|---:|---:|---:|---:|---|
| base | no | 14 | 5 | 0 | strict_gate_no_candidate |
| alignment-risk | no | 16 | 0 | 0 | strict_gate_no_candidate |
| base | yes | 7 | 0 | 0 | strict_gate_no_candidate |
| alignment-risk | yes | 6 | 0 | 0 | strict_gate_no_candidate |

Strict validation did not promote any alignment-risk candidate.

## Robust Diagnostic Results

Robust mode evaluates final holdout even when fold-level strict validation is
not clean. It is diagnostic evidence only.

| Surface | Include series | Final metric delta | Final relative lift | Changed windows | Final verdict |
|---|---:|---:|---:|---:|---|
| base | no | +0.0002280509 | +0.0009678327 | 77 | future_validated_positive |
| alignment-risk | no | +0.0001021934 | -0.0003618867 | 85 | incremental_positive_but_below_fallback |
| base | yes | +0.0001617361 | +0.0002671987 | 67 | future_validated_positive |
| alignment-risk | yes | +0.0001575894 | +0.0002233868 | 81 | future_validated_positive |

The raw alignment-risk surface does not beat the base surface. It is slightly
closer on include-series, but still weaker than base on final holdout.

## Alignment-Risk Attribution

No-series alignment-risk:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | -0.0001195002 | 173 | 88 | 85 | fold_regresses |
| 4000 | -0.0004633152 | 92 | 35 | 57 | fold_regresses |
| 4250 | +0.0045841671 | 76 | 52 | 24 | fold_improves |

Worst no-series fold:

```text
cut: 4000
metric_delta: -0.0004633152
main series harm: DFF:realized_vol_20, sum_delta -0.1974912665
main family harm: recent1500, sum_delta -0.1736482605
```

Include-series alignment-risk:

| Cut | Metric delta | Changed windows | Help windows | Harm windows | Verdict |
|---:|---:|---:|---:|---:|---|
| 3750 | +0.0000112141 | 180 | 93 | 87 | fold_improves |
| 4000 | -0.0000212966 | 105 | 43 | 62 | fold_regresses |
| 4250 | +0.0012210300 | 118 | 68 | 50 | fold_improves |

Worst include-series fold:

```text
cut: 4000
metric_delta: -0.0000212966
main series harm: VIXCLS:realized_vol_20, sum_delta -0.0496361358
main family harm: zero-shot, sum_delta -0.0514676563
```

## Conclusion

Fact: the new alignment-risk surface increases loose no-series robust-pass
candidates from 14 to 16, but utility-positive candidates fall from 5 to 0.

Fact: include-series alignment-risk reduces strict diagnostic fold regressions
to one small cut4000 regression, but final holdout is still slightly weaker
than base include-series.

Fact: strict promotion remains blocked with zero strict-positive candidates.

Inference: raw derived alignment features add signal and noise at the same
time. They help expose the failure surface, but they do not improve the router
enough to promote.

Recommendation: keep `alignment-risk` as an experimental switch, not the
default. The next useful experiment is a smaller, regularized alignment surface
or feature selection pass, not adding more raw alignment columns.
