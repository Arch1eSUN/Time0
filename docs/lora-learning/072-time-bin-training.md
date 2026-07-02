# 072 - Time-Bin Training

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-time-bin-training-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 在 cut3500 里面再切时间段 | within-cut temporal bins | `start_index` bins |
| 不碰 validation folds | no-leak training pressure | discovery only |
| 每个时间 bin 平衡标签 | bin-label-balanced loss | `time-bin-label-balanced` |
| 让训练真的看到早中晚差异 | temporal diversity in training | `training_time_bins=3` |

通俗解释：

```text
上一轮的问题是：

  discovery 只有一个 cut3500。
  所以按 cut 平衡没有用。

这轮我们不再按 cut 平衡。

我们在 cut3500 内部再切成 3 段：

  early
  middle
  late

这样还是没有偷看 validation，
但训练集里面终于有了不同时间段。
```

专业解释：

```text
This run introduces `time-bin-label-balanced` sample weights. Examples are
grouped by cut and chronological `start_index` bin. Each nonempty bin receives
equal mass, then fallback-better and selected-better labels are balanced inside
that bin.
```

项目对应：

```bash
--training-weighting time-bin-label-balanced
--training-time-bins 3
```

## 2. Why This Is No-Leak

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只切训练集内部 | train-split-only grouping | discovery examples |
| 不用 validation 结果 | no validation target leakage | validation folds untouched |
| 只看 start_index | chronological metadata | row field |
| 不看未来误差 | no future labels | no final data |

通俗解释：

```text
我们没有把 validation 的输赢拿来训练。

我们只是看 discovery 里面每个样本的 start_index：

  350-366
  367-383
  384-399

然后在这些训练段里做平衡。

这仍然是 no-leak。
```

专业解释：

```text
The bin assignment is computed only from the current training examples. It uses
`start_index`, not validation metric deltas or final holdout labels.
```

项目对应：

```text
discovery cut3500 bins:
  bin0: start_index 350-366
  bin1: start_index 367-383
  bin2: start_index 384-399
```

## 3. Discovery Bin Shape

| Cut | Bin | Start index | Fallback better | Selected better |
|---:|---:|---|---:|---:|
| 3500 | 0 | 350-366 | 47 | 105 |
| 3500 | 1 | 367-383 | 73 | 72 |
| 3500 | 2 | 384-399 | 90 | 55 |

通俗解释：

```text
这个表很重要。

它说明 cut3500 里面确实有时间变化：

  早段 selected_better 多。
  中段差不多平衡。
  晚段 fallback_better 多。

所以 time-bin training 不是空操作。
它真的改变了训练权重。
```

专业解释：

```text
The discovery cut contains different label regimes across start-index bins.
This gives the weighting objective actual leverage, unlike cut-level balancing
where discovery had only one cut.
```

项目对应：

```text
discovery_example_time_bin_summary:
  cut3500/bin0: fallback 47, selected 105
  cut3500/bin1: fallback 73, selected 72
  cut3500/bin2: fallback 90, selected 55
```

## 4. What Happened

| Surface | Gate | Objective | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---|
| no-series | strict | combined | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 0 | 54 | -0.0000143517 | not_promotable |
| no-series | robust | worst-fold | 0 | 54 | -0.0000143517 | not_promotable |
| include-series | strict | combined | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 0 | 1 | +0.0000001652 | incremental_positive_but_below_fallback |

通俗解释：

```text
结果是：

  它确实改变了模型。
  但没有变好。

no-series:
  final 改了 54 个窗口。
  结果是负的。

include-series:
  final 只改了 1 个窗口。
  虽然是小正数，但证据太小。
```

专业解释：

```text
Time-bin weighting changes the candidate surface: no-series robust-pass count
drops from 5 to 4. However, strict-positive remains 0 and final holdout is
negative for the no-series candidate.
```

项目对应：

```text
no-series robust:
  final_changed_windows: 54
  final_metric_delta: -0.0000143517

include-series robust:
  final_changed_windows: 1
  final_metric_delta: +0.0000001652
```

## 5. Why The Include-Series Positive Does Not Count

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只改 1 次不算可靠 | final exposure too small | `final_changed_windows=1` |
| 小正数可能是偶然 | high variance estimate | tiny intervention count |
| 仍然低于 fallback | below fallback lift | negative relative lift |
| 不能发布 | not promotion evidence | diagnostic only |

通俗解释：

```text
include-series robust 看起来有一个小正数。

但它只改了 1 个窗口。

这和上一轮我们学过的 exposure 问题一样：

  只出手一次，
  就算赢了，
  也不能说明规则可靠。
```

专业解释：

```text
The include-series robust final result is not actionable because the final
intervention count is 1. Its estimated delta is too sparse to support
promotion.
```

项目对应：

```text
include-series robust final:
  changed_windows: 1
  metric_delta: +0.0000001652
  relative_lift_vs_fallback: -0.0014398426
```

## 6. What This Teaches About LoRA Work

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 有 leverage 不等于有提升 | objective changes can hurt | no-series negative final |
| 时间平衡要验证 final | temporal weighting needs holdout proof | final split |
| 曝光门不能只放 validation | final exposure also matters | include-series changed 1 |
| 失败也能缩小搜索空间 | falsified training lever | stop this variant |

通俗解释：

```text
这轮比 cut-balanced 更有意义：

  cut-balanced 基本没施力点。
  time-bin-balanced 真的改了模型行为。

但改了不代表改对了。

它让 no-series final 变负。
所以这条简单时间平衡路线不能晋级。
```

专业解释：

```text
The experiment falsifies simple equal-mass temporal bin weighting. The model
responds to the objective, but the learned boundary does not transfer to final
holdout.
```

项目对应：

```text
kept:
  time-bin diagnostics

rejected:
  time-bin-label-balanced as a promotion config
```

## 7. Next Round

Recommendation:

```text
Keep:
  time-bin summaries
  training_time_bins parameter
  minimum validation exposure gate

Do not promote:
  no-series time-bin robust
  include-series one-window robust

Next experiment:
  add minimum final exposure gate
  then test time-bin count sensitivity only if final exposure is sufficient
```
