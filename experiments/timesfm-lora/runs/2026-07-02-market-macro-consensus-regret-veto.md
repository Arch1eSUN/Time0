# Temporal-Prefix Consensus Expected-Regret Veto

Date: 2026-07-02

## Problem Framing

The utility-aware expected-regret run filtered high-lift false positives, but it
still could not produce a strict-positive validation candidate. This run tests a
different stability idea: train multiple expected-regret models on chronological
discovery prefixes and require consensus before vetoing an adapter override.

The goal is to test whether model agreement across discovery history reduces
fold metric regressions. The strict gate remains unchanged and final holdout is
not evaluated unless a strict-positive validation candidate exists.

## Commands

Default single-model smoke run:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --output reports/router-expected-regret-veto-consensus-default-smoke-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

No-series temporal-prefix consensus:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --consensus-mode temporal-prefix \
  --consensus-min-models 2 \
  --consensus-min-models 3 \
  --output reports/router-expected-regret-consensus-veto-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Series-aware temporal-prefix consensus:

```bash
uv run python scripts/validate_multifold_expected_regret_veto.py \
  --include-series \
  --consensus-mode temporal-prefix \
  --consensus-min-models 2 \
  --consensus-min-models 3 \
  --output reports/router-expected-regret-consensus-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Setup

```text
model: expected-regret ridge fallback-veto
consensus mode: temporal-prefix
discovery prefix cuts: 3000, 3250, 3500
consensus min models: 2, 3
selection_gate: strict
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
```

Decision rule:

```text
For each override window:
  train one expected-regret model per discovery prefix
  each model votes if predicted_regret >= regret_threshold
  veto to fallback only if vote_count >= consensus_min_models
```

## Default Smoke Result

```text
consensus_mode: single
validation_candidate_count: 105
validation_positive_count: 14
validation_utility_positive_count: 5
validation_strict_positive_count: 0
verdict: strict_gate_no_candidate
final_holdout_evaluated: false
```

This confirms the default single-model path remains compatible with the prior
expected-regret and utility-aware results.

## No-Series Consensus Result

```text
consensus_mode: temporal-prefix
validation_candidate_count: 210
validation_positive_count: 28
validation_utility_positive_count: 10
validation_strict_positive_count: 0
verdict: strict_gate_no_candidate
final_holdout_evaluated: false
```

Breakdown by consensus threshold:

| Consensus min models | Candidates | Positive | Utility positive | Strict positive |
|---:|---:|---:|---:|---:|
| 2 | 105 | 14 | 5 | 0 |
| 3 | 105 | 14 | 5 | 0 |

Best utility-ranked candidate:

| L2 | Regret threshold | Positive weight | Consensus min models | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | -0.0010 | 2.0 | 2 | 308 | +0.0013203037 | 0 | 1 | 0 | +0.0003203037 |

## Series-Aware Consensus Result

```text
consensus_mode: temporal-prefix
validation_candidate_count: 210
validation_positive_count: 14
validation_utility_positive_count: 0
validation_strict_positive_count: 0
verdict: strict_gate_no_candidate
final_holdout_evaluated: false
```

Breakdown by consensus threshold:

| Consensus min models | Candidates | Positive | Utility positive | Strict positive |
|---:|---:|---:|---:|---:|
| 2 | 105 | 7 | 0 | 0 |
| 3 | 105 | 7 | 0 | 0 |

Best utility-ranked candidate:

| L2 | Regret threshold | Positive weight | Consensus min models | Changed windows | Combined metric delta | Negative series delta | Fold metric regressions | Fold negative regressions | Utility score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.0020 | 4.0 | 2 | 94 | +0.0010332927 | 0 | 2 | 0 | -0.0009667073 |

## Interpretation

Fact: temporal-prefix consensus did not create any strict-positive validation
candidate.

Fact: `consensus_min_models=2` and `consensus_min_models=3` produced identical
aggregate counts on both no-series and series-aware surfaces.

Fact: final holdout remained untouched.

Inference: the discovery-prefix models are not disagreeing enough to filter the
unstable windows. Consensus gating does not fix the current blocker because the
submodels share the same feature surface and learn nearly the same failure
boundary.

Recommendation: stop adding more post-hoc gates to this expected-regret
surface. The next useful step should change the information available to the
router: richer no-leak regime features, target-specific instability features,
or a new data slice that directly addresses fold metric regressions.
