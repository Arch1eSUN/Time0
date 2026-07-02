# 059 - Supervised Router Transfer

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-supervised-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再手写 if 规则 | supervised policy | KNN-regret veto |
| 用历史错误当训练答案 | observed regret label | `regret_vs_fallback` |
| 找相似历史窗口 | nearest-neighbor model | `k=25` |
| 判断要不要退回 fallback | fallback-veto classifier | `recent2000` |

通俗解释：

```text
前几轮我们一直在手写规则：

  如果某个特征大于阈值，就退回 fallback。
  如果两个条件同时满足，就退回 fallback。
  如果很多规则投票够多，就退回 fallback。

这轮开始换方向：

  不靠人手写判断边界。
  让历史数据告诉我们：
  哪些 override 最后是错的？
  哪些 override 最后是对的？

然后当前窗口来了以后，
去找过去最像它的窗口，
看过去这些类似情况里 fallback 是不是更好。
```

专业解释：

```text
This run evaluates a supervised fallback-veto router. The training examples are
historical override windows with observed regret labels. At evaluation time, a
KNN-regret model estimates whether the current selected adapter is likely to be
worse than the fixed fallback.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_supervised_veto.py

default report:
  reports/router-supervised-veto-multifold-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

series-aware sensitivity:
  reports/router-supervised-veto-multifold-validation-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Supervised Learning?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给模型题目和答案 | labeled training | features + regret |
| 题目是当时能看到的信息 | no-leak features | runtime feature matrix |
| 答案是事后谁更准 | realized label | adapter vs fallback error |
| 学的是判断边界 | decision boundary | fallback-veto policy |

通俗解释：

```text
监督学习就是：

  给模型很多例题。

每道题都有：

  输入：当时能看到什么。
  答案：后来证明哪个选择更好。

比如：

  输入：
    这个窗口的历史波动、趋势、adapter 预测形状。

  答案：
    router 选的 adapter 比 fallback 差。

模型学到的不是“未来答案”，
而是：

  哪些当时可见的迹象，
  经常意味着这个 adapter override 会错。
```

专业解释：

```text
Supervised learning estimates a mapping from observable features to labels. In
this router experiment, the label is realized regret versus fallback. The
feature contract must be no-leak: it can use only information available at the
forecast decision time.
```

项目对应：

```text
input feature:
  no-leak runtime features
  selected adapter one-hot

label:
  selected_adapter_error - recent2000_error

positive label:
  fallback was better

negative label:
  selected adapter was better
```

## 3. What Is Regret?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 后悔值 | regret | `regret_vs_fallback` |
| 选错越多，后悔越大 | error difference | selected error minus fallback error |
| 正数说明该退回 fallback | fallback better | veto target |
| 负数说明 override 是对的 | adapter better | keep selected adapter |

通俗解释：

```text
regret 可以理解成：

  如果当时我不这么选，
  会不会更好？

在这里：

  router 选了某个 LoRA adapter。
  我们事后拿真实结果对比。

如果：

  adapter error > fallback error

说明：

  这个 override 是错的。
  当时应该退回 fallback。
```

专业解释：

```text
Regret is the excess error of the selected action relative to a reference
action. Here the reference action is fixed `recent2000`. Positive regret means
the selected adapter underperformed fallback.
```

项目对应：

```text
regret_vs_fallback = selected_adapter_error - fallback_error

if regret_vs_fallback > 0:
  fallback would have been better
```

## 4. What Is KNN-Regret?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 找相似案例 | k-nearest neighbors | `k` |
| 看相似案例平均后悔值 | local regret estimate | `mean_neighbor_regret` |
| 后悔值超过阈值就拦截 | thresholded local risk | `regret_threshold` |
| 它不是深度模型 | non-parametric model | numpy distance search |

通俗解释：

```text
KNN 的想法很直：

  当前窗口来了。
  我去历史里找最像它的 25 个窗口。
  看那 25 个窗口当时 override 有没有错。

如果那些相似窗口平均来看都很后悔，
那当前这个 override 也危险。

于是退回 fallback。
```

专业解释：

```text
KNN-regret is a non-parametric local estimator. It does not train neural
weights. It stores historical labeled examples, computes distances in feature
space, averages neighbor regret, and applies a threshold.
```

项目对应：

```text
selected config:
  k: 25
  regret_threshold: 0.001

decision:
  if mean_neighbor_regret > 0.001:
    veto to recent2000
```

## 5. Why This Is Still Connected To LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 是专家 | specialized predictor | recent adapters |
| router 是调度员 | selection policy | adapter router |
| 监督 router 学谁该出场 | learned adapter selection | regret model |
| 训练 router 也是专精系统的一部分 | post-adapter specialization | LoRA + policy |

通俗解释：

```text
这轮没有继续改 LoRA 权重。

但它仍然是 LoRA 项目的一部分。

因为最终系统不是只有一个 adapter：

  TimesFM base
  LoRA adapter A
  LoRA adapter B
  fallback
  router

如果 adapter 是专家，
router 就是调度员。

专家训练好了，
调度员不会调度，
系统还是不强。
```

专业解释：

```text
Adapter specialization and adapter selection are separate but coupled
interfaces. LoRA changes candidate prediction functions. The router chooses
among those functions. A learned router can improve or destroy the value of
specialized adapters.
```

项目对应：

```text
adapter layer:
  TimesFM + LoRA checkpoints

router layer:
  learned fallback-veto policy

current experiment:
  train router behavior from prediction-level archives
