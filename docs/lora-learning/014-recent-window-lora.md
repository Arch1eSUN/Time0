# 014 - Recent-Window Training: Why Newer Data Helped Cut5500

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-recent-window.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 少看很旧的题 | recency-limited fine-tuning | `recent2000` |
| 只看考试前最近一段训练题 | rolling recent train window | `skip_windows=cutpoint-2000` |
| LoRA 配置不变 | controlled experiment | `r=4, alpha=8, step=200` |
| holdout 不变 | same chronological evaluation | `skip4000/5000/5500` |

通俗解释：

```text
上一轮 normalization 失败后，我们怀疑问题不是“数字尺度不同”，
而是“训练里旧环境太多，考试是新环境”。

所以这一轮不改变模型大小，只改变训练材料：
不再从最早开始训练，而是只用考试前最近的 2000 个窗口。
```

专业解释：

```text
This run tests whether reducing stale historical data improves out-of-sample
adaptation under regime shift.
```

项目对应：

```text
cut4000: train windows 2000-3999, holdout starts at 4000
cut5000: train windows 3000-4999, holdout starts at 5000
cut5500: train windows 3500-5499, holdout starts at 5500
```

## 2. What Is A Recent Window?

| 通俗版 | 专业版 | 项目里的样子 |
|---|---|---|
| 只复习考试前最近的题 | recency-limited training set | last N windows before holdout |
| 不让太旧的题干扰 | reduce stale-regime exposure | skip older windows |
| 不是随机抽题 | chronological split is preserved | no leakage |
| 不是训练更少一定更好 | window length is a hyperparameter | `recent2000`, next `recent3000` |

通俗解释：

```text
如果考试考的是最近市场环境，
十年前的题可能不但帮不上忙，还会把答题习惯带偏。

recent-window 的意思是：
离考试越近的数据越可能有用，
太早的数据先不让 LoRA 学。
```

专业解释：

```text
A recent-window train split uses only the latest N chronological training
windows before the holdout cut-point. It keeps temporal ordering and avoids
holdout leakage.
```

项目对应：

```text
full-history train4000:
  skip_windows=0
  max_windows=4000

recent2000 train4000:
  skip_windows=2000
  max_windows=2000
```

## 3. Why This Is Different From Normalization

| 问题假设 | 实验 | 结果 |
|---|---|---|
| 数字尺度不统一 | normalization | cut5500 没修好 |
| 旧环境干扰新环境 | recent-window | cut5500 明显改善 |
| LoRA 容量不够 | larger rank | 还没测试，不应先跳 |

通俗解释：

```text
normalization 是换尺子。
recent-window 是换复习材料。

上一轮说明“尺子”不是主要问题。
这一轮说明“复习材料太旧”确实影响结果。
```

专业解释：

```text
Normalization controls scale mismatch. Recent-window training controls exposure
to stale regimes. The recent-window result gives stronger evidence for recency
mismatch than for simple scale mismatch.
```

项目对应：

```text
normalized cut5500 MAE improvement: -0.185%
recent2000 cut5500 MAE improvement: 2.011%
```

## 4. Results

| Cut | Zero-shot MAE | Full-history LoRA MAE | Full gain | Recent2000 LoRA MAE | Recent gain | Recent wins |
|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.117591233 | 0.113765778 | 3.253% | 0.114672099 | 2.482% | 6/10 |
| 5000 | 0.079628254 | 0.078652678 | 1.225% | 0.079087892 | 0.679% | 7/10 |
| 5500 | 0.131079191 | 0.130988480 | 0.069% | 0.128443571 | 2.011% | 5/10 |

通俗解释：

```text
好消息：
最弱的 cut5500 被救起来了。

坏消息：
cut4000 和 cut5000 的收益变小了。

所以 recent2000 不是最终答案，
但它证明“看更新的数据”这个方向有用。
```

专业解释：

```text
Recent2000 improves the hardest split but trades off some performance on the
earlier splits. Average MAE improvement rises from full-history 1.515849% to
recent2000 1.723918%, still below the 2% Promotion Ready threshold.
```

项目对应：

```text
full-history average MAE improvement: 1.515849%
recent2000 average MAE improvement:   1.723918%
Promotion Ready threshold:            2.000000%
```

## 5. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 学的是你给它看的材料 | adapter behavior follows fine-tuning distribution | train window matters |
| 旧数据太多会带偏 | negative transfer from stale regimes | cut5500 full-history weak |
| 数据窗口本身是超参数 | training window length is a hyperparameter | `recent2000` vs full-history |
| 不能只看平均值 | robustness needs per-series checks | 5/10 wins at cut5500 |

通俗解释：

```text
LoRA 不是自己知道哪些数据该信、哪些数据该忘。
你给它很多旧环境，它就会把旧环境也学进去。

所以“训练多少数据”不是越多越好。
更准确地说：
训练数据要和未来考试环境有关。
```

专业解释：

```text
For non-stationary time series, more historical data can introduce stale-regime
negative transfer. Recency-limited fine-tuning can improve adaptation when the
holdout regime is closer to recent history than to the full historical average.
```

项目对应：

```text
cut5500:
  full-history LoRA MAE gain = 0.069%
  recent2000 LoRA MAE gain  = 2.011%
```

## 6. Why We Still Cannot Publish

| 条件 | 当前状态 |
|---|---|
| 3 个 cutpoint 都赢 zero-shot | 是 |
| 平均 MAE 改善 >= 2% | 否，1.723918% |
| per-series 不被少数序列支配 | 还不够，cut5500 只有 5/10 |
| 结果可复现并有 run note | 是 |
| 可以作为 Moirai adapter | 暂时不行 |

通俗解释：

```text
这轮像是找到了一条更对的路，
但还没有到终点。

它不是失败。
它是证据：
下一步应该调训练窗口长度，而不是盲目加大 LoRA。
```

专业解释：

```text
Recent-window training improved the bottleneck split but did not satisfy the
Promotion Ready average-improvement gate.
```

项目对应：

```text
Do not publish.
Do not move to Moirai integration.
Do not jump to r=8 yet.
```

## 7. Next Round

| 选项 | 结论 | 原因 |
|---|---|---|
| `recent2000` 发布 | 不发布 | 平均收益未过 2% |
| `recent3000` | 建议 | 可能保留 cut5500 改善，同时恢复 cut4000/5000 |
| `r=8` | 暂缓 | 训练窗口还没调完 |
| normalized target | 已测 | 没修好 cut5500 |
| full-history | 保留参照 | 稳但 cut5500 太弱 |

下一轮建议：

```text
field=realized_vol_20
training_window=recent3000
lora_r=4
max_steps=200
cutpoints=4000,5000,5500
```

要验证的问题：

```text
recent3000 能不能同时保留 cut5500 的修复，
并恢复 cut4000/cut5000 的收益？
```
