# 070 - Worst-Fold Selection

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-worst-fold-selection-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看总分 | avoid combined-only selection | `selection_objective` |
| 看最差那一折 | worst-fold utility | `min_fold_metric_delta` |
| 先保护最弱时间段 | chronological robustness | validation folds |
| 这轮只改排序，不改训练 | ranking-only diagnostic | same logistic labels |

通俗解释：

```text
上一轮我们发现：

  有一个 robust candidate。
  它 final 小赢。
  但三个 validation folds 里有两个折亏。

所以这轮问一个问题：

  如果不优先选总分最高的候选，
  而是优先选“最差一折没那么差”的候选，
  会不会更稳？
```

专业解释：

```text
This run adds a selection objective that ranks robust validation candidates by
their weakest chronological fold. It does not change logistic training,
features, labels, or prediction data.
```

项目对应：

```bash
--selection-objective worst-fold
```

## 2. What Is A Fold?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一段历史时间考试 | chronological validation split | `cut3750`, `cut4000`, `cut4250` |
| 不能把所有时间混成一锅 | avoid pooled overclaiming | fold reports |
| 每一折都代表一种未来感 | temporal transfer check | rolling validation |
| 折内亏损说明不稳定 | fold regression | `fold_metric_regressions` |

通俗解释：

```text
我们不是随机切数据。

金融时间序列不能随便打乱。

我们按时间切：

  cut3750
  cut4000
  cut4250

每一折都像一次“模拟未来”。

如果模型只在其中一折很好，
但另外两折亏，
那它不是稳定强。
```

专业解释：

```text
A fold is one chronological validation slice. Fold-level evaluation prevents a
candidate from looking good only because a large positive later split hides
earlier temporal regressions.
```

项目对应：

```text
validation folds:
  validation_cut3750
  validation_cut4000
  validation_cut4250
```

## 3. What Is Worst-Fold Selection?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先看最差成绩 | maximize weakest fold | `min_fold_metric_delta` |
| 不让一个大胜掩盖两个小亏 | reduce aggregate masking | fold deltas |
| 这是一种保守排序 | robust ranking objective | worst-fold key |
| 它不是新的 LoRA 训练 | post-hoc candidate selection | no adapter retrain |

通俗解释：

```text
普通 combined selection 像这样：

  第一折亏一点。
  第二折亏很多。
  第三折赚很多。
  总分还是正的。

它可能会说：

  选它。

worst-fold selection 会先问：

  最差那一折到底有多差？

如果最差那一折太差，
就算总分高，也要降级。
```

专业解释：

```text
Worst-fold selection changes the ranking key. Among validation-positive or
robust candidates, it prioritizes the maximum value of `min_fold_metric_delta`
before combined validation lift.
```

项目对应：

```text
combined objective:
  rank mostly by combined_metric_delta

worst-fold objective:
  rank by min_fold_metric_delta before combined_metric_delta
```

## 4. What Changed In Code

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 新增选择目标 | selection objective switch | `--selection-objective` |
| 默认保持旧逻辑 | backward-compatible default | `combined` |
| 报告每折 delta | fold metric diagnostics | `fold_metric_deltas` |
| 报告最差折 | weakest-fold metric | `min_fold_metric_delta` |

通俗解释：

```text
这次没有重新训练 TimesFM。

也没有重新训练 LoRA adapter。

也没有改数据。

我们只是改：

  在一堆候选 router 规则里，
  到底优先挑哪一个。
```

专业解释：

```text
The script now stores fold metric deltas in the validation summary and supports
a ranking objective. The `combined` objective preserves the previous behavior.
The `worst-fold` objective changes robust candidate ordering.
```

项目对应：

```text
new report fields:
  fold_metric_deltas
  min_fold_metric_delta
  mean_fold_metric_delta

new CLI:
  --selection-objective combined
  --selection-objective worst-fold
```

## 5. What Happened

| Objective | Fold regressions | Worst fold | Validation changed | Final changed | Final delta |
|---|---:|---:|---:|---:|---:|
| combined | 2 | -0.0003655074 | 144 | 52 | +0.0000070437 |
| worst-fold | 1 | -0.0000696377 | 45 | 14 | -0.0000146476 |

通俗解释：

