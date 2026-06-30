# 007 - When Is LoRA Training Successful?

Date: 2026-07-01

Related repo document:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/SUCCESS_CRITERIA.md
```

## 1. The Missing Rule

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 跑完不等于成功 | Training completion is not model improvement | adapter saved does not mean adapter is useful |
| 训练时分数变好不等于成功 | Training loss is not enough | holdout metrics decide |
| 一次赢不等于真强 | Single split win is weak evidence | need rolling holdout cut-points |
| 上线需要更高标准 | Promotion requires reproducibility and integration safety | Moirai seam must stay clean |

我们前面缺的不是训练代码，而是判定规则。

通俗说：

```text
以前我们像是在说：
“学生写完作业了。”

但我们还没有说清楚：
“什么分数算及格？”
“考几次才算稳定？”
“考砸了什么时候停？”
“什么时候可以让它去真实项目里干活？”
```

专业说：

```text
We had training execution, but not an explicit experimental success criterion.
```

项目对应：

```text
SUCCESS_CRITERIA.md now defines run-valid, experiment-useful, candidate-success,
and promotion-ready gates.
```

## 2. Four Levels Of "Success"

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 能跑完 | Run Valid | script exits, report saved, no NaN/inf |
| 能学到东西 | Experiment Useful | compared against naive and zero-shot |
| 看起来真的变强 | Candidate Success | beats TimesFM zero-shot on holdout |
| 可以准备接产品 | Promotion Ready | wins across rolling windows and stays reproducible |

### Level 1: Run Valid

通俗解释：

```text
机器没有炸，训练没有中断，文件真的生成了。
```

专业解释：

```text
The run is technically valid.
```

它需要满足：

```text
训练脚本正常结束
adapter 文件夹存在
评估 report 文件存在
指标不是 NaN 或 inf
target field 正确
holdout window 数量符合预期
每个 series 都有样本
```

项目对应：

```text
reports/*.json
adapters/*
windows_by_series
field
mae
smape
```

注意：

```text
Run Valid 是最低标准。
它只说明这次实验“可用来分析”，不说明模型变强。
```

### Level 2: Experiment Useful

通俗解释：

```text
这次实验能告诉我们一个清楚结论。
```

专业解释：

```text
The experiment is controlled and comparable.
```

它需要满足：

```text
同一个 holdout split
同一个 context_len
同一个 horizon_len
同一个 target field
同一批 series
只改一个主要变量
同时对比 naive baseline 和 TimesFM zero-shot
```

为什么“一次只改一个主要变量”？

通俗说：

```text
如果你同时换题目、换学习率、换 LoRA rank、换训练步数，
最后分数变了，你不知道是谁造成的。
```

专业说：

```text
This preserves experimental attribution.
```

项目对应：

```text
level -> log_change 是 target 变化。
r=4, alpha=8, max_steps=200 保持不变。
所以我们能判断：这轮主要是在测试 target choice。
```

### Level 3: Candidate Success

通俗解释：

```text
它在新题上比原版 TimesFM 更准。
```

专业解释：

```text
The adapter improves out-of-sample performance over the zero-shot base model.
```

最低要求：

```text
primary metric 至少比 zero-shot 好 1%
secondary metric 不能明显变差
必须赢过 naive baseline
```

为什么不是只赢 naive？

通俗说：

```text
naive 是很笨但很强的简单猜法。
赢 naive 只能说明“不是废的”。
但我们微调的是 TimesFM，所以真正要赢的是原版 TimesFM。
```

专业说：

```text
The correct baseline for adaptation value is the frozen foundation model,
not only naive forecasting.
```

项目对应：

```text
LoRA adapter vs TimesFM zero-shot
```

### Level 4: Promotion Ready

通俗解释：

```text
不是一次考试碰巧赢，而是换几套时间段的卷子都能赢。
```

专业解释：

```text
The adapter generalizes across rolling chronological validation splits.
```

它需要满足：

```text
至少 3 个 rolling holdout cut-points
平均 primary metric 至少比 zero-shot 好 2%
不是只靠某一个 series 拉高总分
重复跑一次结果稳定
训练数据、参数、报告路径都能追溯
```

项目对应：

```text
Promotion Ready 之后才讨论 Moirai integration。
在那之前，它只是 research artifact。
```

## 3. What Is A Holdout?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 作业后面的考试题 | Out-of-sample evaluation split | `skip_windows=5000`, `max_windows=500` |
| 不能提前偷看 | Avoid leakage | train split and holdout split are separated |
| 用未来考过去训练出的模型 | Chronological validation | later windows test earlier training |

在时序预测里，顺序很重要。

通俗说：

```text
你不能拿 2025 年的数据训练，然后说自己预测了 2020 年。
真正合理的是：用更早的数据训练，拿后面的数据考试。
```

专业说：

```text
Time-series validation must preserve chronological order.
```

项目对应：

```text
训练窗口：
skip_windows=0
max_windows=5000

考试窗口：
skip_windows=5000
max_windows=500
```

## 4. Why Training Loss Is Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 作业越做越熟不代表考试更好 | Lower training loss can still overfit | level step1000 got worse |
| 背答案不是学能力 | Memorization is not generalization | holdout decides |
| LoRA 小也会过拟合 | Parameter-efficient does not mean overfit-proof | more steps can hurt |

训练 loss 是什么？

通俗说：

```text
模型在练习题上的错误。
```

专业说：

```text
Optimization objective on the training split.
```

holdout metric 是什么？

通俗说：

```text
模型在没见过的新题上的错误。
```

专业说：

```text
Generalization metric on an out-of-sample split.
```

项目对应：

```text
level step200 already lost to zero-shot.
level step1000 became worse.
```

这说明：

```text
继续加训练步数不会自动变强。
```

专业表达：

```text
Increasing training budget can degrade out-of-sample performance.
```

## 5. Metrics: MAE And SMAPE

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| MAE 看平均差多少 | Mean Absolute Error | lower is better |
| SMAPE 看相对差多少 | Symmetric Mean Absolute Percentage Error | lower is better |
| 不同 target 要选不同主指标 | Metric suitability depends on target distribution | `log_change` uses MAE as hard gate |

MAE:

```text
预测错了多少，取绝对值，再平均。
```

专业说：

```text
MAE measures average absolute forecast error.
```

SMAPE:

```text
错的比例有多大。
```

专业说：

```text
SMAPE measures relative error normalized by forecast and actual magnitudes.
```

为什么 `log_change` 上 SMAPE 不能当唯一裁判？

通俗说：

```text
log_change 经常接近 0。
真实值太小的时候，一点点误差都会被比例放大。
```

专业说：

```text
SMAPE is unstable for near-zero targets because the denominator becomes tiny.
```

项目对应：

```text
log_change LoRA:
MAE 变好了一点。
SMAPE 变差了一点。

所以这不是 clean success，只能叫 partial signal。
```

## 6. How We Decide Stop

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 连续几次没进步就停 | Early stop on no holdout improvement | 3 checkpoints no primary metric gain |
| 作业变好考试变差就停 | Overfitting stop | train loss down, holdout worse |
| 比原版 TimesFM 差就停 | Zero-shot regression stop | adapter worse than base model |
| 指标不适合就换题 | Target stop | move from `level`/`log_change` to `realized_vol_20` |

停止不是失败。

通俗说：

```text
停止是为了不把时间浪费在已经显示不好的方向上。
```

专业说：

```text
Stop criteria prevent overfitting, wasted compute, and false promotion.
```

项目对应：

```text
level 方向：停止继续加 step。
log_change 方向：可以最多做一次复验，但不应该直接晋级。
下一轮主方向：realized_vol_20。
```

## 7. Current Run Verdicts

| Run | 通俗判断 | 专业判断 | 项目结论 |
|---|---|---|---|
| `level r4 step200` | 没赢原版 | failed zero-shot comparison | not success |
| `level r4 step1000` | 训更久反而更差 | longer training degraded holdout | stop this direction |
| `log_change r4 step200` | 有一点苗头 | MAE improved, SMAPE regressed | partial signal only |

`level` 的结论：

```text
这个 target 当前不值得继续堆训练步数。
```

专业说：

```text
The raw-level target failed candidate success and showed no evidence that
longer training helps.
```

`log_change` 的结论：

```text
这个 target 比 level 更有苗头，但还不算成功。
```

专业说：

```text
The transformed target improved primary absolute error, but did not produce
metric-consistent generalization.
```

## 8. Why Next Is `realized_vol_20`

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 我们不预测明天涨跌，先预测风险大小 | Volatility is more stable than directional returns | market/macro risk adapter |
| 比 raw level 更统一 | More comparable target distribution | avoids SP500 vs rates scale mismatch |
| 比 log_change 更适合相对误差 | Less near-zero instability | SMAPE becomes more meaningful |
| 对 Moirai 更有用 | Better downstream risk feature | temporal simulation input |

通俗说：

```text
市场涨跌很难直接猜。
但“未来一段时间会不会更剧烈波动”更像一个可学习的结构。
```

专业说：

```text
Realized volatility is a domain-aligned risk target with stronger structure
than one-step directional return.
```

项目对应：

```text
下一轮建议：
field=realized_vol_20
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
max_steps=200
same holdout split
```

## 9. The Rule To Remember

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 跑完只是开始 | Completed training is only an artifact | Run Valid |
| 赢简单猜法才有资格看 | Beat naive baselines | Experiment Useful |
| 赢原版 TimesFM 才算微调有价值 | Beat zero-shot foundation model | Candidate Success |
| 多个时间段都赢才考虑接项目 | Rolling validation + reproducibility | Promotion Ready |

一句话：

```text
LoRA 成功 = 不是 adapter 被训练出来了，而是 adapter 在没见过的未来窗口里，
稳定地比原版 TimesFM 更准。
```

专业表达：

```text
LoRA success means reproducible out-of-sample improvement over the frozen
foundation model under domain-relevant metrics.
```
