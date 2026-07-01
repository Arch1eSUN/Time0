# 040 - Latest-Cut Downside Guard

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-latest-cut-guard.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只看最近一次小考 | latest prior-cut validation | `prior_cuts[-1]` |
| 最近一次亏了就别选它 | per-series downside gate | `latest_cut_selection_risk_gate` |
| 先让 fallback-veto 选，再加安全阀 | guarded fallback-veto | `fallback_veto_latest_cut_guarded` |
| late 上能小赢，但 expanded 上不稳 | temporal robustness failed | no promotion |

通俗解释：

```text
上一轮我们发现：

  guarded fallback-veto 在完整 expanded surface 上能赢，
  但放到更后面的 late surface 上输了。

所以这轮我们试一个更敏感的安全阀：

  不再平均看很多旧 cut，
  只看最近一个 prior cut。

如果某个 series 在最近一次验证里被 router 选错，
这次就让它回到固定 fallback。
```

专业解释：

```text
This round adds `fallback_veto_latest_cut_guarded`, a router policy that first
builds prior fallback-veto selections, then computes a per-series validation
gate from only the latest prior cut. Series that fail the latest prior-cut
minimum lift are routed back to the fixed fallback family.
```

项目对应：

```text
new policy:
  fallback_veto_latest_cut_guarded

new gate:
  latest_cut_selection_risk_gate

fallback:
  recent2000

candidate set:
  knn-regret
```

## 2. What Is A Latest-Cut Guard?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 看最近一次考试成绩 | latest validation cut | latest prior cut |
| 最近亏，就先别冒险 | downside-aware routing | block series override |
| 反应快 | high recency sensitivity | no decay, no long average |
| 容易短视 | higher temporal variance | may overfit one cut |

通俗解释：

```text
假设我们每隔一段时间考一次模型。

以前的 guard 像这样：

  看过去很多次考试，
  越新的考试权重越高，
  然后算一个平均印象。

latest-cut guard 更激进：

  只看最近一次考试。

好处：

  如果市场状态刚刚变了，
  它能立刻反应。

坏处：

  如果最近一次只是偶然波动，
  它也会被带偏。
```

专业解释：

```text
The latest-cut gate trades statistical smoothing for regime sensitivity. It
uses the latest available chronological validation cut as the only per-series
risk signal. This can reduce stale historical averaging, but it also increases
variance because one cut can dominate the decision.
```

项目对应：

```text
recency-weighted guard:
  uses multiple prior cuts + decay

latest-cut guard:
  uses exactly one prior cut

selection fallback:
  blocked series -> recent2000
```

## 3. Result Summary

Routed cuts only:

| Check | Config | Delta vs fallback | Split | Verdict |
|---|---|---:|---:|---|
| Previous frozen late retest | recency guarded, balanced | -0.0000326219 | 7 / 3 | failed |
| Latest-cut late best | `series/k50/thr0.00025/msvl0.001` | 0.0000096078 | 3 / 3 | late positive |
| Same config on expanded | `series/k50/thr0.00025/msvl0.001` | -0.0000150012 | 4 / 4 | expanded failed |
| Expanded narrow best | `series/k25/thr0.00015/msvl-0.001` | 0.0001983892 | 6 / 4 | expanded positive |
| Same config on late | `series/k25/thr0.00015/msvl-0.001` | -0.0000426158 | 7 / 3 | late failed |
| Expanded k50 strict best | `series/k50/thr0.00015/msvl0.001` | -0.0000123373 | 4 / 4 | failed |

通俗解释：

```text
这轮最重要的不是“找到一个 late 上小赢的参数”。

最重要的是：

  late 上最好的参数，
  放回 expanded 会输。

  expanded 上最好的参数，
  放到 late 会输。

这说明它们不是同一个稳定规律。
```

专业解释：

```text
The latest-cut policy can optimize a single chronological surface, but the
best configuration does not transfer bidirectionally between expanded and late
archives. This is temporal instability, not promotion-quality lift.
```

项目对应：

```text
late sweep:
  reports/router-policy-sweep-latest-cut-guarded-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

expanded narrow sweep:
  reports/router-policy-sweep-latest-cut-guarded-fallback-veto-expanded-narrow-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

expanded k50 strict sweep:
  reports/router-policy-sweep-latest-cut-guarded-fallback-veto-expanded-k50-strict-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 4. How This Relates To LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 是不同专长的小插件 | adapter specialization | `full/recent1500/recent2000/recent3000` |
| Router 是派谁上场 | adapter selection policy | `summarize_router_attribution.py` |
| Guard 是安全员 | risk gate | fallback to `recent2000` |
| 本轮不是继续训练权重 | post-training selection experiment | no new adapter weights |

通俗解释：

```text
我们现在不是在重新训练 LoRA 权重。

我们已经有几类 adapter：

  full
  recent1500
  recent2000
  recent3000

现在的问题是：

  当前窗口到底该用哪个 adapter？

router 做选择。
guard 做刹车。

如果 router 想选一个 adapter，
但 guard 发现这个 series 最近刚被这个选择坑过，
就不让它冒险，退回 fallback。
```

专业解释：

```text
This checkpoint is part of post-training adapter routing. The LoRA adapters are
fixed; the experiment changes the selection interface. A guard is not another
adapter. It is a constraint on the adapter selector that prevents overrides
when validation evidence suggests per-series downside.
```

项目对应：

```text
LoRA adapter evidence:
  prediction archives

router evidence:
  router rows

guard evidence:
  attribution + sweep reports
```

## 5. Why Single-Surface Wins Are Dangerous

通俗解释：

```text
如果我们只看 late：

  会觉得 latest-cut guard 成功了。

如果我们只看 expanded：

  又会选另一个完全不同的参数。

但两个参数互相一换地方就输。

这说明：

  我们不是发现了稳定能力，
  只是发现了某个时间段的局部最优。
```

专业解释：

```text
Single-surface tuning creates post-hoc selection risk. A policy can show
positive delta after being selected on the same surface, while still failing
out-of-surface chronological validation. Promotion requires a frozen config
that survives both aggregate and later chronological checks.
```

项目对应：

```text
promotion condition:
  same frozen config positive on expanded and late

current state:
  no tested latest-cut config satisfies this
```

## 6. Current Verdict

Fact:

```text
Latest-cut guard improved the late surface enough to find a small positive
late-only configuration.
```

Fact:

```text
The late-best configuration failed on expanded:

  late delta:     0.0000096078
  expanded delta: -0.0000150012
```

Fact:

```text
The expanded-best narrow configuration failed on late:

  expanded delta: 0.0001983892
  late delta:    -0.0000426158
```

Inference:

```text
Latest-cut gating is useful as a diagnostic tool, but too myopic to promote as
the current main router policy.
```

Recommendation:

```text
Do not promote `fallback_veto_latest_cut_guarded` yet.

Next step:
  build a two-horizon temporal guard.

It should require:
  1. latest prior cut is not bad
  2. longer prior history is not bad

That would combine the quick reaction of latest-cut with the stability of
recency-weighted validation.
```
