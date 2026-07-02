# 076 - Fold-Utility Selection

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-fold-utility-selection-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看总分 | fold-aware selection | `fold-utility` |
| 惩罚弱 validation fold | negative fold penalty | `negative_fold_metric_delta` |
| 先减少 fold regression | fold-stability first | fewer `fold_metric_regressions` |
| 不改训练数据 | selection-only experiment | same candidates |

通俗解释：

```text
上一轮最好结果的问题是：

  final 是正的，
  但 validation 里面有两个 fold 是负的。

这轮我们不重新训练模型。

我们只改变“从候选里挑谁”的规则：

  少一点 fold regression，
  哪怕总收益低一点。
```

专业解释：

```text
This run adds a fold-utility validation objective. It ranks robust candidates
by fold stability before aggregate validation lift.
```

项目对应：

```bash
--selection-objective fold-utility
```

## 2. What Is A Fold?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一段时间考试 | chronological validation fold | cut3750 / cut4000 / cut4250 |
| 多段都稳才可信 | temporal robustness | fold-level validation |
| 某段亏就是 fold regression | fold metric regression | fold delta <= 0 |
| 只靠总分可能遮住问题 | aggregate hides instability | combined metric delta |

通俗解释：

```text
validation 不是一张总试卷。

它分成几段时间：

  cut3750
  cut4000
  cut4250

如果总分好，
但其中两段都亏，
那说明它不是稳定规律。
```

专业解释：

```text
Fold validation measures chronological transfer. A candidate can be aggregate
positive while still failing earlier validation regimes.
```

## 3. The Fold-Utility Score

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总收益减掉亏损 fold | penalized validation utility | `fold_utility_score` |
| 只惩罚负 fold | downside-only fold penalty | `negative_fold_metric_delta` |
| 正 fold 仍保留 | aggregate lift retained | `combined_metric_delta` |
| 先看 regression 数量 | fold count priority | `fold_metric_regressions` |

通俗解释：

```text
score 的逻辑是：

  总体赚了多少
  减去每个亏损 fold 的亏损

如果一个候选总收益高，
但两个 fold 亏，
它会被扣分。
```

专业解释：

```text
fold_utility_score = combined_metric_delta + sum(negative fold metric deltas)
```

项目对应：

```text
combined_metric_delta: +0.0002618032
negative_fold_metric_delta: -0.0001016381
fold_utility_score: +0.0001601650
```

## 4. What Happened

| Surface | Objective | Fold regressions | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---|
| no-series previous | combined | 2 | 81 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | fold-utility | 1 | 16 | -0.0000119835 | not_validated_final_underexposed |
| include-series | fold-utility | 2 | 1 | +0.0000001652 | not_validated_final_underexposed |

通俗解释：

```text
fold-utility 确实做到了它想做的事：

  validation 负 fold 从 2 个变成 1 个。

但代价太大：

  final 出手从 81 次掉到 16 次。
  final delta 从正变负。

所以这不是进步。
```

专业解释：

```text
Selection-only fold repair chose a more conservative candidate. It improved
one validation stability statistic but reduced final intervention coverage and
hurt final holdout metric delta.
```

## 5. Why This Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 选得更稳不等于更强 | selection stability can overfit | fold-utility failed final |
| final exposure 不能丢 | intervention coverage required | 16 < 20 |
| 修 validation 不能牺牲 final | transfer tradeoff | final delta negative |
| 不能只调排序 | ranking is not enough | candidate pool limit |

通俗解释：

```text
这轮告诉我们：

  只是在已有候选里换排序，
  解决不了真正问题。

我们需要的是：

  候选本身更好。

也就是训练目标或特征要变，
不是只改怎么挑。
```

专业解释：

```text
The candidate pool lacks a policy that simultaneously preserves validation
fold stability, final exposure, and positive final delta. Selection-only
optimization cannot create that policy.
```

## 6. What We Learned

Fact: Fold-utility selection reduced no-series validation fold regressions from
2 to 1.

Fact: It reduced final changed windows from 81 to 16 and made final delta
negative.

Fact: Include-series remained underexposed.

Inference: The positive-quantile candidate pool has a real exposure/stability
tradeoff. The best final candidate is not the best fold-utility candidate.

Recommendation: Stop selection-only repairs. Next, modify the training target
or add fold-aware features so the model can learn why cut3750/cut4000 regress
without throwing away final exposure.
