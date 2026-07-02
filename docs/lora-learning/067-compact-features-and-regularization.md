# 067 - Compact Features And Regularization

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-alignment-compact-features.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 上一轮特征太多，可能太吵 | raw surface may be noisy | `alignment-risk` 14 features |
| 这轮只保留核心线索 | compact representation | `alignment-compact` 5 features |
| 再试强正则 | stronger ridge regularization | `--l2 1/10/100/1000` |
| 看 strict gate 能不能过 | promotion validation | `strict_positive` |

通俗解释：

```text
上一轮我们给 router 看了 14 个 alignment-risk 特征。

结果是：

  有信号，
  但不够稳，
  不能晋级。

这轮我们问：

  是不是给它看的东西太多了？
  如果只给它看最关键的 5 个，会不会更稳？
```

专业解释：

```text
This run tests representation compression and stronger regularization for the
expected-regret veto. It introduces `alignment-compact`, a five-feature derived
surface, then evaluates default and strong-L2 grids under the same chronological
validation protocol.
```

项目对应：

```text
new flag value:
  --feature-surface alignment-compact

script:
  experiments/timesfm-lora/scripts/router_fallback_veto.py
```

## 2. What Is Feature Compression?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把一堆线索缩成少数核心线索 | reduce feature dimensionality | 14 -> 5 features |
| 少看一点，可能更稳 | lower variance | compact surface |
| 但可能丢掉有用信息 | higher bias risk | underfit risk |
| 目标是减少噪声 | improve generalization | fold transfer |

通俗解释：

```text
你判断一个人会不会迟到。

你可以看 50 个线索：

  天气。
  距离。
  心情。
  睡眠。
  早餐。
  鞋子颜色。

线索越多，不一定越好。

有些线索只是噪声。
模型可能会把噪声当规律。

feature compression 就是：

  删掉可疑线索，
  留下最可能有用的线索。
```

专业解释：

```text
Feature compression reduces the input dimensionality of a learned module. The
goal is to reduce variance and overfitting by removing weak, redundant, or
unstable features. The tradeoff is that the model may lose useful information
and become too biased.
```

项目对应：

```text
alignment-risk:
  14 extra features

alignment-compact:
  5 extra features
```

## 3. What We Kept

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| selected 自己偏得多不多 | selected absolute displacement | selected_abs_* |
| selected 是否比 fallback 更极端 | relative displacement | selected_minus_fallback_abs_* |
| 趋势偏离 | trend alignment risk | trend_minus_past_trend |
| 最后值偏离 | last-value risk | last_delta_from_past_last_over_std |

通俗解释：

```text
compact surface 只保留两个问题：

1. selected adapter 自己是不是很激进？
2. selected adapter 是不是比 fallback 更激进？

它不再看：

  所有 family 里谁最激进。
  fallback 自己的完整特征。
  sign mismatch 这种硬规则。
```

专业解释：

```text
The compact surface keeps selected adapter absolute displacement and
selected-minus-fallback relative displacement. It removes family-level maxima,
fallback-only absolute displacement, and sign-mismatch indicators.
```

项目对应：

```text
kept:
  selected_abs_predicted_trend_minus_past_trend
  selected_abs_predicted_last_delta_from_past_last_over_std
  selected_abs_predicted_mean_delta_from_past_last_over_std
  selected_minus_fallback_abs_predicted_trend_minus_past_trend
  selected_minus_fallback_abs_predicted_last_delta_from_past_last_over_std
```

## 4. What Is Regularization?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不让模型太相信某个线索 | penalize large weights | ridge L2 |
| 防止记住偶然规律 | reduce overfitting | validation transfer |
| 太强会变迟钝 | underfitting | robust-pass collapse |
| 正则不是魔法 | not a substitute for signal | strong L2 failed |

通俗解释：

```text
regularization 就像给模型加一个刹车：

  不要因为某个特征在训练里看起来很有用，
  就把它的权重拉得特别大。

刹车太弱：

  模型容易过拟合。

刹车太强：

  模型什么都不敢做。
```

专业解释：

```text
L2 regularization adds a penalty proportional to squared model weights. In ridge
regression, larger L2 values shrink feature weights toward zero. This can
improve generalization when the model is overfitting, but it can also remove
useful signal.
```

项目对应：

```text
default l2 grid:
  0.0, 0.001, 0.01, 0.1, 1.0

strong l2 grid:
  1, 10, 100, 1000
```

## 5. Strict Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 还是不能晋级 | no strict candidate | strict_positive = 0 |
| no-series 变少了 | fewer loose positives | robust_pass 16 -> 10 |
| include-series 变多了 | more loose positives | robust_pass 6 -> 11 |
| 但都没过最终门槛 | no promotion | final locked in strict |

