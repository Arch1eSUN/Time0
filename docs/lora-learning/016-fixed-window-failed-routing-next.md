# 016 - Fixed Window Failed: Why Routing Is Next

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-recent1500.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把训练窗口再缩短 | shorter recent-window fine-tuning | `recent1500` |
| 只看考试前最近 1500 个窗口 | recency sweep | `max_windows=1500` |
| LoRA 配置不变 | controlled experiment | `r=4, alpha=8, step=200` |
| 和所有旧窗口方案比较 | fixed-window comparison | full / 1500 / 2000 / 3000 |

通俗解释：

```text
我们已经试过：

看全部历史。
只看最近 3000 个窗口。
只看最近 2000 个窗口。
只看最近 1500 个窗口。

这轮的任务是确认：
是不是窗口越短，cut5500 越好？

答案：不是。
```

专业解释：

```text
This run completes a fixed-window recency sweep and tests whether a shorter
train window improves the hardest holdout regime.
```

项目对应：

```text
recent1500:
cut4000 train = windows 2500-3999
cut5000 train = windows 3500-4999
cut5500 train = windows 4000-5499
```

## 2. Results

| Cut | Best fixed window | Best MAE | recent1500 gain | 判断 |
|---:|---|---:|---:|---|
| 4000 | `recent1500` | 0.113148473 | 3.778% | recent1500 最好 |
| 5000 | `full-history` | 0.078652678 | -3.462% | recent1500 失败 |
| 5500 | `recent2000` | 0.128443571 | -0.110% | recent1500 失败 |

通俗解释：

```text
不是一个窗口通吃。

cut4000 喜欢 recent1500。
cut5000 喜欢 full-history。
cut5500 喜欢 recent2000。

所以继续猜一个固定窗口，没有太大意义。
```

专业解释：

```text
The optimal training window is split-dependent. A single fixed recency window
does not dominate across rolling holdouts.
```

项目对应：

```text
full-history average MAE improvement: 1.515849%
recent1500 average MAE improvement:   0.068585%
recent2000 average MAE improvement:   1.723918%
recent3000 average MAE improvement:   1.507674%
```

## 3. Why Recent1500 Failed

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 看得太少，容易偏科 | high variance from narrow train window | cut5000 collapsed |
| 对某场考试有效 | local regime fit | cut4000 best |
| 对另一场考试有害 | poor cross-regime generalization | cut5000, cut5500 weak |
| 不能当全局 adapter | not robust as one fixed policy | no promotion |

通俗解释：

```text
recent1500 像只复习了最近一小本题。

如果考试刚好和这本题很像，效果很好。
如果考试稍微换环境，就容易偏。
```

专业解释：

```text
Shorter recency windows can reduce stale-regime exposure but increase variance
and reduce coverage of useful historical dynamics.
```

项目对应：

```text
recent1500 cut4000 = best so far
recent1500 cut5000 = worse than zero-shot
recent1500 cut5500 = worse than zero-shot
```

## 4. What Is Routing?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只用一个学生答所有卷子 | adapter selection | choose adapter per regime |
| 看题型选择复习策略 | regime-aware policy | choose window family |
| 不是偷看答案 | no holdout leakage | selection from validation only |
| 比固定窗口更灵活 | conditional adapter choice | full / r1500 / r2000 / r3000 |

通俗解释：

```text
如果不同考试适合不同训练窗口，
那我们不应该逼一个 adapter 解决所有情况。

routing 的意思是：
先判断当前像哪种市场环境，
再选对应 adapter。
```

专业解释：

```text
Regime-aware routing selects among multiple adapters using pre-holdout evidence
or regime features, instead of using one adapter for every future window.
```

项目对应：

```text
candidate adapters:
full-history
recent1500
recent2000
recent3000
```

## 5. The Important Guardrail

| 错误做法 | 正确做法 |
|---|---|
| 看了 holdout 结果后选择 adapter | 用 validation 选择 adapter |
| 每个 cutpoint 事后挑最好 | 先定义 routing policy |
| 用测试集调参 | 测试集只做最终评估 |
| 把 oracle 当模型 | routing 不能偷看答案 |

通俗解释：

```text
不能考试结束后说：
“这场应该派 recent1500。”

那是作弊。

正确做法是：
考试前，用训练段末尾的一小段 validation，
判断哪种 adapter 更适合当前 regime。
```

专业解释：

```text
Adapter routing must be selected from validation windows that precede the
holdout. Choosing the best adapter using holdout metrics would be leakage.
```

项目对应：

```text
next experiment must define validation windows before holdout.
```

## 6. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA adapter 也可以有多个 | adapter ensemble / router | multiple window adapters |
| 不是所有问题都靠加 rank | capacity is not current blocker | no immediate `r=8` |
| 数据选择是模型行为的一部分 | train distribution controls adapter | window sweep evidence |
| 评估设计比训练本身更重要 | validation protocol matters | avoid routing leakage |

通俗解释：

```text
现在我们学到：
LoRA 不只是“训练一个 adapter”。

在金融这种会换环境的时序里，
更可能需要：
多个 adapter + 一个选择规则。
```

专业解释：

```text
For non-stationary financial forecasting, routing among specialized adapters may
outperform a single fixed-window adapter, provided the routing policy is learned
without holdout leakage.
```

项目对应：

```text
Time0 next direction = regime-aware adapter routing.
```

## 7. Next Round

| 选项 | 结论 | 原因 |
|---|---|---|
| 继续测固定窗口 | 暂停 | 已看到 split-dependent optimum |
| 直接 `r=8` | 暂缓 | 容量不是主要证据 |
| routing | 建议 | 不同 cutpoint 最优 adapter 不同 |
| per-series routing | 候选 | 某些 series 长期拖累 |
| 发布 adapter | 不发布 | 未过 promotion gate |

下一轮建议：

```text
method=regime-aware adapter routing
candidate_adapters=full-history,recent1500,recent2000,recent3000
selection_data=pre-holdout validation windows
target=realized_vol_20
```

要验证的问题：

```text
不用偷看 holdout 的情况下，
router 能不能选出比任何单一固定窗口更稳的 adapter？
```
