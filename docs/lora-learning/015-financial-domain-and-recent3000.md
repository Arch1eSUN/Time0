# 015 - Financial Domain: What Are We Actually Training?

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-recent3000.md
```

## 1. Is Our Adapter Financial?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 是金融领域 | financial-domain adapter | market/macro risk |
| 但不是炒股机器人 | not a trading signal model | no buy/sell labels |
| 不是预测明天涨跌 | not direction classification | not `up/down` |
| 当前预测的是风险/波动 | volatility forecasting | `realized_vol_20` |

通俗解释：

```text
我们的 adapter 是金融领域的。

但它不是：
“明天买不买 SPY？”
“比特币会涨吗？”
“这个股票给目标价。”

它更像：
“市场接下来会不会更不稳定？”
“利率、汇率、油价、信用利差的波动风险会怎么变？”
```

专业解释：

```text
The current adapter direction is public financial market and macro risk
forecasting, focused on realized volatility rather than trading direction or
portfolio decisions.
```

项目对应：

```text
domain = financial market / macro risk
target = realized_vol_20
usage = risk signal for future Moirai forecasting Modules
```

## 2. What Data Are We Training On?

| 类别 | Series | 通俗解释 | 专业解释 |
|---|---|---|---|
| 股票市场 | `SP500` | 美股大盘 | S&P 500 index |
| 市场恐慌/隐含波动 | `VIXCLS` | 恐慌指数 | CBOE VIX |
| 长端利率 | `DGS10` | 10 年美债利率 | 10-year Treasury yield |
| 短端利率 | `DGS2` | 2 年美债利率 | 2-year Treasury yield |
| 政策利率 | `DFF` | 联邦基金利率 | effective federal funds rate |
| 信用风险 | `BAMLH0A0HYM2` | 高收益债利差 | high-yield corporate spread |
| 大宗商品 | `DCOILWTICO` | WTI 原油 | crude oil spot price |
| 美元指数 | `DTWEXBGS` | 广义美元 | trade-weighted dollar index |
| 外汇 | `DEXUSEU` | 欧元/美元 | EUR/USD exchange rate |
| 外汇 | `DEXJPUS` | 日元/美元 | JPY/USD exchange rate |

通俗解释：

```text
我们没有拿某个单一股票训练。
我们拿的是一组“金融市场温度计”：

股票、波动率、利率、信用利差、油价、美元、汇率。
```

专业解释：

```text
The dataset is a 10-series public FRED market/macro panel, converted into long
time-series format and evaluated with chronological rolling holdout splits.
```

项目对应：

```text
source = FRED public data
frequency = daily
format = series_id,timestamp,field,value,source_symbol,source
```

## 3. What Is `realized_vol_20`?

| 通俗版 | 专业版 | 项目里的样子 |
|---|---|---|
| 最近 20 天波动有多大 | 20-day realized volatility | `realized_vol_20` |
| 不是价格本身 | not level prediction | `level` 已经失败 |
| 不是涨跌幅本身 | not raw return prediction | `log_change` 只有弱信号 |
| 更接近风险强度 | risk magnitude target | current best target |

通俗解释：

```text
如果价格每天小幅变化，波动率低。
如果价格每天大起大落，波动率高。

realized_vol_20 问的是：
过去 20 天实际波动有多大？
模型要预测未来 20 天这种波动风险会怎么走。
```

专业解释：

```text
Realized volatility is derived from historical log changes and summarizes
observed movement magnitude over a rolling window.
```

项目对应：

```text
level target: failed
log_change target: partial signal
realized_vol_20 target: current strongest direction
```

## 4. Why Not Train A Buy/Sell Model First?

| 原因 | 通俗解释 | 专业解释 |
|---|---|---|
| 信号更吵 | 涨跌很难稳定预测 | directional return noise |
| 容易过拟合 | 模型可能背历史行情 | overfitting risk |
| 难证明有效 | 买卖收益受成本/滑点影响 | evaluation confounders |
| 风险更通用 | 风险预测能服务更多模块 | reusable risk feature |

通俗解释：

```text
“明天涨还是跌”通常很吵。
短期方向像猜硬币，很容易训练出看起来聪明、实际没用的模型。

