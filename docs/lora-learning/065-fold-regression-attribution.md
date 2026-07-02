# 065 - Fold Regression Attribution

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-fold-regression-attribution.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再继续加 gate | stop post-hoc gating | consensus stopped |
| 找出哪一折坏了 | fold attribution | validation cuts |
| 找出谁在拖后腿 | error attribution | series/family |
| 找出坏窗口有什么特征 | feature contrast | runtime features |

通俗解释：

```text
前几轮我们一直在问：

  能不能设计一个更好的 gate？

这一轮换问题：

  到底是哪一段 validation 在坏？
  是哪个资产在坏？
  是哪个 adapter family 被错误 veto？
  坏窗口和好窗口的特征有什么不同？

这叫 attribution。
```

专业解释：

```text
This run performs fold-regression attribution. It keeps the selected
expected-regret configs fixed, reconstructs validation-fold veto decisions, and
decomposes metric delta by fold, series, original selected family, and runtime
feature contrasts.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/diagnose_expected_regret_fold_regressions.py

reports:
  reports/router-expected-regret-fold-regression-attribution-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-expected-regret-fold-regression-attribution-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A Fold Regression?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 某一段时间倒退 | fold regression | fold metric delta <= 0 |
| 总体好不代表每段都好 | aggregate can hide failure | combined validation |
| strict gate 要每段都不坏 | non-regression requirement | strict positive |
| 坏一折就不能进 final | holdout protection | fail closed |

通俗解释：

```text
validation 被切成几段时间：

  cut3750
  cut4000
  cut4250

如果一个 router：

  cut4000 好。
  cut4250 好。
  cut3750 坏。

那它总体可能还是好看的。

但 strict gate 不允许。
因为真实未来不保证刚好像表现好的那一段。
```

专业解释：

```text
A fold regression occurs when the candidate policy worsens the selected metric
on a chronological validation fold. The strict gate rejects any candidate with
fold_metric_regressions > 0 even if combined validation is positive.
```

项目对应：

```text
strict blocker:
  fold_metric_regressions > 0
```

## 3. How Row-Level Delta Works

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 每次 veto 都有收益或伤害 | per-window delta | selected error - fallback error |
| 正数是帮助 | positive delta | fallback better |
| 负数是伤害 | negative delta | adapter better |
| fold delta 是平均结果 | aggregate contribution | sum / fold windows |

通俗解释：

```text
如果 router 把某个窗口从 adapter 退回 fallback：

  adapter 错误 = 0.20
  fallback 错误 = 0.10

那么：

  delta = +0.10

这是帮助。

反过来：

  adapter 错误 = 0.10
  fallback 错误 = 0.20

那么：

  delta = -0.10

这是伤害。
```

专业解释：

```text
For each changed window, the diagnostic computes
original_selected_error - fallback_error. Positive values mean the veto
improves the metric; negative values mean the veto harms the metric.
```

项目对应：

```python
row_delta = family_error(row, original_family) - family_error(row, fallback_family)
```

## 4. No-Series Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只有一折坏 | one regression fold | cut3750 |
| VIX 是主要伤害源 | concentrated series harm | VIXCLS |
| recent3000 被错杀 | harmful veto source | original family recent3000 |
| trend alignment 很关键 | feature contrast | predicted trend minus past trend |

通俗解释：

```text
no-series 结果比之前清楚很多：

  不是每一折都坏。
  主要坏在 cut3750。

cut3750 里：

  154 个窗口被 veto。
  77 个帮助。
  77 个伤害。

数量一样，
但伤害更大。
所以这一折整体倒退。
```

专业解释：

```text
The no-series selected utility config has one fold regression. The failing
fold is cut3750 with metric_delta -0.0002406373. The veto has balanced
help/harm counts, but harm magnitude dominates.
```

项目对应：

```text
no-series selected config:
  l2: 0.0
  regret_threshold: -0.001
  positive_weight: 2.0

cut3750:
  metric_delta: -0.0002406373
  changed_windows: 154
  help_windows: 77
  harm_windows: 77
  sum_help_delta: +0.1112237212
  sum_harm_delta: -0.2315423740
```

## 5. No-Series Main Failure Sources

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| VIX 全部被伤害 | concentrated harmful series | VIXCLS 6/0 harm/help |
| SP500 也偏伤害 | broad series drag | SP500 35/15 |
| recent3000 不能乱退 | harmful original family | recent3000 |
| trend 差异明显 | alignment feature gap | trend-minus-past-trend |

通俗解释：

```text
cut3750 最明显的问题：

  VIXCLS 被 veto 的 6 个窗口全部是伤害。

另一个问题：

  原本选 recent3000 的窗口，
  被退回 fallback 后整体伤害最大。

这说明：

  对某些波动率 regime，
  recent3000 可能真的有价值。
  router 太容易把它退回 recent2000。
