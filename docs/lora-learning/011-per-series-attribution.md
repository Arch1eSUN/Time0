# 011 - Per-Series Attribution: Where Did LoRA Help?

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-per-series.md
```

## 1. What We Added

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看总分 | add disaggregated metrics | `per_series` |
| 看每个 series 单独变好还是变差 | per-series attribution | 10 market/macro series |
| 找出是谁贡献提升 | decompose aggregate improvement | cut4000/cut5000/cut5500 |
| 找出是谁拖后腿 | identify regressions | weak series and weak regime |

通俗说：

```text
以前我们只知道全班平均分变好了。
现在要看每个学生的分数。
```

专业说：

```text
Aggregate metrics can hide heterogeneous behavior across series.
Per-series attribution shows whether adaptation is broad or concentrated.
```

项目对应：

```text
evaluate_naive.py -> per_series
evaluate_timesfm.py -> per_series
```

## 2. Why This Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总分赢不代表每个都赢 | aggregate win can hide regressions | cut5500 |
| 发布模型要知道风险 | model card needs limitations | weak series disclosure |
| 不能盲目加 rank | capacity change can mask diagnosis | do not jump to r=8 |
| Moirai 更需要可信证据 | downstream forecast seam needs provenance | evidence-first |

通俗说：

```text
如果模型只是在 2 个 series 上大赢，
但在 8 个 series 上小输，
总分可能还不错，但这不是稳定模型。
```

专业说：

```text
Promotion requires distributional evidence, not only aggregate metric uplift.
```

项目对应：

```text
Promotion Ready 仍然 blocked。
```

## 3. Per-Series Result

| Series | Cut4000 | Cut5000 | Cut5500 | Average |
|---|---:|---:|---:|---:|
| `DEXUSEU` | -2.627553% | 0.624542% | -2.037267% | -1.346759% |
| `DGS10` | 0.253103% | 0.283125% | -1.142659% | -0.202144% |
| `DGS2` | -2.644006% | 1.568999% | 1.911722% | 0.278905% |
| `VIXCLS` | 0.277337% | 0.673529% | -0.095068% | 0.285266% |
| `DTWEXBGS` | 2.226942% | 1.497981% | -1.485192% | 0.746577% |
| `SP500` | 1.601611% | -0.000741% | 1.403606% | 1.001492% |
| `BAMLH0A0HYM2` | -0.162285% | 3.042571% | 0.469182% | 1.116489% |
| `DCOILWTICO` | 1.067360% | 3.455488% | -0.174774% | 1.449358% |
| `DFF` | 5.769349% | 0.754525% | -0.045858% | 2.159339% |
| `DEXJPUS` | 4.233439% | 3.674496% | -0.048423% | 2.619837% |

通俗解释：

```text
8 个 series 平均是正的。
2 个 series 平均是负的。
但 cut5500 这一场只有 3 个 series 变好。
```

专业解释：

```text
The adapter has broad but shallow positive signal, with a late-cutpoint
generalization weakness.
```

项目对应：

```text
realized_vol_20 方向保留。
发布继续 blocked。
```

## 4. What Cut5500 Tells Us

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 第三场考试几乎没赢 | cut5500 uplift is marginal | MAE +0.069% |
| 只有 3 个 series 赢 | improvement is not broad | BAMLH0A0HYM2, SP500, DGS2 |
| 7 个 series 小输 | regressions are distributed | weak temporal robustness |
| 不能直接发布 | not stable enough | Promotion Ready = false |

通俗说：

```text
这不是“模型失败”。
这是“模型还不够稳”。
```

专业说：

```text
The model passes positive-signal criteria but fails promotion-grade robustness.
```

项目对应：

```text
下一步不是发布，也不是直接 r=8。
下一步是诊断 cut5500 为什么弱。
```

## 5. What We Learned About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 可能只帮一部分数据 | adaptation can be heterogeneous | per-series mixed |
| 平均分会骗人 | aggregate metrics hide regressions | cut5500 |
| 微调前要会评估 | evaluation depth matters before training scale | per_series before r=8 |
| 发布要讲限制 | release needs limitations | model card later |

一句话：

```text
LoRA 不是只看总分；要看它到底帮了谁、伤了谁。
```

专业表达：

```text
Per-series attribution is required to distinguish broad adaptation from
aggregate-only improvement.
```

## 6. Next Step

通俗说：

```text
先查 cut5500 的环境是不是变了。
比如那段时间哪些 series 波动结构不同，哪些目标尺度变了。
```

专业说：

```text
Next, analyze series-level target distributions and regime shifts before
changing LoRA capacity.
```

项目对应：

```text
Next implementation:
add per-series distribution summary for realized_vol_20
compare train vs holdout target mean/std/min/max
then decide whether r=8 is justified
```
