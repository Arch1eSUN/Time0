# 017 - No-Leak Adapter Routing

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-router.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再训练新学生 | no new LoRA training | reused existing adapters |
| 让系统选择派哪个学生 | adapter routing | `full/recent1500/recent2000/recent3000` |
| 不能看答案再选人 | no holdout leakage | prior cuts only |
| 先测试最朴素的选法 | historical-performance router | `evaluate_adapter_router.py` |

通俗解释：

```text
上一轮我们发现：
不同考试适合不同 adapter。

所以这轮不继续训练新 adapter，
而是问一个更重要的问题：

能不能在考试前，
根据过去成绩判断这次该用哪个 adapter？
```

专业解释：

```text
This run evaluates adapter-family routing using historical out-of-sample
reports. Route selection for each cut can only use earlier cut reports.
```

项目对应：

```text
cut4000: no prior cut -> default full-history
cut5000: selection uses cut4000 only
cut5500: selection uses cut4000 and cut5000 only
```

## 2. What Is Adapter Routing?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不让一个人考所有科目 | conditional adapter selection | multiple LoRA adapters |
| 看情况派不同专家 | routing policy | choose adapter family |
| 专家本身不变 | frozen candidate adapters | no new training |
| 变的是选择规则 | inference-time selection | router |

通俗解释：

```text
LoRA adapter 可以理解成：
给基础模型装上的一个小专业插件。

adapter routing 就是：
我们手里有多个插件，
预测前先判断当前更适合哪个插件。
```

专业解释：

```text
Adapter routing is a policy that selects one adapter from a candidate set before
inference. The selected adapter changes the model behavior without changing the
base model or merging all adapters.
```

项目对应：

```text
candidate families:
full-history
recent1500
recent2000
recent3000
```

## 3. What Does No-Leak Mean?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 考前能知道的信息可以用 | pre-holdout information allowed | prior cut reports |
| 考后答案不能用 | holdout metrics forbidden for selection | current cut hidden |
| 看答案选 adapter 是作弊 | data leakage | leaky oracle |
| 作弊结果只能当上限 | upper bound only | not deployable |

通俗解释：

```text
如果 cut5500 结束后我们才发现 recent2000 最好，
然后说：
“那 cut5500 就应该用 recent2000。”

这不叫模型强。
这叫看了答案。
```

专业解释：

```text
No-leak routing means the selection function cannot use labels, errors, or
metrics from the evaluation holdout. It can only use data available before the
forecasting decision.
```

项目对应：

```text
valid:
use cut4000 result to choose for cut5000
use cut4000 + cut5000 result to choose for cut5500

invalid:
use cut5500 result to choose the cut5500 adapter
```

## 4. Two Routers We Tested

| Router | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| `global_history_best` | 过去谁整体最好，就派谁 | global historical winner | one family per cut |
| `per_series_history_best` | 每条序列过去谁最好，就派谁 | per-series historical winner | one family per series |

通俗解释：

```text
global_history_best:
全班过去平均分最高的人，下一场继续派他。

per_series_history_best:
数学派数学强的人，英语派英语强的人。
```

专业解释：

```text
The global router minimizes historical weighted MAE across prior cuts. The
per-series router minimizes historical weighted MAE separately for each series.
```

项目对应：

```text
selection_metric=mae
horizon_len=20
cold_start_family=full
```

## 5. Results

| Method | Scope | MAE gain | SMAPE gain | 判断 |
|---|---|---:|---:|---|
| `recent2000` fixed | all cuts | 1.857% | 0.838% | 当前最好固定方案 |
| `global_history_best` | routed cuts only | -1.265% | -1.032% | 失败 |
| `per_series_history_best` | routed cuts only | -0.069% | -0.072% | 基本无效 |
| `leaky_current_cut_best_global` | all cuts | 2.453% | 0.791% | 作弊上限，不算成功 |

通俗解释：

