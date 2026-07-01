# 048 - Finance Readiness Stop Gate

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-finance-readiness.md
```

## 1. What We Built

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给金融方向加了一个结业考 | finance readiness gate | `evaluate_finance_readiness.py` |
| 不再凭感觉决定要不要继续训练 | explicit stop/release criteria | `release_gates` |
| 把当前关键证据汇总到一张表 | evidence aggregation | fixed adapter + router + sensitivity |
| 让项目知道什么时候能停 | release stop / negative stop / continue research | `verdict` |

通俗解释：

```text
之前我们一直在训练、评估、加 router、加 guard。

这样很容易进入一个陷阱：

  每一轮都有一点点发现，
  但永远不知道什么时候算完成。

所以这轮我们加了一个“停止门禁”。

它回答三个问题：

  1. 现在能不能发布？
  2. 现在是不是应该放弃金融方向？
  3. 如果都不是，那下一步只能做什么？
```

专业解释：

```text
This round adds a finance-domain readiness evaluator that aggregates fixed
adapter evidence, router lift, router downside, and fallback-sensitivity
diagnostics into a reproducible release/stop verdict.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/evaluate_finance_readiness.py

generated report:
  experiments/timesfm-lora/runs/2026-07-02-market-macro-finance-readiness.md
```

## 2. Why We Need A Stop Gate

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练完成不等于模型有用 | training completion is not model success | adapter saved but may regress |
| 有一点提升不等于能发布 | local lift is not promotion readiness | `1.724% < 2%` |
| router 小赢不等于稳定 | aggregate lift can hide downside | 3 negative routed series |
| 没有停止条件就会无限试参数 | unbounded search creates overfit risk | rank/window/threshold sweep |

通俗解释：

```text
如果我们没有停止门禁，
项目会变成这样：

  这轮不好，换 window。
  window 不好，换 rank。
  rank 不好，换 router。
  router 不好，换 gate。
  gate 不好，再换特征。

这不是研究，这是迷路。

真正的研究需要提前说清楚：

  什么结果可以发布？
  什么结果说明该放弃？
  什么结果说明只能继续某一个具体方向？
```

专业解释：

```text
A stop gate prevents unbounded hyperparameter search. It turns open-ended
experimentation into a finite decision process with release, negative, and
continue-research outcomes.
```

项目对应：

```text
current verdict:
  continue_research

meaning:
  signal exists, but release conditions are not met
```

## 3. The Three Possible End States

| End State | 通俗解释 | 专业解释 | 项目动作 |
|---|---|---|---|
| `release_stop_ready` | 可以毕业发布 | evidence is strong enough for public adapter release | 准备 Hugging Face adapter |
| `negative_stop_ready` | 这条路走不通 | scoped evidence failed to beat zero-shot | 发布负结果或封存 |
| `continue_research` | 还没毕业，也没死 | signal exists but blockers remain | 只做能移动门禁的实验 |

通俗解释：

```text
金融方向不是只能“继续训练”。

它有三种结局：

  第一种：成功。
    指标过线，可以发布。

  第二种：失败。
    做过合理实验，还是打不过 zero-shot。
    那就不要硬凹，发布负结果也有价值。

  第三种：继续研究。
    已经看到信号，但还不够稳。
    这就是我们现在的位置。
```

专业解释：

```text
The readiness gate separates publication readiness from research usefulness.
An adapter can be useful as evidence while still being unfit for release.
```

项目对应：

```text
current state:
  continue_research

not:
  release_stop_ready

not:
  negative_stop_ready
```

## 4. Current Gate Results

| Gate | Required | Current | Passed |
|---|---:|---:|---|
| fixed average MAE lift | 2.000% | 1.724% | No |
| fixed positive cut count | 3 | 3 | Yes |
| router extra lift vs fallback | 0.200% | 0.316% | Yes |
| router negative series | 0 | 3 | No |
| zscore fallback sensitivity | no sensitive reports | 2 sensitive reports | No |

通俗解释：

```text
这张表的意思是：

  recent2000 adapter 在三个时间切点都比 zero-shot 好。
  这是好事。

  但是平均提升只有 1.724%。
  我们的发布线是 2%。
  所以还差一点。

  router 在总体上又加了一点收益。
  这也是好事。

  但 router 还有 3 个 series 变差。
  所以不能说它稳定。

  zscore 分支有些结果换 fallback 后会翻车。
  所以 zscore 不能当发布证据。
