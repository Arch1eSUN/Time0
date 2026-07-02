# Market Macro Override Failure Diagnosis

Date: 2026-07-02

## Goal

Diagnose the two remaining negative routed series from the current best router:

```text
BAMLH0A0HYM2:realized_vol_20
DEXJPUS:realized_vol_20
```

The question is whether the release blocker comes from broad adapter weakness
or from a small number of bad override windows.

## Code Changes

Added:

```text
scripts/diagnose_router_override_failures.py
```

The script replays a selected router policy and reports:

```text
per-target override windows
harmful vs beneficial override counts
selected adapter family breakdown
best-family labels on those windows
top harmful override examples
target fallback counterfactuals
combined target fallback counterfactual
```

## Command

```bash
uv run python scripts/diagnose_router_override_failures.py
```

Input defaults:

```text
router rows:
  reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

router report:
  reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

policy:
  summary.best_veto_by_delta
```

Output:

```text
reports/router-override-failure-diagnosis-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## Results

| Series | Override windows | Harmful overrides | Beneficial overrides | Override delta sum |
|---|---:|---:|---:|---:|
| BAMLH0A0HYM2 | 42 | 25 | 17 | -0.0263685151 |
| DEXJPUS | 47 | 29 | 18 | -0.0139567242 |

Current best router:

```text
relative_lift_vs_fallback: 0.318529%
positive / negative series: 8 / 2
```

Combined target fallback counterfactual:

```text
changed_windows: 89
relative_lift_vs_fallback: 0.327293%
positive / negative series: 8 / 0
```

## Target Details

BAMLH0A0HYM2:

```text
all selected counts:
  full: 33
  recent2000: 458
  zero-shot: 9

override selected family:
  full: 33 windows, +0.0028386842 delta, 18 harmful
  zero-shot: 9 windows, -0.0292071993 delta, 7 harmful

all override windows occur at cut3500
```

DEXJPUS:

```text
all selected counts:
  full: 3
  recent1500: 32
  recent2000: 453
  recent3000: 12

override selected family:
  full: 3 windows, -0.0040153118 delta, 3 harmful
  recent1500: 32 windows, -0.0064244556 delta, 17 harmful
  recent3000: 12 windows, -0.0035169569 delta, 9 harmful

all override windows occur at cut3500
```

## Interpretation

Fact: the remaining router downside is concentrated in 89 override windows, all
at cut3500 for the two negative series.

Fact: forcing only those two target series back to fallback clears negative
series and slightly improves aggregate lift.

Fact: this target fallback is an oracle counterfactual because the target series
were identified from the completed backtest.

Inference: the problem is not that all adapters are useless. The problem is that
the current router cannot detect bad override windows for these two series early
enough without leaking.

Recommendation: do not publish a hard-coded target-series veto yet. The next
valid experiment should create a future validation split or train/evaluate
features/adapters that can identify these bad override windows causally.