```text
历史成绩选人这件事，没有真正成功。

它的问题是：
上一次考得好，不代表下一次还适合。
```

专业解释：

```text
Historical aggregate performance is not a strong enough router signal under
the current rolling cuts. It overfits previous cut behavior and fails to
generalize to the next cut.
```

项目对应：

```text
global router:
cut5000 selected recent1500 because recent1500 won cut4000.
But recent1500 was bad on cut5000.

per-series router:
cut5500 improved, but cut5000 regressed.
```

## 6. Why The Leaky Oracle Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 如果能提前选对，收益很大 | adapter choice has upside | 2.453% MAE gain |
| 但这次是看答案选的 | current-cut oracle is leakage | invalid result |
| 它说明方向有潜力 | upper-bound evidence | keep routing direction |
| 它不能当成果发布 | not promotion evidence | no release |

通俗解释：

```text
作弊版 router 告诉我们：
如果真的能提前知道该用哪个 adapter，
效果可能超过 2% 门槛。

但是它是作弊版，
所以不能拿来发布。
```

专业解释：

```text
The leaky oracle provides an upper bound for adapter-family selection. It shows
that routing capacity may be valuable, but the selection signal must be learned
from valid pre-holdout features.
```

项目对应：

```text
leaky best:
cut4000 -> recent1500
cut5000 -> full
cut5500 -> recent2000

average MAE gain: 2.453%
promotion gate threshold: 2%
status: invalid because selection used current-cut metrics
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不只看训练有没有完成 | evaluation protocol matters | report-driven routing |
| 多个 adapter 不自动变强 | ensemble needs a valid selector | routing failed so far |
| 选 adapter 也会过拟合 | router overfitting | cut4000 -> cut5000 failed |
| 不偷看答案很重要 | leakage control | no-leak guardrail |

通俗解释：

```text
这轮最重要的知识是：

多个 LoRA adapter 放在一起，
不会天然变成更强模型。

真正难的是：
预测前怎么知道该用哪个 adapter。
```

专业解释：

```text
Adapter routing creates a new interface: the selector. The selector must be
validated like a model, because it can overfit and leak just like the adapter
itself.
```

项目对应：

```text
new Module:
adapter router

new Interface:
inputs available before forecast -> selected adapter family

failed first Adapter:
historical aggregate MAE selector
```

## 8. What We Need Next

| 下一步 | 为什么 |
|---|---|
| 保存逐窗口预测 | aggregate report 太粗，训练不了真正 router |
| 保存 adapter disagreement | 不同 adapter 分歧可能提示 regime |
| 加 pre-holdout validation split | 选择器要在考试前训练 |
| 做 nested rolling eval | router 自己也要滚动验证 |

通俗解释：

```text
现在的 report 只告诉我们：
一整段考试最后平均错多少。

这太粗了。

如果要训练 router，
我们需要每一道题的情况：
预测前波动率是多少？
最近趋势是什么？
几个 adapter 的预测差异大不大？
最后谁错得少？
```

专业解释：

```text
The next step is prediction-level instrumentation: store per-window predictions,
actuals, series metadata, and adapter outputs so a router can learn from
pre-forecast features under nested validation.
```

项目对应：

```text
next artifact:
per-window prediction archive

next script change:
extend evaluate_timesfm.py or add a companion exporter

next routing features:
series_id
recent_mean
recent_std
last_value
adapter_disagreement
```

## 9. Current Verdict

| 问题 | 答案 |
|---|---|
| routing 方向要不要停？ | 不停 |
| history router 成功了吗？ | 没有 |
| 可以发布 adapter 吗？ | 不可以 |
| 下一轮继续训练新 LoRA 吗？ | 暂时不训练 |
| 下一轮做什么？ | 先补 prediction-level router 数据 |

一句话：

```text
adapter routing 有潜力，但历史平均成绩不是足够好的选择信号。
下一轮应该先收集逐窗口预测证据，再训练真正的 no-leak router。
```
