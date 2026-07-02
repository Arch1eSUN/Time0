# 052 - Oracle Counterfactuals

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-override-failure-diagnosis.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 找出剩下两个亏损 series 为什么亏 | residual downside diagnosis | `BAMLH0A0HYM2`, `DEXJPUS` |
| 看亏损是否集中在少数窗口 | override failure concentration | `override_windows` |
| 假设这些窗口都退回 fallback 会怎样 | counterfactual intervention | target fallback counterfactual |
| 标记这个假设不能直接发布 | oracle diagnostic only | guardrail |

通俗解释：

```text
上一轮我们知道：

  当前 best router 还有 2 个 negative series。

这一轮不继续瞎调阈值。
我们先问一个更具体的问题：

  这两个 series 是整体都不行，
  还是只有少数 override 窗口选错了？

如果只是少数窗口选错，
下一步应该训练或设计“识别坏 override 窗口”的能力。

如果整体都不行，
下一步才应该考虑新 adapter 或直接长期禁用。
```

专业解释：

```text
This round replays the current best no-leak router policy and diagnoses the
remaining negative series at the override-window level. It then computes an
oracle counterfactual: force target-series overrides to fallback and rescore the
same routed windows.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/diagnose_router_override_failures.py

report:
  reports/router-override-failure-diagnosis-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is An Oracle Counterfactual?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 事后开上帝视角问如果当时不这么选会怎样 | oracle counterfactual | completed-backtest intervention |
| 它能告诉我们潜力上限 | diagnostic upper bound | counterfactual lift |
| 它不能直接上线 | not deployable evidence | leakage guardrail |
| 真上线还需要未来验证 | future validation split | next gate |

通俗解释：

```text
counterfactual 就是：

  如果当时不这样做，
  结果会不会更好？

oracle counterfactual 是更危险的一种：

  我们已经看完答案，
  知道哪里错了，
  再回头假设那几个地方不犯错。

它很有用，
因为它告诉我们：

  问题有没有可修复空间。

但它不能直接发布，
因为它用到了事后信息。
```

专业解释：

```text
An oracle counterfactual changes decisions after observing completed evaluation
results. It estimates an upper bound or diagnostic opportunity, but it is not a
causal no-leak policy unless validated on future unseen cuts.
```

项目对应：

```text
guardrail:
  Target-series fallback counterfactuals are diagnostic only.
```

## 3. What We Found

| Series | Override windows | Harmful | Beneficial | Delta sum |
|---|---:|---:|---:|---:|
| BAMLH0A0HYM2 | 42 | 25 | 17 | -0.0263685151 |
| DEXJPUS | 47 | 29 | 18 | -0.0139567242 |

通俗解释：

```text
两个负收益 series 不是所有窗口都坏。

真正的问题集中在 override 窗口：

  BAMLH0A0HYM2 有 42 个 override 窗口，
  DEXJPUS 有 47 个 override 窗口。

这 89 个窗口如果全退回 fallback，
负收益 series 会从 2 个变 0 个。
```

专业解释：

```text
The residual downside is concentrated in 89 non-fallback selections. The
counterfactual intervention sets only these target-series overrides back to the
fallback family and leaves all other routed decisions unchanged.
```

项目对应：

```text
current best:
  relative_lift_vs_fallback = 0.318529%
  positive / negative series = 8 / 2

combined counterfactual:
  relative_lift_vs_fallback = 0.327293%
  positive / negative series = 8 / 0
```

## 4. Why This Is Not A Release Yet

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 我们是看完答案才知道这两个 series 有问题 | target discovered post hoc | completed backtest |
| 直接禁用它们会数据泄漏 | selection leakage | not no-leak |
| 需要新时间段验证 | future holdout validation | next split |
| 或者需要可提前识别的特征 | causal feature signal | router features |

通俗解释：

```text
你可能会想：

  那就直接把这两个 series 永远退回 fallback。

不能这么快。

因为我们现在知道它们有问题，
是因为我们已经看完了这套 backtest。

这像考试后看错题本，
然后说考试时我不会做错。

真正可以发布的规则必须在未来也成立。
所以它还需要下一段时间验证。
```

专业解释：

```text
The target-series veto is selected using completed evaluation results. It is a
post-hoc rule. To become deployable, it must be frozen before a future cut and
then evaluated without using that future cut's labels.
```

项目对应：

```text
not deployable yet:
  hard-coded BAMLH0A0HYM2 / DEXJPUS veto

deployable after:
  frozen rule passes future holdout without leakage
```

## 5. Adapter Problem Or Router Problem?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| adapter 不是全没用 | adapter signal exists | 8 positive series |
| router 在少数窗口误选 | selection error | harmful overrides |
| 新训练要围绕这些错误窗口 | targeted training/eval | target series |
| 不该继续全局乱调 | global threshold exhausted | previous rounds |

通俗解释：

```text
这轮结果告诉我们：

  不是 LoRA 完全没学到金融领域。

因为其他 8 个 series 仍然是正收益。

真正的问题是：

  router 在两个 series 的 cut3500 窗口，
  不知道什么时候该相信 fallback，
  什么时候该 override。

所以接下来不应该继续调一个全局阈值。
应该围绕这两个 series 的坏 override 窗口做训练或特征。
```

专业解释：

```text
The failure is localized policy selection error. The adapter family contains
usable signal, but the current selector lacks enough causal discrimination for
the two residual negative series.
```

项目对应：

```text
BAMLH0A0HYM2:
  zero-shot overrides are strongly negative

DEXJPUS:
  full, recent1500, and recent3000 overrides are all net negative
```

## 6. Next Direction

Fact:

```text
The 89-window target fallback counterfactual would clear negative series and
raise aggregate lift to 0.327293%.
```

Fact:

```text
The counterfactual is post-hoc and cannot be used as release evidence yet.
```

Inference:

```text
The next gate-moving experiment should test whether this localized failure can
be detected causally before seeing the future labels.
```

Recommendation:

```text
Freeze a target-series diagnostic rule or add target-specific router features,
then validate on a later unseen cut. If it survives, it becomes a real release
candidate. If it fails, train/evaluate a small adapter or rank variant aimed at
the BAMLH0A0HYM2 and DEXJPUS regimes.
```