```

## 6. What Happened In The No-Series Run

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| validation 看起来能学到 | validation-positive signal | 6 positive candidates |
| 但正式 holdout 挂了 | final transfer failure | metric delta negative |
| 负收益 series 没变 | downside neutral | `2 -> 2` |
| 不能发布 | not promotable | final hurts split |

通俗解释：

```text
默认 no-series 跑法是最干净的：

  不告诉模型 series_id。
  只让它看通用 no-leak 特征。

结果很有意思：

  validation 里有 5 个 robust-pass。
  selected config 在 validation 上是正的。

但是 final holdout 里：

  它让 MAE 变差。

这说明：

  它学到了一点局部规律，
  但这个规律没有稳定跨到最后一段市场。
```

专业解释：

```text
The no-series KNN-regret model passes the existing validation gate but fails
final holdout. This is a validation-to-final transfer failure. It suggests the
current validation gate is still too permissive for supervised router release.
```

项目对应：

```text
default no-series:
  validation_robust_pass_count: 5
  validation_positive_count: 6
  validation_strict_positive_count: 0
  selected combined_metric_delta: +0.0004494389
  final_metric_delta: -0.0000276801
  final_negative_series: 2 -> 2
  verdict: not_promotable
```

## 7. Why `validation_strict_positive_count=0` Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 表面过关不等于每折都好 | combined vs fold robustness | fold regressions |
| 总分正可能掩盖局部倒退 | aggregate masking | `fold_metric_regressions` |
| 严格计数要求每折都不倒退 | stricter fold gate | strict positive |
| 当前没有一个候选满足 | no strict candidate | count 0 |

通俗解释：

```text
validation combined 是把几段 validation 合起来看。

问题是：

  合起来是正的，
  不代表每一段都是正的。

这轮 selected config 的 validation combined 很好，
但它有 2 个 fold 的 metric regression。

也就是说：

  三场模拟考里，
  总分看起来不错，
  但有两场其实考差了。

这就是为什么我们新增了：

  validation_strict_positive_count

结果是 0。
```

专业解释：

```text
`validation_strict_positive_count` requires positive combined metric delta,
non-increasing combined downside, no fold downside regression, no fold metric
regression, and no fold exposure failure. The current supervised candidate set
has no such candidate.
```

项目对应：

```text
legacy validation-positive:
  combined_metric_delta > 0
  combined_negative_series_delta <= 0
  fold_negative_regressions == 0

strict validation-positive:
  above conditions
  plus fold_metric_regressions == 0
  plus fold_no_exposure <= max_fold_no_exposure
```

## 8. What Happened In The Series-Aware Sensitivity

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 告诉模型是哪条 series | include series identity | `--include-series` |
| final 变好一点 | final-only positive | `+0.0000228784` |
| validation 不支持 | no validation pass | 0 positive candidates |
| 仍不能发布 | diagnostic only | below fallback |

通俗解释：

```text
series-aware 版本把 series_id 也给模型。

它在 final holdout 里变好了一点。

但问题是：

  validation robust-pass = 0
  validation positive = 0

这说明：

  它最后那段好，
  但中间验证段不支持它。

所以它和上一轮 score-vote 一样：

  有信号，
  不是证据。
```

专业解释：

```text
The series-aware sensitivity produces a small final holdout gain, but the
validation gate rejects the candidate class. Since series identity can
encourage memorization, this result should remain diagnostic.
```

项目对应：

```text
series-aware:
  validation_robust_pass_count: 0
  validation_positive_count: 0
  validation_strict_positive_count: 0
  final_metric_delta: +0.0000228784
  final_negative_series: 2 -> 2
  verdict: incremental_positive_but_below_fallback
```

## 9. What We Learned

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 监督 router 比手写规则更接近正路 | learned policy is the right seam | KNN-regret |
| 但现在还不稳 | regime transfer failure | final hurt |
| 旧 gate 太宽松 | validation gate insufficiency | strict count 0 |
| 下一步要更严格或更校准 | calibrated supervised router | probability + downside |

通俗解释：

```text
这轮不是坏消息。

它告诉我们：

  router 确实能从历史错误里学到一点东西。

但也告诉我们：

  现在这种简单 KNN-regret 还不够。

最重要的新发现是：

  只看 validation combined 不够。

我们需要更严格地看：

  每个 validation fold 是否都不倒退。
```

专业解释：

```text
The supervised router direction is valid as a seam, but this implementation is
not a release candidate. The failure mode is transfer stability, not absence of
signal. A stricter validation gate or calibrated probabilistic router is needed
before further promotion.
```

项目对应：

```text
current status:
  learned router signal exists
  no publishable supervised policy yet

next gate change:
  require validation_strict_positive_count > 0 before final promotion
```

## 10. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再只找 combined validation 好的 | stricter fold-level gate | strict validation |
| 让模型输出概率而不是硬阈值 | calibrated probability | fallback risk score |
| 把 downside 放进训练目标 | downside-aware objective | per-series guard |
| 继续保持 no-leak | causal feature contract | no future labels |

通俗解释：

```text
下一轮应该做的不是：

  再随便调几个 k 和 threshold。

而是：

  先把 gate 收紧。
  再训练一个能输出概率的 router。

比如：

  这个 override 有 72% 概率比 fallback 差。

然后再结合：

  这条 series 最近是不是已经容易亏？
  这个 adapter 在这类 regime 里是否稳定？
```

专业解释：

```text
The next experiment should either make the multi-fold gate stricter before
model selection, or replace KNN-regret with a calibrated supervised router that
optimizes fallback-veto probability and downside-aware selection under the same
no-leak feature contract.
```

项目对应：

```text
candidate next script:
  validate_multifold_calibrated_supervised_veto.py

must keep:
  discovery/train split
  validation folds
  final holdout once
  no target leakage
  per-series downside reporting
```
