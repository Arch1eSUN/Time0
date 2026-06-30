# 010 - Rolling Validation Without Data Leakage

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-rolling.md
```

## 1. What We Fixed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不能用看过的题当考试 | avoid train/eval leakage | no overlap between train and holdout |
| 一个时间点要一个对应模型 | train one adapter per cut-point | cut4000, cut5000, cut5500 |
| 太晚的数据不平衡就先不用 | keep holdout balanced | skip6000 rejected |
| 赢一次不够，要换时间段考 | rolling chronological validation | 3 balanced cut-points |

通俗说：

```text
如果模型已经做过 0-5000 的练习题，
我们不能再拿 4000-4500 当考试题。
这叫偷看答案。
```

专业说：

```text
Evaluating a model on windows that overlap its training region causes data
leakage and invalidates the holdout result.
```

项目对应：

```text
cut4000: train 0-4000, eval 4000-4500
cut5000: train 0-5000, eval 5000-5500
cut5500: train 0-5500, eval 5500-6000
```

## 2. Why We Did Not Use `skip_windows=6000`

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 有的 series 题不够了 | holdout became imbalanced | BAMLH0A0HYM2 only had 18 windows |
| 不公平的考试会误导判断 | imbalance can distort aggregate metrics | use 5500 instead |
| 先保持实验干净 | controlled validation | 50 windows per series |

通俗说：

```text
如果 10 个科目里，9 个科目各考 50 题，一个科目只考 18 题，
总分会变得不稳定。
```

专业说：

```text
Uneven per-series window counts can bias aggregate metrics toward series with
more available examples.
```

项目对应：

```text
skip5500: 10 series x 50 windows
skip6000: not balanced
```

## 3. Rolling Results

| Cut-point | Zero-shot MAE | LoRA MAE | MAE Improvement | Zero-shot SMAPE | LoRA SMAPE | SMAPE Improvement |
|---:|---:|---:|---:|---:|---:|---:|
| 4000 | 0.11759123320482111 | 0.11376577804925998 | 3.253180574182707% | 0.19646661915877023 | 0.1941615794770051 | 1.173247491932641% |
| 5000 | 0.0796282537318497 | 0.07865267778637558 | 1.225163054258857% | 0.1877752198880728 | 0.18479685396576195 | 1.5861336357833395% |
| 5500 | 0.13107919061242465 | 0.13098847961884505 | 0.06920319934520795% | 0.21800550932341226 | 0.2179365651864745 | 0.03162495165912306% |

Average:

```text
MAE improvement: 1.5158489425955908%
SMAPE improvement: 0.9303353597917012%
```

通俗解释：

```text
三场考试都赢了，但第三场只赢了一点点。
平均成绩还没达到我们规定的“可以发布”的线。
```

专业解释：

```text
The adapter family shows positive rolling signal, but does not satisfy the
Promotion Ready threshold.
```

项目对应：

```text
Direction: promising.
Release: blocked.
```

## 4. Candidate Success vs Promotion Ready

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它不是废的 | positive adaptation signal | all 3 cut-points improved |
| 它还不够强 | below promotion threshold | average MAE gain 1.52%, target is 2% |
| 不能发布 | not release-ready | no HF adapter yet |
| 下一步要查细节 | need attribution | per-series metrics |

通俗说：

```text
这个方向值得继续。
但如果现在发布，我们是在把一个“有苗头”的模型包装成“稳定变强”的模型。
这不严谨。
```

专业说：

```text
Positive aggregate improvement is insufficient for release when the average
gain is below threshold and per-series distribution is unknown.
```

项目对应：

```text
realized_vol_20 = best target so far
promotion_ready = false
```

## 5. What We Learned About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 能让模型往目标领域偏一点 | LoRA can adapt behavior with few trainable params | all cut-points improved |
| 小赢也要小心 | small gains may not be robust enough | cut5500 only +0.07% MAE |
| 实验设计比训练次数重要 | validation design controls evidence quality | leakage fix mattered |
| 下一步要看每个 series | aggregate metrics hide distribution | per-series eval needed |

一句话：

```text
这轮证明方向有价值，但还不能发布。
```

专业表达：

```text
The adapter family passed a positive rolling-signal check but failed the
Promotion Ready gate due to insufficient average improvement and missing
per-series attribution.
```

## 6. Next Step

通俗说：

```text
不要急着把 LoRA 变大。
先看它到底在哪些 series 上变强，哪些 series 上没变强。
```

专业说：

```text
Before increasing adapter capacity, add per-series metrics to determine whether
the gains are broad or concentrated.
```

项目对应：

```text
Next implementation:
evaluate_timesfm.py -> per_series metrics
evaluate_naive.py -> per_series metrics
rerun realized_vol_20 rolling reports
```
