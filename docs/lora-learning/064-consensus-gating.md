# 064 - Consensus Gating

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-consensus-regret-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不让一个模型单独决定 | ensemble decision | multiple regret models |
| 多个模型同意才 veto | consensus gate | `consensus_min_models` |
| 每个模型看不同历史前缀 | temporal-prefix training | cuts 3000, 3250, 3500 |
| strict gate 仍然不放松 | fail-closed promotion | final untouched |

通俗解释：

```text
上一轮 utility score 告诉我们：

  很多候选平均收益好看，
  但风险太贵。

这一轮我们试一个更保守的办法：

  不让一个模型单独决定是否退回 fallback。
  训练多个模型。
  只有多个模型都觉得该退，
  才真的退。

这叫 consensus gating。
```

专业解释：

```text
This run adds a temporal-prefix consensus gate to expected-regret routing.
Instead of one regression model making the veto decision, multiple models are
trained on chronological discovery prefixes. An override is vetoed only when
the number of models predicting regret above threshold reaches the configured
minimum.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_expected_regret_veto.py

new args:
  --consensus-mode temporal-prefix
  --consensus-min-models 2
  --consensus-min-models 3
```

## 2. What Is An Ensemble?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 多个模型一起判断 | ensemble | multiple models |
| 一个模型可能偏 | single-model variance | one regret boundary |
| 多个模型可互相制衡 | variance reduction | consensus |
| 但它们必须真的不同 | diversity requirement | temporal prefixes |

通俗解释：

```text
一个模型像一个分析师。

一个分析师可能看错。

所以我们找多个分析师：

  A 说该退回 fallback。
  B 也说该退回 fallback。
  C 也说该退回 fallback。

那我们更相信这个决定。

但注意：

  如果 A、B、C 都看的是同一套信息，
  学到的是同一个偏见，
  那他们一起同意也没用。
```

专业解释：

```text
An ensemble reduces variance only when member models have useful diversity.
If all members share the same features, labels, and highly overlapping data,
their errors can be correlated. In that case consensus does not remove the
failure mode.
```

项目对应：

```text
members:
  model trained on cut <= 3000
  model trained on cut <= 3250
  model trained on cut <= 3500
```

## 3. What Is Temporal-Prefix Consensus?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先看早期历史 | first prefix | cut <= 3000 |
| 再看更多历史 | second prefix | cut <= 3250 |
| 最后看完整 discovery | third prefix | cut <= 3500 |
| 三个模型投票 | vote count | regret above threshold |

通俗解释：

```text
我们不是随机复制三个模型。

我们按时间切三段训练：

  模型 1:
    只看最早的 discovery。

  模型 2:
    看更长一点的 discovery。

  模型 3:
    看完整 discovery。

如果一个 window 只有模型 3 觉得危险，
模型 1 和模型 2 不觉得危险，
那我们就更谨慎。
```

专业解释：

```text
Temporal-prefix consensus trains deterministic chronological-prefix models.
The aim is to filter decisions that depend only on late discovery behavior and
do not appear in earlier discovery prefixes.
```

项目对应：

```text
consensus_min_models:
  2 means at least 2 prefix models must vote fallback
  3 means all 3 prefix models must vote fallback
```

## 4. Why We Tried This

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| blocker 是时间折倒退 | chronological instability | fold regressions |
| consensus 可能减少偶然判断 | reduce variance | agreement filter |
| 目标不是提高平均收益 | not raw lift chasing | strict gate |
| 目标是减少 fold regression | stability target | strict positive |

通俗解释：

```text
我们现在最大的问题不是：

  完全没有收益信号。

我们的问题是：

  某些时间段有收益。
  换一个时间段又倒退。

所以 consensus 的目的不是让平均收益更大。

它的目的是：

  少做不稳定的选择。
  减少 fold regression。
```

专业解释：

```text
The active failure mode is chronological transfer instability. Consensus gating
is a variance-control experiment: it tests whether requiring agreement across
training prefixes removes fold-level regressions.
```

项目对应：

```text
success condition:
  validation_strict_positive_count > 0

not enough:
  validation_positive_count > 0
```