风险/波动率更适合作为第一阶段：
它不直接告诉你买卖，
但能告诉你未来环境是不是更危险、更不稳定。
```

专业解释：

```text
Volatility forecasting is generally a more stable first specialization target
than directional returns because the target has stronger persistence and cleaner
risk-management use.
```

项目对应：

```text
This adapter should become a risk forecasting adapter, not a trading advisor.
```

## 5. What Did Recent3000 Test?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 多看一点最近数据 | longer recent train window | `recent3000` |
| 比 recent2000 多 1000 个窗口 | recency-length sweep | 300 per series |
| 看能不能兼顾三场考试 | rolling robustness | cut4000/5000/5500 |
| 结果没成功 | negative result | average 1.507674% |

通俗解释：

```text
recent2000 救了 cut5500，但牺牲了 cut4000/5000。

我们试 recent3000，是想问：
多看一点历史，能不能既保留 cut5500 的修复，
又把 cut4000/5000 拉回来？

答案：没有。
```

专业解释：

```text
Recent3000 tested whether a longer recency-limited window improves the
bias-variance/regime tradeoff observed in recent2000.
```

项目对应：

```text
recent3000 average MAE improvement = 1.507674%
recent2000 average MAE improvement = 1.723918%
Promotion Ready threshold = 2.000000%
```

## 6. Recent3000 Results

| Cut | Zero-shot MAE | Recent2000 gain | Recent3000 gain | 判断 |
|---:|---:|---:|---:|---|
| 4000 | 0.117591233 | 2.482% | 3.391% | recent3000 更好 |
| 5000 | 0.079628254 | 0.679% | 0.632% | 都偏弱 |
| 5500 | 0.131079191 | 2.011% | 0.500% | recent3000 明显更差 |

通俗解释：

```text
recent3000 像是：
第一场考得更好，
第二场没变好，
第三场又被旧知识带偏。
```

专业解释：

```text
Recent3000 improves cut4000 but reintroduces stale-regime interference for
cut5500.
```

项目对应：

```text
recent3000 is not a Promotion Ready adapter family.
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 训练数据范围本身很重要 | train-window selection is a hyperparameter | `recent2000` vs `recent3000` |
| 多看历史不一定更好 | more data can add stale regimes | cut5500 worsened |
| 单一 adapter 可能不够 | one fixed adapter may not fit all regimes | routing candidate |
| 负结果也有价值 | negative result narrows search | do not keep lengthening |

通俗解释：

```text
LoRA 不只是调 r、alpha、step。
你让它看哪段数据，也是在调模型。

如果金融市场环境会变，
那“所有历史都看”或者“固定看最近 N 天”都可能不是最终答案。
```

专业解释：

```text
For non-stationary financial time series, adapter performance can be highly
sensitive to training-window selection. The recent3000 negative result suggests
the optimal window length is regime-dependent.
```

项目对应：

```text
Next step should not be r=8.
Next step should map recency or test regime-aware routing.
```

## 8. Next Round

| 选项 | 结论 | 原因 |
|---|---|---|
| 发布 recent3000 | 不发布 | 平均收益 1.507674%，低于 2% |
| 继续加长窗口 | 不建议 | cut5500 修复已经变弱 |
| `recent1500` | 可测 | 看更短窗口是否进一步增强 cut5500 |
| regime-aware routing | 重要候选 | 不同 cutpoint 最优窗口不同 |
| `r=8` | 暂缓 | 还没证明容量是瓶颈 |

下一轮建议：

```text
field=realized_vol_20
training_window=recent1500
lora_r=4
max_steps=200
cutpoints=4000,5000,5500
```

要验证的问题：

```text
recent1500 会不会进一步强化 cut5500？
如果它只强化 cut5500，却损伤其他 split，
说明我们需要 regime-aware adapter routing。
```
