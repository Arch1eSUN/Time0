# 012 - Distribution Shift: Why Cut5500 Is Weak

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-distribution-shift.md
```

## 1. What We Checked

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 看训练题和考试题是不是同一种题 | train/holdout distribution comparison | `summarize_series_distribution.py` |
| 看每个 series 的波动大小变没变 | per-series target distribution shift | `realized_vol_20` |
| 不只看模型错多少 | diagnose data regime before capacity | before `r=8` |
| 看 weak cutpoint 为什么弱 | explain cut5500 | mean/std/min/p50/p90/max |

通俗说：

```text
如果训练时看到的是一种市场环境，
考试时变成另一种市场环境，
模型变弱不一定是“模型太小”。
可能是题目分布变了。
```

专业说：

```text
Distribution shift means the target distribution in holdout differs from the
target distribution seen during training.
```

项目对应：

```text
cut5500 是 weakest rolling split。
所以我们先查 train5500 vs holdout5500 的 target distribution。
```

## 2. Overall Cutpoint Summary

| Cut-point | LoRA MAE Improvement | Holdout Mean Delta | Holdout Std Ratio |
|---:|---:|---:|---:|
| 4000 | 3.253180574182707% | 3.708459% | 1.186646 |
| 5000 | 1.225163054258857% | -1.994440% | 0.913917 |
| 5500 | 0.06920319934520795% | 5.950047% | 1.259878 |

通俗解释：

```text
cut5500 不是“环境没变但模型突然不行”。
cut5500 的 holdout 整体波动均值更高，波动离散程度也更高。
```

专业解释：

```text
The weakest split coincides with a higher aggregate holdout mean and higher
aggregate holdout variance.
```

项目对应：

```text
cut5500:
mean_delta_pct = +5.95%
std_ratio = 1.26x
```

## 3. Cut5500 Per-Series Shift

| Series | LoRA Improvement | Mean Delta | Std Ratio | 通俗判断 |
|---|---:|---:|---:|---|
| `DEXUSEU` | -2.037267% | -35.939341% | 0.403940 | 考试波动低很多、窄很多 |
| `DTWEXBGS` | -1.485192% | -49.670691% | 0.334922 | 考试波动低很多、窄很多 |
| `DGS10` | -1.142659% | -14.997429% | 0.455578 | 考试波动更低、更窄 |
| `DFF` | -0.045858% | 74.485666% | 1.355348 | 考试波动高很多、更散 |
| `SP500` | 1.403606% | 3.940449% | 0.433104 | 均值略高，但范围更窄 |
| `DGS2` | 1.911722% | -17.676788% | 0.334233 | 虽然更低更窄，但 LoRA 帮了 |

通俗解释：

```text
这不是一个统一变化。
大多数 series 变成“低波动、窄范围”。
DFF 却变成“高波动、更散”。
这叫混合 regime shift。
```

专业解释：

```text
Cut5500 contains heterogeneous regime shifts across series.
Most targets compress downward, while DFF expands sharply upward.
```

项目对应：

```text
cut5500 只有 3/10 个 series 变好。
它不是 release-grade robustness。
```

## 4. What This Means For LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不是马上把模型变大 | do not jump to capacity scaling | no immediate `r=8` |
| 先处理题目尺度变化 | normalize target distribution | per-series normalization |
| 先问数据是不是换环境了 | diagnose regime shift | cut5500 |
| 训练更多可能背错方向 | more capacity can overfit train regime | rank later |

通俗说：

```text
如果学生考试题型变了，
你不能第一反应就是“让他多刷 1000 道旧题”。
你应该先确认题型差在哪里。
```

专业说：

```text
Before increasing LoRA rank, normalize or otherwise control target scale and
regime mismatch.
```

项目对应：

```text
下一步不是 r=8。
下一步是 normalized realized_vol_20。
```

## 5. Next Experiment

| 选项 | 通俗解释 | 专业解释 | 先后顺序 |
|---|---|---|---|
| per-series normalization | 每个 series 先按自己的尺度标准化 | train-window z-score or scale normalization | 先做 |
| r=8 | 给 LoRA 更大容量 | larger adapter rank | 后做 |
| publish | 发布 adapter | Hugging Face release | 暂停 |

建议下一轮：

```text
field=realized_vol_20_normalized
normalization=per-series train-window z-score
lora_r=4
same cutpoints=4000,5000,5500
```

验证问题：

```text
normalized target 能不能提升 cut5500，同时不牺牲 cut4000/cut5000？
```

专业表达：

```text
The next controlled experiment should isolate normalization effects before
capacity effects.
```
