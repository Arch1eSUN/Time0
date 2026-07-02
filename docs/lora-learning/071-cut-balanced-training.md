# 071 - Cut-Balanced Training

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-cut-balanced-training-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不让一个时间切片支配训练 | cut-balanced training | `--training-weighting cut-label-balanced` |
| 每个 cut 给相近权重 | equal cut mass | discovery cut weights |
| cut 内再平衡正负标签 | label-balanced within cut | fallback-better vs selected-better |
| 这次改训练，不是只改排序 | training-time weighting | logistic loss weights |

通俗解释：

```text
上一轮 worst-fold selection 只是改“挑哪个候选”。

这轮我们往训练里动一点：

  训练 logistic veto 时，
  不让某一个时间 cut 的样本太强势。

直觉是：

  如果模型从训练阶段就看到更平衡的时间块，
  它可能更不容易只适应某一段历史。
```

专业解释：

```text
This run adds a sample-weighting mode for logistic fallback-veto training.
Instead of balancing labels globally, `cut-label-balanced` first assigns equal
mass to each training cut, then balances labels inside each cut.
```

项目对应：

```bash
--training-weighting cut-label-balanced
```

## 2. The Important Structural Surprise

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| discovery 只有一个 cut | single-cut discovery split | cut3500 only |
| 所以 cut 平衡没东西可平衡 | no temporal groups at selection time | one group |
| validation 候选不会变 | candidate surface unchanged | same strict/robust counts |
| final retrain 才会变 | final training has multiple cuts | cut3500/3750/4000/4250 |

通俗解释：

```text
这是这轮最关键的发现。

我们想让训练更懂不同时间 cut。

但 validation selection 阶段的 discovery training 只有一个 cut：

  cut3500

只有一个 cut，就没法做“cut 之间平衡”。

这就像你说：

  我要让每个班级权重一样。

结果学校里现在只有一个班。

那这个规则不会改变任何东西。
```

专业解释：

```text
The validation-selection training split contains only cut3500. Therefore
cut-level balancing is equivalent to label balancing for validation candidate
selection. It only changes the final retrain path, where the training set
contains cuts 3500, 3750, 4000, and 4250.
```

项目对应：

```text
discovery examples:
  cut3500:
    fallback_better: 210
    selected_better: 232

final_train examples:
  cut3500: fallback_better 210, selected_better 232
  cut3750: fallback_better 141, selected_better 132
  cut4000: fallback_better 68, selected_better 90
  cut4250: fallback_better 82, selected_better 67
```

## 3. What Happened

| Surface | Gate | Objective | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---|
| no-series | strict | combined | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 0 | 53 | -0.0000121668 | not_promotable |
| no-series | robust | worst-fold | 0 | 15 | -0.0000299353 | not_promotable |
| include-series | strict | combined | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 0 | 0 | +0.0000000000 | not_validated_no_future_exposure |

通俗解释：

```text
结果很直接：

  strict 还是 0。
  no-series robust final 变负。
  worst-fold robust final 更负。
  include-series 还是没有未来曝光。

所以 cut-balanced training 这条路，
在当前切分方式下没有带来提升。
```

专业解释：

```text
Cut-balanced training does not create strict-positive candidates. The selected
robust no-series validation candidate is unchanged in validation shape, but
final retraining with cut-balanced weights produces negative holdout delta.
```

项目对应：

```text
combined robust:
  final_changed_windows: 53
  final_metric_delta: -0.0000121668

worst-fold robust:
  final_changed_windows: 15
  final_metric_delta: -0.0000299353
```

## 4. Why Validation Did Not Move But Final Did

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| validation 训练只有 cut3500 | single training group | discovery split |
| cut balance 等于没生效 | degenerate balancing | one cut |
| final 训练有多个 cut | multiple groups | final_train split |
| 所以 final 模型边界变了 | retrained model changed | final holdout |

通俗解释：

```text
这点很容易混：

  validation 阶段：
    训练数据只有 cut3500。
    cut-balanced 没有真正发挥作用。

  final 阶段：
    训练数据包含 cut3500、3750、4000、4250。
    cut-balanced 开始发挥作用。

但发挥作用以后，final 变差。
```

专业解释：

```text
The selected config is chosen using discovery-only training. Because discovery
has one cut, cut balancing does not change candidate validation scores. The
final holdout model is retrained on a larger pre-final set with multiple cuts,
so the same config can produce different final behavior.
```

项目对应：

```text
previous global final_delta:
  +0.0000070437

cut-balanced final_delta:
  -0.0000121668
```

## 5. What This Teaches About LoRA Work

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练方法要匹配数据切分 | objective depends on split design | discovery has one cut |
| 好想法也可能没施力点 | no leverage without groups | cut balancing degenerates |
| final retrain 也要被验证 | retrain distribution shift | final_train differs |
| 不能只看参数名很高级 | mechanism over label | empirical check |

通俗解释：

```text
你要记住：

  不是每个听起来高级的训练技巧都有用。

它必须真的作用在数据结构上。

如果你说“按时间块平衡”，
但训练数据里只有一个时间块，
那它不会帮助模型学跨时间稳定性。
```

专业解释：

```text
An objective only has leverage if the training split exposes the variation it
tries to control. Here, fold consistency cannot be learned from cut-level
balancing during validation selection because discovery has no cut diversity.
```

项目对应：

```text
failed hypothesis:
  cut-level balancing can improve fold consistency

reason:
  validation-selection training split has only cut3500
```

## 6. Next Round

Recommendation:

```text
Keep:
  training_weighting option
  discovery/final_train cut summaries

Do not promote:
  cut-label-balanced combined robust
  cut-label-balanced worst-fold robust
  include-series cut-balanced

Next experiment:
  add no-leak time-bin-label-balanced training inside discovery cut3500
```
