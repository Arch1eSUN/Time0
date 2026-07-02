# 077 - Compact Alignment Logistic Surface

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-alignment-compact-logistic-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给 router 更多可用信息 | feature surface expansion | `alignment-compact` |
| 不再只换排序 | change candidate representation | logistic input matrix |
| 仍然不偷看未来 | no-leak runtime features | prediction/context alignment |
| 继续用 abstention | two-stage policy | positive-quantile gate |

通俗解释：

```text
上一轮证明：

  只换候选排序没用。

所以这轮不再只改 selection objective。

我们给 logistic router 增加一些“预测和上下文是否对齐”的特征。

目标是让它学会：

  哪些窗口看起来像 cut3750/cut4000 里的坏情况。
```

专业解释：

```text
This run exposes `alignment-compact` as a feature surface for the logistic veto
model. It adds compact prediction/context alignment features to the base router
matrix.
```

项目对应：

```bash
--feature-surface alignment-compact
```

## 2. What Is A Feature Surface?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型能看到的输入集合 | feature surface | base / alignment-compact |
| 输入变了，模型边界会变 | representation change | logistic feature matrix |
| 不是训练更多步 | not optimization-only | same logistic model |
| 不是看答案 | no target leakage | runtime features only |

通俗解释：

```text
feature surface 就是：

  router 做决定时能看到什么信息。

如果只给它简单信息，
它可能分不清某些坏窗口。

如果给它 alignment 信息，
它可能学到：

  这个预测方向和过去上下文不一致，
  所以这个 adapter 风险更高。
```

专业解释：

```text
Changing the feature surface changes the representation, not just the ranking
or loss weight. The logistic model still learns the same target, but over a
different input matrix.
```

## 3. Why This Is No-Leak

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只用预测时已经有的信息 | runtime-available features | `runtime_features` |
| 不用未来真实误差 | no final label leakage | no final target in features |
| validation 仍然独立 | chronological validation preserved | same folds |
| final 仍然最后测试 | held-out evaluation | cut > 4250 |

通俗解释：

```text
alignment feature 不是答案。

它不是：

  这个窗口实际预测错了多少。

它是：

  模型预测形状和过去上下文之间的关系。

这些信息在真正预测时就能知道。
```

专业解释：

```text
The compact alignment surface is derived from prediction/context alignment
features already present in the router rows. It is available at routing time
and does not use validation or final holdout labels.
```

## 4. What Happened

| Surface | Feature surface | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---|
| no-series previous | base | 10 | 0 | 81 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | alignment-compact | 7 | 0 | 33 | -0.0000297337 | not_promotable |
| include-series | alignment-compact | 0 | 0 | 0 | 0.0 | not_validated_no_future_exposure |

通俗解释：

```text
结果不好。

alignment-compact 让 validation 候选变少：

  robust-pass 从 10 降到 7。

更关键的是 final：

  原来的 base surface 改 81 个窗口，final 是正的。
  compact alignment 只改 33 个窗口，final 是负的。
```

专业解释：

```text
Compact alignment improves some training fit signals but worsens final
transfer. The selected candidate loses out-of-sample exposure and produces a
negative final metric delta.
```

## 5. Selected Candidate

```text
l2: 0.1
probability_threshold: 0.6
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
feature_surface: alignment-compact
abstention_mode: positive-quantile
positive_probability_quantile: 0.5
```

Validation:

```text
combined_metric_delta: +0.0003324972
combined_changed_windows: 81
fold_metric_deltas:
  cut3750: -0.0000452110
  cut4000: -0.0000121337
  cut4250: +0.0010548362
fold_changed_windows: 44, 9, 28
fold_metric_regressions: 2
```

Final:

```text
changed_windows: 33
metric_delta: -0.0000297337
promotion_verdict: not_promotable
```

## 6. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 特征更多不一定更好 | feature expansion can overfit | alignment-compact failed |
| 训练拟合好不等于 final 好 | fit-transfer gap | Brier vs holdout |
| 保留最强 checkpoint | checkpoint discipline | base no-series abstention |
| 下一步要换目标，不是堆特征 | target/interface change | weak-fold repair |

通俗解释：

```text
这轮提醒我们：

  给模型更多输入，
  不等于模型更聪明。

如果这些输入只帮助它拟合 validation 表面，
但不能迁移到 final，
那就不是好方向。
```

专业解释：

```text
Feature-surface expansion increased representation capacity, but the current
logistic objective did not use that capacity in a way that transferred to final
holdout.
```

## 7. What We Learned

Fact: `alignment-compact` is a valid no-leak logistic feature surface.

Fact: It reduces robust candidates and turns final delta negative.

Fact: Include-series with compact alignment collapses to no final exposure.

Inference: The current blocker is not lack of alignment features in the
logistic surface. The blocker is still the training target/interface around
weak fold transfer.

Recommendation: Keep `base + no-series + positive-quantile` as the current best
diagnostic checkpoint. The next round should change the target formulation,
for example predicting fold-consistent fallback benefit instead of only
window-level fallback benefit.
