# 020 - Router Training Rows

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-router-rows.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把 5 个学生同一道题的答案放到同一行 | join aligned prediction archives | `join_prediction_archives.py` |
| 看谁这道题错得最少 | supervised best-family label | `best_family_by_mae` |
| 只把考试前能看到的信息给 selector | no-leak runtime features | `runtime_features` |
| 把标准答案单独放起来 | outcome/label separation | `label.actual`, `family_errors` |

通俗解释：

```text
之前我们已经让 5 个 family 都做了同一批题：

zero-shot
full
recent1500
recent2000
recent3000

这轮不是继续训练 TimesFM。
这轮是在整理“训练 router 的教材”。

每一行就是一道题：
这道题的过去走势是什么？
5 个 family 分别预测成什么样？
预测之间分歧大不大？
最后谁错得最少？
```

专业解释：

```text
We converted aligned per-window prediction archives into supervised router rows.
Each row has runtime-safe features and offline labels. The label is the adapter
family with the lowest future MAE for that forecast window.
```

项目对应：

```text
input: 15 prediction archives
output: 1500 router rows
join key: cut + window_id
label: best_family_by_mae
```

## 2. What Is A Router Row?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一道完整练习题 | supervised training example | one JSON row |
| 题目前半部分 | feature vector | `runtime_features` |
| 题目答案 | training label | `label.best_family_by_mae` |
| 每个学生的错题记录 | outcome metrics | `family_errors` |

通俗解释：

```text
想象你要训练一个小裁判。

裁判未来要做的事是：
看到一个新的预测窗口，
判断应该用哪个 adapter。

那我们就要给裁判准备很多练习题：

输入：
这条时间序列过去长什么样？
几个 adapter 的预测长什么样？
它们预测分歧大不大？

答案：
真实未来出来以后，哪个 adapter 错得最少？
```

专业解释：

```text
A router row is a supervised sample for adapter selection. The feature side
must contain only information available before the forecast target is observed.
The label side can contain future outcomes because it is used only offline for
training and evaluation.
```

项目对应：

```text
runtime_features:
  context:
    past_last
    past_mean
    past_std
    past_min
    past_max
    past_trend
  prediction_summaries:
    per-family predicted_mean/predicted_std/predicted_trend/...
  prediction_disagreement:
    family_predicted_mean_range
    horizon_prediction_spread_mean

label:
  best_family_by_mae
  best_mae
  second_best_mae
  best_margin_mae
  family_errors
  actual
```

## 3. What Is Data Leakage Here?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 考试时偷看答案 | using future target in features | leakage |
| 训练时可以看答案 | labels can use future outcomes | offline supervision |
| 上线预测时不能看答案 | runtime features cannot use actuals/errors | no-leak guardrail |
| 偷看答案的成绩只能当上限 | leaky oracle upper bound | invalid production policy |

通俗解释：

```text
训练 router 的时候，我们当然要知道正确答案。
不然它没法学习。

但是预测一个新的未来窗口时，
真实未来还没发生。

所以：

可以放进输入：
过去 128 天的走势
5 个 adapter 各自的预测
5 个预测之间的分歧

不能放进输入：
真实未来 actual
每个 adapter 的 MAE
谁是 best_family
```

专业解释：

```text
Leakage occurs when feature construction uses information unavailable at
decision time. In this project, `actual`, `mae`, `smape`, and `best_family`
are valid offline labels/outcomes, but invalid runtime features.
```

项目对应：

```text
script guardrail:
FORBIDDEN_RUNTIME_KEYS = {
  "actual",
  "mae",
  "smape",
  "best_family",
  "family_errors",
  "label"
}
```

## 4. What Did The Labels Show?

| Family | Best-window labels |
|---|---:|
| `zero-shot` | 379 |
| `full` | 328 |
| `recent1500` | 419 |
| `recent2000` | 197 |
| `recent3000` | 177 |

通俗解释：

```text
没有一个 adapter 永远最好。

有些题 zero-shot 最好，
有些题 full 最好，
有些题 recent1500 最好，
有些题 recent2000 最好。

这说明“只选一个固定 adapter”可能不够聪明。
```

专业解释：

```text
The best-family label distribution is multi-modal. That means adapter selection
has a real classification target, not a trivial always-pick-one-family target.
```

项目对应：

```text
rows: 1500
best fixed family by mean MAE: recent2000
but per-window labels are spread across all 5 families
```

## 5. What Is The Leaky Oracle?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 每道题都提前知道谁答得最好 | future-error selector | leaky oracle |
| 它不是合法模型 | invalid runtime policy | cannot publish |
| 它告诉我们上限在哪 | upper-bound diagnostic | research signal |
| 上限越高，router 越值得试 | routing headroom | next experiment |

Observed:

```text
zero-shot mean MAE: 0.1094328925
best fixed family: recent2000
recent2000 mean MAE: 0.1074011875
leaky per-window oracle MAE: 0.1029191785
leaky per-window oracle MAE improvement vs zero-shot: 5.952245%
```

通俗解释：

```text
leaky oracle 像一个作弊裁判：
它每一道题都先看真实答案，
然后挑错得最少的 adapter。

这个成绩不能算真正成绩。

但它有价值：
如果作弊裁判都没有提升，
说明 router 没必要做。

现在作弊裁判提升接近 6%，
说明“选择 adapter”这件事可能有真实空间。
```

专业解释：

```text
The leaky oracle is an upper bound computed by selecting the lowest-MAE family
per row using future errors. It cannot be deployed, but it estimates the maximum
headroom available to a perfect router under the current candidate set.
```

项目对应：

```text
previous aggregate leaky oracle: 2.453% MAE improvement
new per-window leaky oracle: 5.952% MAE improvement
```

## 6. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不一定只训练一个最终模型 | multiple adapters can be candidate experts | adapter family |
| 每个 adapter 可能擅长不同题型 | specialization by regime/window | label distribution |
| router 是 adapter 选择器 | meta-model over adapters | future no-leak router |
| 不要用作弊成绩发布 | leaky oracle is not evidence | promotion still blocked |

通俗解释：

```text
LoRA 微调到现在，我们学到一件更高级的事：

不是必须押宝一个 adapter。

我们可以先训练多个 adapter，
再训练一个小 router，
让它判断当前窗口该用哪个 adapter。

这像一个专家组：
不是让所有问题都交给一个专家，
而是先判断问题类型，
再把问题交给更合适的专家。
```

专业解释：

```text
The LoRA adapters form a candidate expert set. Router training is a second-stage
supervised learning problem where features are derived from pre-forecast context
and model disagreement, and labels are derived from future evaluation outcomes.
```

项目对应：

```text
TimesFM base model: frozen foundation forecaster
LoRA adapters: domain/window-specialized candidate experts
router rows: supervised data for adapter selection
future router: no-leak policy module
```

## 7. What We Should Do Next

Recommendation:

```text
Do not train a larger LoRA rank yet.
Do not publish the adapter yet.
Train/evaluate the no-leak prediction-level router first.
```

下一轮应该测试：

```text
train cut4000 -> evaluate cut5000
train cut4000+cut5000 -> evaluate cut5500
compare:
  zero-shot
  fixed recent2000
  no-leak router
  leaky per-window oracle upper bound
```

成功标准：

```text
no-leak router must beat fixed recent2000 on future cuts
no-leak router must not depend on actual/mae/smape at runtime
no-leak router must explain selected family counts by cut
```