```

专业解释：

```text
The fixed recent2000 adapter passes chronological directionality but misses the
average primary-metric threshold. The best router improves aggregate MAE over
the fixed fallback, but still violates the downside gate because routed gains
are not non-negative across all series.
```

项目对应：

```text
fixed adapter:
  recent2000

best current router:
  KNN-regret fallback-veto alignment-normalized

release blocker:
  weak average lift + negative routed series
```

## 5. What Does "Final Effect" Mean?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不是预测股票涨跌 | not a trading signal | no buy/sell output |
| 是预测风险状态 | risk forecasting adapter | `realized_vol_20` |
| 给 Moirai/Time0 当风险输入 | downstream forecast/risk input | future ForecastRequest seam |
| 发布的是 adapter，不是整个 TimesFM | LoRA adapter package | Hugging Face model repo |

通俗解释：

```text
我们最后想要的不是：

  明天买不买 SP500？
  美债要不要做多？
  汇率会不会涨？

我们最后想要的是：

  未来 20 步的市场/宏观风险波动会不会变大？
  当前 series 更像哪种风险状态？
  Moirai 做决策或审计时，有没有一个更懂金融风险时序的预测模块？
```

专业解释：

```text
The target artifact is a vertical-domain TimesFM 2.5 LoRA adapter specialized
for public market/macro realized-volatility forecasting. Its product value is
as a risk feature generator or forecasting Module, not as a standalone trading
or investment decision system.
```

项目对应：

```text
final release shape:
  Arch1eSUN/Time0 on GitHub for code and eval reports
  Hugging Face adapter repo for LoRA weights and model card

expected claim:
  improves realized-volatility forecasting on public FRED market/macro series

forbidden claim:
  predicts profitable trades
```

## 6. When Can This Finance Direction End?

| Stop Condition | 通俗解释 | 专业解释 |
|---|---|---|
| fixed/router metrics pass release gates | 真的够好 | promotion-ready evidence |
| report is reproducible | 别人能复现 | public recipe + pinned data |
| no negative series remains | 不是靠少数 series 撑起来 | downside-controlled generalization |
| model card and release package ready | 可以对外负责 | release artifact complete |

通俗解释：

```text
金融方向可以成功结束的条件：

  1. 至少一个 adapter/router 组合平均 MAE 提升超过 2%。
  2. 至少 3 个 chronological cut 都赢。
  3. 不能靠一个 series 撑起总收益。
  4. 不能还有明显负收益 series。
  5. 别人能用公开数据和脚本复现。
  6. 能写清楚限制：不是金融建议，不是交易信号。

这些满足后，就不该继续无止境训练。
应该进入发布和维护。
```

专业解释：

```text
The finance line reaches release stop when a reproducible adapter/router
configuration passes promotion gates across chronological holdouts, controls
per-series downside, and is packaged with a model card, training recipe, data
provenance, and limitations.
```

项目对应：

```text
release verdict needed:
  release_stop_ready

current verdict:
  continue_research
```

## 7. What Should We Do Next?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不要盲目继续训练 | avoid ungated search | no random window/rank sweep |
| 先解决负收益 series | downside control first | SP500 / DGS10 / DEXJPUS style risk |
| 或做一个明确的 r8 对照 | scoped capacity comparison | one controlled rank test |
| 每轮都要能改变门禁表 | gate-moving experiment only | readiness report rerun |

通俗解释：

```text
下一步不能是：

  随便再训练一个 adapter 看看。

下一步应该是：

  这个实验能不能让门禁表某一项从 No 变成 Yes？

比如：

  能不能把 negative router series 从 3 降到 0？
  能不能把 average MAE lift 从 1.724% 拉到 2% 以上？
  能不能证明 r8 比 r4 稳定，而不是只更会过拟合？
```

专业解释：

```text
Continue only with experiments that target an explicit failed gate:
average lift, per-series downside, or fallback sensitivity. Otherwise the
research loop becomes ungated hyperparameter search.
```

项目对应：

```text
best next directions:
  per-series downside control for current KNN-regret router
  one controlled r8 comparison if downside control stalls
  new target only if realized_vol_20 stops improving
```
