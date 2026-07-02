# Score-Vote Veto Under Multi-Fold Gate

Date: 2026-07-02

## Problem Framing

The previous two-feature AND veto improved the final holdout, but it was too
sparse: two validation folds had zero exposure. This run tests a score-vote
veto under the same chronological gate. Instead of requiring two conditions to
fire together, it counts how many discovery-selected single-feature rules match
and vetoes only when the vote count reaches a threshold.

## Command

```bash
uv run python scripts/validate_multifold_score_veto.py
```

## Setup

```text
initial discovery: cut <= 3500
validation folds: 3750, 4000, 4250
final holdout: cut > 4250
single_candidate_count: 60
score_candidate_count: 25
max_validation_fold_no_exposure: 0
```

The rule class is:

```text
votes = count(single_feature_rule_i matches)

if votes >= min_votes:
  selected_family = recent2000
```

## Selected Rule

```text
operator: vote
rule_count: 40
min_votes: 4
```

First rules in the vote pool:

```text
context.past_trend <= -0.3866836197
context.past_trend <= -0.34558421950000007
context.past_trend <= -0.4278790928
context.past_trend <= -0.35108272390000006
context.past_trend <= -0.6070787029999999
```

Selection result:

```text
selection_reason: best_available_no_robust_pass
validation_robust_pass_count: 0
validation_positive_count: 0
```

## Validation Result

Selected validation summary:

```text
combined_metric_delta: -0.0004421860
combined_negative_series_delta: 0
fold_negative_regressions: 1
fold_metric_regressions: 2
fold_no_exposure: 0
robust_pass: false
```

Top validation-ranked candidates:

| Rule count | Min votes | Changed windows | Combined metric delta | Negative series delta | Fold downside regressions |
|---:|---:|---:|---:|---:|---:|
| 40 | 4 | 168 | -0.0004421860 | 0 | 1 |
| 20 | 5 | 157 | -0.0000929890 | 1 | 1 |
| 20 | 4 | 162 | -0.0001076651 | 1 | 1 |
| 5 | 4 | 66 | -0.0001182361 | 1 | 1 |
| 10 | 4 | 66 | -0.0001182361 | 1 | 1 |

The important result is not just `robust_pass=false`. It is that
`validation_positive_count=0`: no score-vote candidate satisfied the weaker
validation condition of positive combined metric delta, no combined downside
increase, and no fold-level downside regression.

## Final Holdout

```text
windows: 2500
changed_windows: 72
harmful_vetoed: 47
beneficial_blocked: 25
metric_delta: +0.0001099906
negative_series: 2 -> 2
```

Relative lift vs fallback:

```text
original router: -0.144159%
score-vote veto: -0.027951%
```

Overall verdict:

```text
incremental_positive_but_below_fallback
```

## Interpretation

Fact: score-vote expands the final holdout intervention surface from the
two-feature rule's 7 changed windows to 72 changed windows.

Fact: the final holdout result improves the current router and keeps negative
series unchanged at `2 -> 2`.

Fact: every score-vote candidate fails validation. The selected candidate has
negative validation combined metric delta, and the full candidate set has
`validation_positive_count=0`.

Inference: the final holdout improvement is useful as a signal, but it is not
release evidence. The rule class is more expressive than two-feature AND, but
the validation split says the score boundary is not stable.

Recommendation: stop hand-written threshold ensembles for this branch. The
next useful router step is either a supervised no-leak router trained against
the same multi-fold gate, or new adapter candidates that change the prediction
surface instead of only changing the router rule.
