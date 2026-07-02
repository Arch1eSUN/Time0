# Feature Veto Frozen Validation

Date: 2026-07-02

## Problem Framing

The previous target-series fallback rule did not have future exposure after
freezing. This run asks a stronger question:

```text
Can a no-leak runtime feature detect bad override windows before future labels
are known?
```

The test learns a single-feature fallback-veto rule on discovery cuts through
`cut3500`, freezes that rule, and evaluates it on future cuts after `cut3500`.

## Command

```bash
uv run python scripts/validate_feature_veto_rule.py
```

Runtime after delta-cache optimization:

```text
about 9 seconds on this local Mac
```

## Inputs

```text
router rows:
  reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

router report:
  reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

output:
  reports/router-feature-veto-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Frozen Rule

```text
feature: context.past_trend
direction: <=
threshold: -0.3866836197
include_series: false
discovery_max_cut: 3500
```

This rule is not a hard-coded target-series rule. It uses only a runtime context
feature that is known before the forecast is scored.

## Result

```text
overall verdict: aggregate_positive_downside_regressed
future split verdict: rule_improves_split
```

| Split | Windows | Changed windows | Harmful vetoed | Beneficial blocked | Metric delta | Negative series |
|---|---:|---:|---:|---:|---:|---:|
| discovery through cut3500 | 1000 | 67 | 42 | 25 | +0.0001999397 | 3 -> 2 |
| future after cut3500 | 4000 | 84 | 36 | 48 | +0.0000128143 | 1 -> 2 |

## Interpretation

Fact: the frozen feature rule has future exposure. It changes 84 future
decisions after `cut3500`.

Fact: aggregate future MAE improves slightly. The future metric delta is
`+0.0000128143`, and the local split verdict is `rule_improves_split`.

Fact: the future downside profile regresses. Negative series increase from 1 to
2 after applying the feature veto.

Inference: a no-leak runtime signal exists, but this single-feature rule is not
release-ready. It moves the aggregate metric in the right direction while
violating the finance downside gate.

Recommendation: keep the feature-veto direction, but do not promote this rule.
The next experiment should add a downside-aware constraint to feature veto
selection, for example requiring that the frozen rule does not increase
future/validation negative series or selecting from multiple discovery windows
with a per-series downside penalty.

