# 009 - First Clean LoRA Win: Realized Volatility

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-h20-r4.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 这次不猜价格，也不猜涨跌 | changed target away from level/return | `field=realized_vol_20` |
| 改成猜未来波动风险 | realized volatility forecasting | 20-day realized volatility |
| 其他训练设置保持保守 | controlled LoRA recipe | `r=4`, `alpha=8`, `step=200` |
| 还是用后面的新题考试 | chronological holdout | `skip_windows=5000`, `max_windows=500` |

通俗说：

```text
前面我们问模型：
“未来数值是多少？”
“未来变化率是多少？”

这次我们问：
“未来一段时间会不会波动更大？”
```

专业说：

```text
We moved from raw level / log-change prediction to realized-volatility
forecasting, which is closer to a market-risk target.
```

项目对应：

```text
field=realized_vol_20
context_len=128
horizon_len=20
lora_r=4
lora_alpha=8
max_steps=200
```

## 2. Why This Target Is Better

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 涨跌方向很吵 | directional returns are noisy | `log_change` only partial signal |
| 价格大小单位差太多 | raw levels are scale-heterogeneous | `level` failed |
| 风险更有结构 | volatility has stronger temporal structure | `realized_vol_20` |
| 对 Moirai 更有用 | better downstream risk feature | temporal simulation input |

通俗解释：

```text
市场明天涨还是跌，很难直接猜。
但市场最近是不是进入高波动状态，往往更有连续性。
```

专业解释：

```text
Volatility clustering makes realized volatility more structurally forecastable
than one-step direction or mixed-scale raw levels.
```

项目对应：

```text
realized_vol_20 是目前最贴近“市场/宏观风险模型”的 target。
```

## 3. Baseline Results

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 0.09038209915835001 | 0.20442511989606849 |
| Seasonal naive | 0.12437439321615 | 0.29747420644269 |
| TimesFM 2.5 zero-shot | 0.0796282537318497 | 0.1877752198880728 |

通俗解释：

```text
简单猜法已经不错。
原版 TimesFM 比简单猜法更好。
所以 LoRA 要证明自己，必须赢原版 TimesFM。
```

专业解释：

```text
The adaptation baseline is the frozen TimesFM 2.5 zero-shot model, not only
the naive forecasters.
```

项目对应：

```text
成功线：
MAE < 0.0796282537318497
SMAPE < 0.1877752198880728
```

## 4. LoRA Result

| Model | MAE | SMAPE |
|---|---:|---:|
| TimesFM 2.5 zero-shot | 0.0796282537318497 | 0.1877752198880728 |
| LoRA r4 step200 realized_vol_20 | 0.07865267778637558 | 0.18479685396576195 |

相对提升：

```text
MAE improved by 1.225163054258857%
SMAPE improved by 1.5861336357833395%
```

通俗解释：

```text
这次不是“有一项变好，一项变差”。
这次 MAE 和 SMAPE 都变好。
```

专业解释：

```text
The adapter produced metric-consistent out-of-sample improvement over the
zero-shot base model on this holdout split.
```

项目对应：

```text
这是 Time0 目前第一个 clean Candidate Success。
```

## 5. What "Candidate Success" Means

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它通过了第一场正式考试 | passed single holdout gate | Candidate Success |
| 还不能毕业 | not promotion-ready | needs rolling holdout |
| 不能马上发布 | not enough reproducibility evidence | no HF release yet |
| 下一步不是乱加训练 | validate stability first | rolling cut-points |

通俗说：

```text
它这次赢了。
但我们不能因为赢了一次就说它是强模型。
```

专业说：

```text
Single-split improvement is evidence of adaptation value, but not enough for
promotion or release.
```

项目对应：

```text
Candidate Success: yes.
Promotion Ready: no.
```

## 6. Why We Do Not Immediately Increase LoRA Rank

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先确认不是碰巧赢 | validate before scaling capacity | rolling holdout first |
| rank 越大越容易记答案 | larger adapter can overfit | `r=8` later, not now |
| 当前 r=4 已经有效 | minimal capacity worked | 0.5944% trainable params |
| 先保护实验结论 | preserve attribution | same recipe, new split |

通俗解释：

```text
现在不是马上把 LoRA 变大。
因为如果先变大，再换 holdout，结果变好或变差都不好解释。
```

专业解释：

```text
The next experiment should test temporal robustness before changing adapter
capacity, otherwise capacity and split effects are confounded.
```

项目对应：

```text
下一步：
same r=4 recipe
different chronological holdout cut-points
```

## 7. Next Experiment

| Cut-point | Purpose |
|---|---|
| `skip_windows=4000` | earlier holdout |
| `skip_windows=5000` | current holdout |
| `skip_windows=6000` | later holdout |

通俗说：

```text
换几套不同时间段的卷子。
如果都赢，说明它不是只碰巧赢了这一段。
```

专业说：

```text
Rolling chronological validation tests whether the adapter generalizes across
different market regimes.
```

项目对应：

```text
Promotion Ready 需要至少 3 个 rolling holdout cut-points。
```

## 8. What We Learned About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不是魔法，target 很关键 | target choice dominates adaptation quality | `level` failed, `realized_vol_20` worked |
| 小 adapter 也能有效 | parameter-efficient adaptation can shift behavior | 0.5944% trainable params |
| 赢一次只是候选 | single holdout is weak evidence | Candidate Success only |
| 下一步要考稳定性 | temporal robustness matters | rolling validation |

一句话：

```text
这轮第一次证明：TimesFM 2.5 LoRA 在我们的市场/宏观风险方向上，
有可能学到比原版 TimesFM 更专精的东西。
```

专业表达：

```text
The realized-volatility target produced the first metric-consistent
out-of-sample improvement over the frozen TimesFM 2.5 baseline.
```
