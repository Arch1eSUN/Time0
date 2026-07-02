# Downside-Aware Feature Veto

Date: 2026-07-02

## Problem Framing

The previous no-leak feature veto found real future exposure and slight
aggregate MAE improvement, but it increased future negative series from 1 to 2.
This run tests whether adding a discovery-side downside objective can select a
safer single-feature rule.

## Commands

Default aggregate objective reproducibility check:

```bash
uv run python scripts/validate_feature_veto_rule.py
```

Downside-filtered objective:

```bash
uv run python scripts/validate_feature_veto_rule.py \
  --selection-objective downside-aware \
  --output reports/router-feature-veto-downside-aware-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

Downside-first objective:

```bash
uv run python scripts/validate_feature_veto_rule.py \
  --selection-objective downside-first \
  --output reports/router-feature-veto-downside-first-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Objective Change

The script now supports:

| Objective | Meaning |
|---|---|
| `aggregate` | choose the positive discovery rule with best aggregate metric delta |
| `downside-aware` | keep only rules that do not increase discovery negative series, then choose best aggregate metric delta |
| `downside-first` | choose the rule with best discovery negative-series improvement, then best aggregate metric delta |

Defaults remain unchanged. The previous aggregate report is still reproducible
without extra arguments.

## Result

All three objectives selected the same rule:

```text
feature: context.past_trend
direction: <=
threshold: -0.3866836197
```

Downside-first report:

```text
overall verdict: aggregate_positive_downside_regressed
positive discovery candidates: 1150
selected discovery candidates after downside filter: 1150
```

| Split | Windows | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---:|---|
| discovery through cut3500 | 1000 | 67 | +0.0001999397 | 3 -> 2 | improves discovery |
| future after cut3500 | 4000 | 84 | +0.0000128143 | 1 -> 2 | aggregate improves, downside regresses |

## Interpretation

Fact: the aggregate-best rule already improves discovery negative series from 3
to 2, so the `downside-aware` filter does not remove it.

Fact: `downside-first` also selects the same rule. Among positive single-feature
discovery rules, this rule is already on the best observed discovery downside
frontier.

Fact: future negative series still regress from 1 to 2.

Inference: discovery-side downside improvement is not sufficient to guarantee
future-side downside improvement for a single-feature threshold rule.

Recommendation: stop escalating single-feature threshold objectives. The next
router experiment needs either a multi-feature model with explicit validation
downside selection, or a policy that evaluates candidate rules across multiple
chronological validation folds before freezing.

