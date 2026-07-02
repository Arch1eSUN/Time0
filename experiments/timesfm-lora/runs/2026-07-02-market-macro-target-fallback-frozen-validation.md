# Target Fallback Frozen Validation

Date: 2026-07-02

## Problem Framing

Previous diagnosis found that the remaining negative routed series were
concentrated in target-series override windows:

```text
BAMLH0A0HYM2:realized_vol_20
DEXJPUS:realized_vol_20
```

Forcing those target series back to the `recent2000` fallback family improved
the completed backtest. That was still an oracle counterfactual, not a
deployable policy. This run tests whether the same target fallback rule has
future validation exposure after being frozen.

## Command

```bash
uv run python scripts/validate_target_fallback_rule.py
```

## Inputs

```text
router rows:
  reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

router report:
  reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

diagnosis report:
  reports/router-override-failure-diagnosis-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

output:
  reports/router-target-fallback-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Result

```text
verdict: not_validated_no_future_exposure
target series:
  BAMLH0A0HYM2:realized_vol_20
  DEXJPUS:realized_vol_20
freeze_after_cut: 3500
```

| Split | Windows | Changed windows | Relative lift vs fallback | Negative series | Verdict |
|---|---:|---:|---:|---:|---|
| posthoc all rows | 5000 | 89 | 0.327293% | 0 | diagnostic only |
| through freeze cut | 1000 | 89 | 0.983608% | 1 | rule_improves_split |
| future after freeze cut | 4000 | 0 | 0.196213% | 1 | no_rule_exposure |

## Interpretation

Fact: the completed-backtest counterfactual still improves the all-row report:
89 changed windows, 0 negative series, and 0.327293% relative lift over the
`recent2000` fallback family.

Fact: all 89 changed windows are in the discovery split through `cut3500`.

Fact: the future split after `cut3500` has 4000 routed windows and 0 changed
windows for the frozen target fallback rule.

Inference: this rule is not validated. It did not lose money in the future
split, but it also did not make any decisions in the future split.

Recommendation: do not promote the hard-coded target fallback rule. Treat it as
a diagnostic that identifies a localized router failure. The next gate-moving
experiment needs either a later prediction archive where the same frozen rule
has future exposure, or a causal feature/router that can detect bad override
windows before labels are known.