## 5. What Happened

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| no-series 没突破 | no strict candidate | strict 0 |
| series-aware 也没突破 | no strict candidate | strict 0 |
| 2票和3票几乎一样 | consensus not discriminative | same aggregate counts |
| final 仍然没动 | holdout protected | final false |

通俗解释：

```text
结果很直接：

no-series:
  strict positive = 0

series-aware:
  strict positive = 0

而且：

  要 2 个模型同意，
  和要 3 个模型同意，
  统计结果一样。

这说明多个 prefix 模型没有真正产生有用分歧。
它们基本在同一批地方犯类似判断。
```

专业解释：

```text
Temporal-prefix consensus did not improve the promotion surface. It duplicated
the existing loose-positive pattern and did not reduce fold metric regressions
to zero.
```

项目对应：

```text
no-series:
  validation_candidate_count: 210
  validation_positive_count: 28
  validation_utility_positive_count: 10
  validation_strict_positive_count: 0

series-aware:
  validation_candidate_count: 210
  validation_positive_count: 14
  validation_utility_positive_count: 0
  validation_strict_positive_count: 0
```

## 6. Why Consensus Failed Here

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型数量变多了 | more models | ensemble size |
| 但信息没有变多 | same feature surface | same no-leak rows |
| 错误高度相关 | correlated errors | same fold blocker |
| 所以投票没过滤风险 | no variance gain | strict still 0 |

通俗解释：

```text
三个模型一起投票听起来更稳。

但如果三个模型看到的信息差不多，
学到的规律也差不多，
那它们会一起犯错。

这就像：

  三个人都只读了同一本错误地图。
  他们一起同意，
  也不代表路是对的。
```

专业解释：

```text
Consensus requires model diversity. Temporal prefixes were not diverse enough
because they shared the same feature space, same target definition, and nested
training data. The resulting errors remained correlated.
```

项目对应：

```text
same surface:
  alignment-normalized features
  expected-regret target
  same adapter/fallback candidates

unchanged blocker:
  fold_metric_regressions
```

## 7. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 叠 gate 不能无限解决问题 | post-hoc gating limit | consensus fail |
| adapter/router 需要新信息 | feature bottleneck | no-leak feature gap |
| ensemble 不等于泛化 | correlated ensemble risk | prefix models agree |
| 下一步要换信息面 | change input surface | richer regime features |

通俗解释：

```text
到这里我们学到一个重要点：

  不要以为加更多 gate，
  模型就一定更可靠。

如果输入信息不够，
后面的 gate 只是在同一堆信息上反复筛。

真正要突破，
可能需要新的 no-leak 特征，
或者新的数据切法，
让 router 看到之前看不到的 regime 差异。
```

专业解释：

```text
LoRA specialization needs a selector with enough information to identify when
the adapter transfers. If the router feature surface cannot separate stable
from unstable overrides, ensembling the same surface will not fix promotion.
```

项目对应：

```text
status:
  consensus diagnostic negative
  final holdout protected

next leverage:
  feature surface, not more post-hoc gates
```

## 8. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 停止叠加同类 gate | stop post-hoc gating loop | no more consensus tuning |
| 找新 no-leak 特征 | feature search | regime separability |
| 针对 fold regression 做诊断 | failure localization | bad fold analysis |
| 看哪一折在伤害 | fold attribution | cut-level error source |

通俗解释：

```text
下一轮不应该继续：

  consensus_min_models 调 1、2、3、4。
  penalty 再调来调去。
  threshold 再调更细。

下一轮应该做：

  找出到底是哪一个 validation fold 在倒退。
  看倒退集中在哪些 series、family、runtime feature。
  再决定要加什么 no-leak 特征。
```

专业解释：

```text
The next experiment should be fold-regression attribution: localize which
validation folds, series, selected families, and runtime features produce the
remaining metric regressions. That has higher leverage than another gate on the
same expected-regret surface.
```

项目对应：

```text
candidate next script:
  diagnose_expected_regret_fold_regressions.py

goal:
  identify the feature/data gap causing fold_metric_regressions
```
