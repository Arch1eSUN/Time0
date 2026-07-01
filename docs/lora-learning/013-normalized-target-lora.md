# 013 - Normalized Target: Why Scale Fix Did Not Fix Cut5500

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-normalized.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把每门考试先换成同一种分数单位 | per-series target normalization | `realized_vol_20_zscore_train*` |
| 每条序列按自己的均值和波动大小换算 | train-window z-score | `(value - mean) / std` |
| 均值和标准差只从训练段算 | no holdout leakage | stats from train windows only |
| LoRA 配置不变，只改 target 尺度 | controlled experiment | `r=4, alpha=8, step=200` |

通俗解释：

```text
我们没有换模型，没有加大 LoRA，也没有换训练步数。
这一轮只问一个问题：

之前 cut5500 弱，是不是因为不同 series 的数字尺度差太大？
```

专业解释：

```text
This run isolates the effect of per-series train-window z-score normalization
on TimesFM LoRA domain adaptation.
```

项目对应：

```text
raw realized_vol_20 -> normalized realized_vol_20_zscore_train4000
raw realized_vol_20 -> normalized realized_vol_20_zscore_train5000
raw realized_vol_20 -> normalized realized_vol_20_zscore_train5500
```

## 2. What Is Normalization?

| 通俗版 | 专业版 | 项目里的样子 |
|---|---|---|
| 把不同单位的数字放到同一把尺子上 | feature/target scaling | 每个 series 自己算 mean/std |
| 不看原来是 0.1 还是 10，只看离平时多远 | standardization | z-score |
| 0 代表和平时差不多 | centered target | `value == train_mean` |
| 1 代表比平时高一个标准差 | one standard deviation above mean | `(value - mean) / std = 1` |
| -1 代表比平时低一个标准差 | one standard deviation below mean | `(value - mean) / std = -1` |

通俗解释：

```text
假设有两个学生：

学生 A 平时考 90 分，波动 5 分。
学生 B 平时考 60 分，波动 20 分。

原始分数里，90 看起来比 60 高很多。
但如果我们关心“今天是不是异常”，就要看它离自己的平时水平有多远。

A 考 95，是高了 1 个标准差。
B 考 80，也是高了 1 个标准差。

z-score 就是把“原始数字”换成“离自己平时有多远”。
```

专业解释：

```text
Z-score standardization transforms a value with:

z = (x - mean) / std

For this experiment, mean and std are computed separately for each series using
training-window future target values only.
```

项目对应：

```text
VIXCLS:realized_vol_20 有自己的 mean/std。
SP500:realized_vol_20 有自己的 mean/std。
DFF:realized_vol_20 有自己的 mean/std。

它们不会共用一个全局 mean/std。
```

## 3. Why Did We Use Training Windows Only?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 考试答案不能提前给学生看 | avoid data leakage | no holdout stats |
| 只能用训练段知道“平时水平” | fit transform on train split | train-window mean/std |
| 考试段只拿这个规则去换算 | apply train transform to holdout | same mean/std |
| 否则分数会虚高 | leakage inflates metrics | invalid backtest |

通俗解释：

```text
如果我们用 holdout 的均值和标准差来归一化 holdout，
就等于提前看了考试卷的整体难度。

那样模型看起来会更稳定，但这是作弊。
```

专业解释：

```text
The scaler is fitted on the training window distribution and then applied to
both training and holdout values.
```

项目对应：

```text
train4000:
  mean/std 从前 4000 个训练窗口的 future values 算
  holdout skip4000 也用这套 mean/std

train5500:
  mean/std 从前 5500 个训练窗口的 future values 算
  holdout skip5500 也用这套 mean/std
```

## 4. Why Normalized MAE Cannot Compare Directly With Raw MAE

| 错误理解 | 正确理解 |
|---|---|
| normalized MAE 0.5 比 raw MAE 0.08 差 | 不能这样比，单位不同 |
| raw MAE 是原始波动率单位 | raw-space error |
| normalized MAE 是标准差单位 | z-score-space error |
| 可以比较 LoRA vs zero-shot | same transformed target |
| 不能比较 normalized MAE vs raw MAE | different measurement scale |

通俗解释：

```text
raw MAE 像“错了多少美元”。
normalized MAE 像“错了多少个标准差”。

美元和标准差不是同一种单位。
所以不能说 0.5 标准差比 0.08 美元更差。

但同一场考试里：
zero-shot 错 0.52 标准差，
LoRA 错 0.50 标准差，
这就可以比。
```

