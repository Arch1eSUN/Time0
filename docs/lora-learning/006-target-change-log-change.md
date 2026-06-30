# 006 - Changing The Target: Level vs Log Change

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-log-change-h20-r4.md
```

## 1. What We Changed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再预测“数值是多少” | Change target from raw level | `field=level` -> `field=log_change` |
| 改成预测“变化了多少” | Use return-like transformed target | `log(current / previous)` |
| 其他训练设置不乱动 | Controlled experiment | `r=4`, `alpha=8`, `max_steps=200` unchanged |

上一轮我们预测的是 `level`。

通俗说：

```text
预测 VIX 是 20 还是 25
预测 SP500 是 5000 还是 5100
预测利率是 4.2 还是 4.3
```

专业说：

```text
raw level forecasting
```

这一轮我们预测的是 `log_change`。

通俗说：

```text
预测它涨了多少比例，或者跌了多少比例
```

专业说：

```text
log-return-like transformed target
```

## 2. Why Change The Target?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不同东西的单位差太远 | Raw targets have heterogeneous scales | SP500 thousands, VIX tens, rates single digits |
| 模型可能被大数字带偏 | Scale imbalance can distort loss and adaptation | `level` adapter failed holdout |
| 变化率更像统一语言 | Returns normalize across assets/series | `log_change` |

Raw level 的问题：

```text
SP500: 5000 左右
VIX: 10-80 左右
利率: 0-6 左右
汇率: 1 或 100+ 左右
```

通俗说：

```text
一张卷子里混着米、厘米、吨、美元，模型很难统一学习。
```

专业说：

```text
The target distribution is scale-heterogeneous across series.
```

`log_change` 的好处：

```text
大家都变成“相对变化”。
```

专业说：

```text
It converts levels into a return-like representation.
```

## 3. What Stayed The Same?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 还是同一本小笔记本大小 | Same LoRA capacity | `r=4` |
| 还是同样训练强度 | Same LoRA scaling | `alpha=8` |
| 还是训练 200 步 | Same training budget | `max_steps=200` |
| 还是看过去 128 步 | Same context length | `context_len=128` |
| 还是预测未来 20 步 | Same forecast horizon | `horizon_len=20` |

为什么要保持这些不变？

通俗说：

```text
一次只改一个东西，才知道是谁造成结果变化。
```

专业说：

```text
This is a controlled experiment.
```

这次唯一主要变化：

```text
target field changed from level to log_change.
```

## 4. What Did We Train?

Adapter:

```text
adapters/market-macro-log-change-h20-r4-step200-balanced
```

Training split:

```text
training windows = first 5000 balanced windows
holdout windows = next 500 balanced windows
```

通俗说：

```text
先做 5000 道作业，再考后面的 500 道新题。
```

专业说：

```text
Train on skip_windows=0/max_windows=5000, evaluate on skip_windows=5000/max_windows=500.
```

## 5. Baselines

Holdout baselines:

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 0.02846349734552 | 1.3721631236138991 |
| Seasonal naive | 0.026348636656100002 | 1.342713152518601 |
| TimesFM zero-shot | 0.01852017978944989 | 1.7846263993121316 |

通俗解释：

```text
简单猜法 MAE 约 0.026-0.028。
原版 TimesFM MAE 约 0.0185。
原版 TimesFM 在绝对误差上明显更强。
```

专业解释：

```text
TimesFM zero-shot outperformed naive baselines on MAE for log_change holdout.
```

注意：

```text
SMAPE 在 log_change 上很难看。
```

为什么？

通俗说：

```text
变化率经常接近 0，分母太小，相对误差会被放大。
```

专业说：

```text
SMAPE is unstable for near-zero targets.
```

## 6. LoRA Result

| Model | MAE | SMAPE |
|---|---:|---:|
| TimesFM zero-shot | 0.01852017978944989 | 1.7846263993121316 |
| LoRA log_change r4 step200 | 0.018340936770009884 | 1.8129117903524623 |

通俗解释：

```text
LoRA 平均绝对错误小了一点。
但相对误差变差了一点。
```

专业解释：

```text
The adapter improved MAE but regressed SMAPE.
```

项目判断：

```text
This is a partial win, not a clean win.
```

## 7. How To Read This Result

| 通俗判断 | 专业判断 | 项目结论 |
|---|---|---|
| 它有一点进步 | MAE improved | `0.01852 -> 0.01834` |
| 但不是全面进步 | SMAPE regressed | `1.7846 -> 1.8129` |
| 不能上线 | Not promotion-ready | adapter stays experimental |
| 方向比 level 好一点 | target is more promising | test `realized_vol_20` next |

这次和 `level` 的区别：

```text
level: LoRA 在 holdout 上明显输给 zero-shot
log_change: LoRA 在 MAE 上小赢 zero-shot，但 SMAPE 输
```

通俗说：

```text
level 路线是“不太行”。
log_change 路线是“有点苗头，但还不稳”。
```

专业说：

```text
The transformed target improved absolute error behavior but did not deliver metric-consistent generalization.
```

## 8. New Tooling Lesson

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 工具启动太慢 | Import-time dependency regression | Transformers 5.12.1 dynamic model scan |
| 我们只需要 TimesFM 和 PEFT | Narrow required import surface | `TimesFm2_5ModelForPrediction`, PEFT LoRA |
| 加了本地修补脚本 | Local environment patch | `scripts/patch_transformers_fast_import.py` |

发生了什么：

```text
Transformers import 卡在扫描所有模型模块。
```

专业说：

```text
The package performed dynamic import-structure scanning across all model modules.
```

我们做了什么：

```text
限制 lazy import metadata 到本实验需要的 TimesFM 2.5 + PEFT AutoModel/Bloom entries。
```

为什么这重要：

```text
可重复实验不只是模型代码，也包括工具链能稳定启动。
```

## 9. What To Do Next

不要做：

```text
直接把 log_change adapter 当成成功
直接上 r=8
直接加到 1000 steps
```

应该做：

```text
下一轮测试 field=realized_vol_20
保持 r=4
保持 holdout split
比较 zero-shot vs LoRA
```

为什么：

通俗说：

```text
我们真正想做 market-macro-risk，波动率比涨跌变化更接近“风险”。
```

专业说：

```text
realized_vol_20 is better aligned with the domain objective than raw level or one-step log change.
```

## 10. One-Sentence Summary

通俗版：

```text
这次换成预测“变化率”以后，LoRA 在平均错误上小赢原模型，但不是全面赢，所以只能算有苗头，不能算成功。
```

专业版：

```text
Changing the target to `log_change` produced a partial MAE improvement over TimesFM zero-shot, but SMAPE regressed, so the adapter remains experimental and the next target should be `realized_vol_20`.
```