```

专业解释：

```text
The largest no-series fold harm is concentrated in VIXCLS and in vetoes away
from original family recent3000. Feature contrasts show harmed windows have
larger predicted-trend-minus-past-trend alignment values than helped windows.
```

项目对应：

```text
cut3750 worst series:
  VIXCLS: sum_delta -0.0780834848, harm/help 6/0
  SP500: sum_delta -0.0182753274, harm/help 35/15

cut3750 worst family:
  recent3000: sum_delta -0.1263973501, harm/help 15/10

feature contrast:
  recent1500_predicted_trend_minus_past_trend
    harmed_mean: +0.1638228940
    helped_mean: +0.0549151759
```

## 6. Series-Aware Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| series-aware 更不稳 | more regression folds | 2 folds |
| 最坏是 cut4000 | worst fold | -0.0003824223 |
| DFF 是主要伤害源 | concentrated series harm | DFF |
| recent1500 被错杀 | harmful original family | recent1500 |

通俗解释：

```text
series-aware 看起来更聪明，
因为它知道资产身份。

但这轮诊断说明：

  它更不稳。

它有两个 regression folds：

  cut3750
  cut4000

最坏的是 cut4000。
那里只有 10 个窗口被 veto，
但 8 个是伤害。
```

专业解释：

```text
The series-aware selected utility config has two regression folds. Its worst
fold is cut4000, where a small exposure set has strongly negative harm
magnitude, dominated by DFF and recent1500 vetoes.
```

项目对应：

```text
series-aware selected config:
  l2: 1.0
  regret_threshold: 0.002
  positive_weight: 4.0

cut4000:
  metric_delta: -0.0003824223
  changed_windows: 10
  help_windows: 2
  harm_windows: 8
  sum_help_delta: +0.0444639475
  sum_harm_delta: -0.2356750793
```

## 7. Series-Aware Main Failure Sources

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| DFF 主导 cut4000 伤害 | concentrated fold harm | DFF |
| recent1500 被错误退回 | original family harm | recent1500 |
| last-value alignment 很关键 | feature contrast | predicted last vs past last |
| 身份特征没有解决稳定性 | identity overfit risk | include-series |

通俗解释：

```text
cut4000 的伤害几乎被 DFF 拉下来：

  DFF 5 个窗口。
  总伤害 -0.1903805358。

这很大。

而且原本选 recent1500 的窗口被退回 fallback 后，
伤害也很大。

这说明：

  资产身份不是万能答案。
  知道这是 DFF 还不够。
  router 还需要知道 DFF 在什么 regime 下不能退。
```

专业解释：

```text
The series-aware failure is a small-exposure, large-magnitude failure. The
dominant harm comes from DFF and from vetoing recent1500. Feature contrasts
show harmed windows have much more negative predicted-last-vs-past-last
alignment than helped windows.
```

项目对应：

```text
cut4000 worst series:
  DFF: sum_delta -0.1903805358, harm/help 4/1

cut4000 worst family:
  recent1500: sum_delta -0.1773439093, harm/help 2/1

feature contrast:
  full_predicted_last_delta_from_past_last_over_std
    harmed_mean: -0.3460372675
    helped_mean: -0.0412065639
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 失败不是平均的 | localized failure | fold/series attribution |
| LoRA 有局部价值 | adapter-specific utility | recent1500/recent3000 |
| router 不能粗暴 fallback | harmful veto | adapter was better |
| 下一步要补特征 | feature gap | alignment-risk features |

通俗解释：

```text
现在我们更清楚了：

  问题不是 LoRA adapter 完全没用。

很多时候 adapter 是有用的。

问题是 router 有时把有用的 adapter 退回 fallback。

所以继续训练的重点不是：

  盲目多训 adapter。

而是：

  让 router 更懂什么时候 adapter 真的该保留。
```

专业解释：

```text
The failure mode is harmful fallback veto, not absence of adapter signal.
The selector needs richer no-leak features that distinguish safe fallback
regimes from regimes where the selected adapter should be preserved.
```

项目对应：

```text
current bottleneck:
  feature separability

candidate feature family:
  prediction-context alignment risk
  trend direction mismatch
  predicted-last displacement
```

## 9. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不继续调 gate | stop threshold chasing | no more post-hoc gates |
| 加 alignment-risk 诊断 | feature engineering | trend/last displacement |
| 先做 ablation | controlled test | strict validation |
| 看 fold regression 是否消失 | target metric | strict positive |

通俗解释：

```text
下一轮应该做：

  把 trend alignment 和 predicted-last displacement
  做成更明确的 no-leak risk features。

然后问：

  cut3750 的 VIXCLS 伤害是否减少？
  cut4000 的 DFF 伤害是否减少？
  fold_metric_regressions 能不能降到 0？

如果不能，
说明还缺别的信息。
```

专业解释：

```text
The next experiment should test alignment-risk features under the same strict
gate. The target is not higher aggregate validation lift; the target is zero
fold metric regressions without collapsing to all fallback.
```

项目对应：

```text
candidate next script:
  evaluate_alignment_risk_features.py

promotion condition:
  validation_strict_positive_count > 0
```