专业解释：

```text
Absolute metric values are not comparable across different target
transformations. Relative improvement against the same baseline within the same
target space remains meaningful.
```

项目对应：

```text
可以看：
normalized LoRA MAE vs normalized zero-shot MAE

不能看：
normalized LoRA MAE vs raw LoRA MAE
```

## 5. Results

| Cut-point | Zero-shot MAE | LoRA MAE | MAE Improvement | SMAPE Improvement | Per-series MAE wins |
|---:|---:|---:|---:|---:|---:|
| 4000 | 0.498800980 | 0.491267123 | 1.510% | -0.697% | 7/10 |
| 5000 | 0.453603232 | 0.446293657 | 1.611% | 0.437% | 9/10 |
| 5500 | 0.520132411 | 0.521097160 | -0.185% | -0.269% | 3/10 |

通俗解释：

```text
归一化后，前两场考试 LoRA 还是略好。
但最关键的 cut5500，LoRA 还是没救回来。

这说明：
问题不只是“数字尺度不统一”。
```

专业解释：

```text
Per-series z-score normalization preserves some adaptation signal on cut4000
and cut5000, but fails on cut5500. Average MAE improvement drops to 0.978786%,
below the 2% Promotion Ready threshold.
```

项目对应：

```text
raw rolling avg MAE improvement:        1.515849%
normalized rolling avg MAE improvement: 0.978786%

normalized did not improve promotion readiness.
```

## 6. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不是魔法贴片 | LoRA is a low-rank adaptation layer | adapter changes limited parameters |
| 数据问题不一定靠训练解决 | data regime issues can dominate | cut5500 still weak |
| 只改尺度不等于理解新环境 | scaling is not regime modeling | normalization failed cut5500 |
| 训练成功不等于模型成功 | completed run is not validation | adapter saved but not promoted |

通俗解释：

```text
LoRA 像给大模型加一个小补丁。

如果问题是：
“这些序列的数字大小不一样”，
那归一化可能有帮助。

但如果问题是：
“市场环境变了，旧训练窗口和新 holdout 不是同一种环境”，
那光把数字换成同一把尺子不够。
```

专业解释：

```text
LoRA can adapt model behavior within the signal present in the fine-tuning
distribution. If holdout differs because of regime shift, simple scale
normalization may not provide the missing conditional structure.
```

项目对应：

```text
cut5500 不是简单 scale mismatch。
更像 regime mismatch 或 recency mismatch。
```

## 7. What Is Recency Mismatch?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 旧题刷太多，新题型没掌握 | stale training distribution | full-history train windows |
| 最近的市场环境更像考试 | recent data may be more predictive | recent-window training |
| 太旧的数据可能反而干扰 | negative transfer from old regime | cut5500 weakness |
| 下一步要少看旧题 | recency-limited fine-tuning | last 2000 windows before holdout |

通俗解释：

```text
如果考试考的是最近的新题型，
那让学生复习十年前的题，可能帮助不大。

甚至可能让他按旧套路答题，反而错。
```

专业解释：

```text
Recency mismatch means older training windows may have lower relevance to the
future holdout regime than more recent windows near the cut-point.
```

项目对应：

```text
下一轮不要先加 r=8。
下一轮先测试 recent-window LoRA：

只用每个 cutpoint 前最近的一段训练窗口，
例如最近 2000 个 balanced windows。
```

## 8. Decision After This Round

| 选项 | 结论 | 原因 |
|---|---|---|
| 发布 normalized adapter | 不发布 | average MAE gain < 2%，cut5500 失败 |
| 继续同配置训练更多 step | 不建议 | 当前问题不是训练没完成 |
| 直接上 `r=8` | 暂缓 | 还没证明容量是瓶颈 |
| 做 recent-window training | 建议 | 针对 regime/recency mismatch |
| 做 target dynamics | 候选 | 如 relative volatility / log-volatility |

本轮结论：

```text
Normalization is useful as a diagnostic, but not sufficient as the fix.
```

下一轮建议：

```text
field=realized_vol_20
training_window=recent-only
lora_r=4
max_steps=200
cutpoints=4000,5000,5500
```

要验证的问题：

```text
如果只用 holdout 前最近的数据训练，
LoRA 能不能改善 cut5500？
```
