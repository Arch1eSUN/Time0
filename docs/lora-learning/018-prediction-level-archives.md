# 018 - Prediction-Level Archives

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-prediction-archive.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有继续训练新 adapter | no new fine-tuning | existing TimesFM/LoRA weights |
| 给评估脚本加了记账能力 | prediction-level instrumentation | `--predictions-output` |
| 每道题都保存下来 | per-window prediction archive | one record per forecast window |
| 为 router 训练准备数据 | router training dataset surface | future joiner |

通俗解释：

```text
之前我们的 report 只像成绩单：
这次考试平均错多少。

这轮我们开始保存每一道题：
题目前的状态是什么？
模型预测了什么？
正确答案是什么？
这道题错了多少？
```

专业解释：

```text
We extended TimesFM evaluation to optionally emit per-window prediction records.
This creates the data surface required for a no-leak adapter router.
```

项目对应：

```text
script:
experiments/timesfm-lora/scripts/evaluate_timesfm.py

new argument:
--predictions-output reports/predictions-*.json
```

## 2. Why Aggregate Reports Were Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 平均分太粗 | aggregate metrics are too coarse | per-series report failed |
| 不知道哪道题适合哪个 adapter | no window-level attribution | cannot train router |
| 只能事后总结 | post-hoc evaluation only | not enough for selection |
| router 需要题目特征 | router needs pre-forecast features | prediction archive |

通俗解释：

```text
如果只知道一个学生平均 80 分，
我们还是不知道：

他擅长哪类题？
在哪类题会错？
下一道题该不该派他？
```

专业解释：

```text
Aggregate MAE/SMAPE can rank adapters after evaluation, but it cannot train a
selection function because it lacks per-window features and per-window errors.
```

项目对应：

```text
history router failed:
global routed-cuts MAE gain: -1.265%
per-series routed-cuts MAE gain: -0.069%
```

## 3. What Is A Prediction Archive?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 每道预测题的记录 | per-window record | `records[]` |
| 题目前能看到的信息 | pre-forecast features | `features` |
| 模型交的答案 | model output | `predicted` |
| 真正答案 | ground truth | `actual` |
| 这道题错多少 | per-window error | `mae`, `smape` |

通俗解释：

```text
prediction archive 就像一本错题本。

不是只写：
“这次考了 80 分。”

而是写：
“第 1 题，当时题目长这样，我答了这个，正确答案是那个，我错了这么多。”
```

专业解释：

```text
A prediction archive stores inference-time context, model predictions, observed
future values, and per-window loss. It can be used to train or evaluate a router
without rerunning inference for every analysis step.
```

项目对应：

```text
window_id = series_id:start_index
```

`window_id` 很重要，因为后面要把多个 adapter 在同一道题上的预测拼起来。

## 4. What Features Did We Save?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最近一个值 | last context value | `past_last` |
| 最近平均水平 | context mean | `past_mean` |
| 最近波动大小 | context standard deviation | `past_std` |
| 最近最低点 | context min | `past_min` |
| 最近最高点 | context max | `past_max` |
| 最近趋势 | last minus first | `past_trend` |

通俗解释：

```text
预测前我们不能看未来答案。

所以 features 只能来自 past：
过去这一段最后是多少？
平均多少？
波动大不大？
趋势往上还是往下？
```

专业解释：

```text
Router features must be available before the forecast. The first feature set is
derived only from the context window, so it does not leak holdout labels.
```

项目对应：

```text
features:
past_last
past_mean
past_std
past_min
past_max
past_trend
```

## 5. Actual vs Predicted

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| `predicted` 是模型答案 | forecast output | length = horizon |
| `actual` 是未来真值 | ground truth | length = horizon |
| 训练 router 时不能提前看 `actual` | labels not features | no-leak rule |
| 评估时可以用 `actual` 算错多少 | supervised target/eval | `mae`, `smape` |

通俗解释：

```text
actual 不是给模型预测前看的。

actual 是考试结束后用来判卷的。

如果 router 在选择 adapter 前看了 actual，
那还是作弊。
```

专业解释：

```text
Actual future values are labels for evaluation and supervised router training.
They cannot be part of the runtime router input.
```

项目对应：

```text
runtime router input:
features + available adapter forecasts

training/evaluation target:
which adapter had lower future error
```

## 6. What We Verified

| 检查 | 结果 |
|---|---|
| LoRA adapter path writes archive | passed |
| zero-shot path writes archive | passed |
| two archives align by `window_id` | passed |
| each record has 20 actual values | passed |
| each record has 20 predicted values | passed |
| feature keys match contract | passed |

Observed:

```text
archives_aligned 20
first_window_id VIXCLS:realized_vol_20:550
feature_keys past_last,past_max,past_mean,past_min,past_std,past_trend
zero_first_mae 0.05017235472868775
lora_first_mae 0.050924211827857356
```

通俗解释：

```text
zero-shot 和 LoRA 现在可以对齐到同一道题。

这意味着下一步我们可以问：
同一道题上，哪个 adapter 答得更好？
它们的答案分歧大不大？
这种分歧能不能提前提示该选谁？
```

专业解释：

```text
Aligned archives make adapter disagreement features possible. The join key is
stable across zero-shot and adapter runs.
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 微调不是终点 | fine-tuning is not the final artifact | adapter evidence needed |
| 评估数据也要设计 | evaluation data model matters | prediction archive |
| router 需要训练数据 | selector needs supervised examples | per-window labels |
| 防泄漏要从数据结构开始 | leakage prevention starts at schema | features vs actual |

通俗解释：

```text
LoRA 不是训练完就结束。

一个严肃的开源模型项目还要回答：
它什么时候有用？
什么时候没用？
和另一个 adapter 比，什么时候该选谁？
```

专业解释：

```text
LoRA adaptation creates model variants. To use variants safely, the project
needs an evaluation and routing data model that separates inputs, predictions,
labels, and decisions.
```

项目对应：

```text
new Interface:
evaluate_timesfm.py -> aggregate report + optional prediction archive

next Module:
prediction archive joiner

future Adapter:
no-leak router
```

## 8. Current Verdict

| 问题 | 答案 |
|---|---|
| 这轮模型变强了吗？ | 没有直接证明 |
| 这轮重要吗？ | 重要，因为打通了 router 数据面 |
| 可以发布 adapter 吗？ | 还不可以 |
| 下一轮继续训练 LoRA 吗？ | 先不训练 |
| 下一轮做什么？ | 导出完整 archives，然后做 joiner/router |

一句话：

```text
我们现在从“训练 adapter”进入“构建 adapter 选择系统”的阶段。
逐窗口 prediction archive 是 router 的训练数据地基。
```