通俗解释：

```text
compact 后，
结果不是纯好也不是纯坏。

no-series:
  loose candidate 变少。

include-series:
  loose candidate 变多。

但最重要的 strict candidate 仍然是 0。

所以：

  不能发布。
  不能说 compact 成功。
```

专业解释：

```text
`alignment-compact` changes the loose validation distribution but does not
produce any candidate with zero fold metric regressions. Therefore strict mode
fails closed and final holdout is not evaluated for promotion.
```

项目对应：

```text
alignment-compact no-series:
  robust_pass: 10
  strict_positive: 0

alignment-compact include-series:
  robust_pass: 11
  strict_positive: 0
```

## 6. Robust Diagnostic Result

| Surface | Include series | Final metric delta | Final relative lift | Final negative series |
|---|---:|---:|---:|---:|
| base | no | +0.0002280509 | +0.0009678327 | 1 |
| alignment-risk | no | +0.0001021934 | -0.0003618867 | 2 |
| alignment-compact | no | +0.0001788929 | +0.0004484648 | 1 |
| base | yes | +0.0001617361 | +0.0002671987 | 1 |
| alignment-risk | yes | +0.0001575894 | +0.0002233868 | 1 |
| alignment-compact | yes | +0.0001521865 | +0.0001663039 | 2 |

通俗解释：

```text
robust diagnostic 不是发布证据。
它只是告诉我们：

  这个方向有没有继续研究价值？

compact no-series 比 raw alignment-risk no-series 好。
但它还是没有 base 好。

compact include-series 更差一点，
还把 final negative series 从 1 变成 2。
```

专业解释：

```text
Robust final diagnostics show that feature compression partially recovers
no-series performance, but it does not beat the base surface. Include-series
compact alignment worsens downside relative to both base and raw alignment-risk.
```

项目对应：

```text
best robust final among compared surfaces:
  base no-series

compact status:
  diagnostic only
  not promotion-ready
```

## 7. Strong L2 Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 刹车太强，车不走了 | over-regularization | robust-pass collapse |
| no-series 只剩 1 个 loose candidate | signal suppressed | robust_pass = 1 |
| include-series 直接 0 | no useful exposure | robust_pass = 0 |
| strict 仍然 0 | blocker unchanged | strict_positive = 0 |

通俗解释：

```text
我们试了更强 L2：

  1
  10
  100
  1000

如果问题只是过拟合，
更强 L2 应该让结果更稳。

但结果相反：

  候选几乎被压没了。
  strict 仍然过不了。
```

专业解释：

```text
The strong-L2 grid falsifies the simple overfitting hypothesis. Larger ridge
penalties reduce candidate exposure and do not eliminate fold regressions.
```

项目对应：

```text
alignment-compact strong L2 no-series:
  robust_pass: 1
  strict_positive: 0

alignment-compact strong L2 include-series:
  robust_pass: 0
  strict_positive: 0
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 项目不是只调 adapter 权重 | system-level specialization | adapter + router |
| 特征多不一定强 | representation tradeoff | alignment-risk vs compact |
| 正则强不一定稳 | bias-variance tradeoff | strong L2 failed |
| 失败定位比盲调更重要 | attribution-driven research | cut4000 blocker |

通俗解释：

```text
如果你只看表面，
会觉得：

  多加特征。
  多加正则。
  再试试。

但真正的训练流程不是这样。

我们现在学到的是：

  alignment 有信号。
  但 expected-regret ridge 这个形式处理不好 cut4000。
  继续加 alignment 特征或加 L2，收益很小。

所以要换问题。
```

专业解释：

```text
This is a representation and regularization ablation. It shows that the current
expected-regret ridge veto is not merely under-regularized. The remaining
failure is localized to fold-specific veto errors, so the next model change
should target abstention or veto calibration rather than more alignment inputs.
```

项目对应：

```text
remaining blocker:
  cut4000 fold regression

main harmful patterns:
  no-series: DFF / recent1500
  include-series: VIXCLS / zero-shot
```

## 9. Next Round

Recommendation:

```text
Stop adding alignment feature columns in the current expected-regret ridge form.

Next useful tests:

1. abstention-aware veto:
   learn when not to veto, even if expected regret looks positive.

2. fold-conditioned risk guard:
   detect cut4000-like contexts from no-leak runtime features.

3. calibration target:
   predict probability that veto helps, but penalize false-positive vetoes more
   heavily than missed vetoes.
```

Success target remains:

```text
strict_positive > 0
fold_metric_regressions = 0
final holdout evaluated only after strict pass
```