```text
worst-fold selection 确实让 validation 看起来更稳：

  折内亏损从 2 个变成 1 个。
  最差那一折亏得没那么严重。

但是 final 变差了：

  final 只改 14 个窗口。
  final metric delta 变成负数。
```

专业解释：

```text
Worst-fold ranking improved validation fold shape but reduced intervention
mass and failed final holdout. This suggests that post-hoc ranking alone does
not solve transfer instability.
```

项目对应：

```text
selected worst-fold config:
  l2: 0.1
  probability_threshold: 0.5
  false_positive_weight: 2.0

final:
  changed_windows: 14
  metric_delta: -0.0000146476
  verdict: rule_hurts_split
```

## 6. Why This Failed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只是换了挑选方式 | ranking-only intervention | same trained model |
| 模型本身没学会折间一致 | objective mismatch | pooled labels |
| 挑保守规则会减少出手 | lower exposure | 45 validation changes |
| final 还是不买账 | failed transfer | negative holdout delta |

通俗解释：

```text
这轮像是在一堆学生里换选拔标准：

  以前选总分最高。
  现在选最差科目没那么差。

这会改变被选中的人。

但它不会改变学生本身学会了什么。

我们的 logistic model 也是一样：

  它训练时还是学 fallback 是否更好。
  它没有被训练成“每个时间折都要稳”。
```

专业解释：

```text
The training target remains pooled fallback-better classification. The
selection objective can prefer a fold-safer candidate, but it cannot reshape
the classifier boundary toward fold consistency.
```

项目对应：

```text
training target:
  fallback_better_probability_with_false_positive_penalty

selection objective:
  worst-fold

failure:
  final_metric_delta < 0
```

## 7. Ranking Objective vs Training Objective

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 排名是挑哪个模型 | selection/ranking objective | `ranked_validation_scores` |
| 训练是模型怎么学 | training objective | logistic loss |
| 排名不能替代学习 | post-hoc choice is limited | failed final |
| 下一步要改学习目标 | fold-aware learning | future target |

通俗解释：

```text
这轮你要记住一个核心区别：

  ranking objective:
    已经训练完了，从候选里挑一个。

  training objective:
    训练过程中告诉模型什么错更严重。

如果模型没学会某种规律，
光靠后面排序，最多只能挑一个没那么坏的。

但不一定能挑出真正好的。
```

专业解释：

```text
A selection objective operates after candidate generation. A training objective
changes gradients and therefore changes the candidate set itself. The result
indicates that fold consistency likely needs to enter training or sample
weighting, not only validation ranking.
```

项目对应：

```text
current change:
  ranked_validation_scores(..., selection_objective="worst-fold")

not changed:
  labels_from_examples
  false_positive_sample_weights
  train_logistic_model
```

## 8. Current Project Meaning

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| no-series 仍比 include-series 值得继续 | better future exposure | include-series final changed = 0 |
| strict 仍然正确拒绝 | fail-closed gate works | strict_positive = 0 |
| robust 只是诊断 | not promotion evidence | `not_promotable` |
| 失败原因更精确了 | objective mismatch localized | fold-aware target needed |

通俗解释：

```text
这轮不是白跑。

它告诉我们：

  问题不只是“选错候选”。

因为我们已经换了更保守的选择方式，
final 还是失败。

所以更可能的问题是：

  训练目标本身没有把“跨时间折稳定”学进去。
```

专业解释：

```text
The ranking diagnostic falsifies the hypothesis that candidate ordering alone
is the blocker. The remaining blocker is an objective mismatch between pooled
fallback-better training and fold-consistent promotion.
```

项目对应：

```text
hypothesis tested:
  worst-fold ranking can fix robust selection

result:
  rejected

next hypothesis:
  fold-consistency-aware training can create better candidates
```

## 9. Next Round

Recommendation:

```text
Keep:
  minimum exposure gate
  fold metric delta reporting
  worst-fold objective as a diagnostic option

Do not promote:
  worst-fold robust no-series
  include-series robust

Next experiment:
  add fold-consistency-aware sample weighting or objective
```

Success target:

```text
strict_positive > 0
exposure_pass = true
fold_metric_regressions = 0
fold_negative_regressions = 0
final_changed_windows is not tiny
final_metric_delta > 0
final_relative_lift_vs_fallback > 0
```
