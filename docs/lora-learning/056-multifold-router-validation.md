# 056 - Multi-Fold Router Validation

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-multifold-feature-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再只用一个未来段考试 | multi-fold chronological validation | `3750/4000/4250` |
| 先用早期数据产生候选规则 | initial discovery split | `cut <= 3500` |
| 再用中间时间段挑规则 | validation folds | rule selection gate |
| 最后才碰真正 holdout | final holdout | `cut > 4250` |

通俗解释：

```text
上一轮的问题是：

  我们用 cut3500 前的数据找规则，
  然后直接看 cut3500 后的未来。

这比事后看答案好，
但还是有点粗。

这一轮我们把时间切得更像真实研发流程：

  第一段：找候选规则
  第二段：用几个中间时间点挑规则
  第三段：最后考试

这样做的目的：

  减少“刚好在某一个时间点看起来不错”的运气。
```

专业解释：

```text
This run introduces chronological multi-fold validation. Candidate rules are
generated on an initial discovery split, selected on intermediate validation
folds, and evaluated once on a later final holdout.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_feature_veto.py

report:
  reports/router-feature-veto-multifold-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. Why Multi-Fold Validation Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一个时间点赢，可能是碰巧 | single split instability | previous feature veto |
| 多个时间点都不坏，证据更强 | temporal robustness | validation folds |
| 规则选择不能看最终 holdout | no final-holdout tuning | final split untouched |
| 它更接近真实上线前流程 | staged policy selection | discovery -> validation -> holdout |

通俗解释：

```text
如果我们只看一个时间点：

  规则 A 看起来很好。

但它可能只是刚好适合那一段市场。

multi-fold 的意思是：

  让规则连续过几道时间门。

它不要求每一关都完美，
但至少要证明：

  不是只在一个时间点偶然有效。
```

专业解释：

```text
Multi-fold validation reduces selection variance. A rule must survive several
chronologically ordered validation folds before being frozen for the final
holdout.
```

项目对应：

```text
initial discovery:
  cut <= 3500

validation folds:
  cut3750
  cut4000
  cut4250

final holdout:
  cut > 4250
```

## 3. The Selected Rule Changed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 单 cut 最爱 raw past trend | single-split rule | `context.past_trend` |
| multi-fold 选了预测和上下文的偏离 | prediction-context alignment | recent3000 last delta over std |
| 这说明选择 gate 有作用 | validation changed selected policy | different rule |
| 它更像 router 信号，不只是历史趋势 | candidate forecast alignment signal | adapter prediction shape |

通俗解释：

```text
上一轮最好的规则是：

  过去趋势很负时，退回 fallback。

这一轮 multi-fold 选出的规则变了：

  recent3000 adapter 的预测最后一个点，
  相对过去最后一个点偏离太大时，
  更保守。

这说明：

  多折验证不是摆设。
  它真的改变了我们会选择的规则。
```

专业解释：

```text
The selected rule moved from a raw context feature to a prediction-context
alignment feature. This suggests that validation folds prefer a signal about
candidate forecast shape relative to the context, not only the context regime
itself.
```

项目对应：

```text
selected_rule:
  prediction_context_alignment.recent3000_predicted_last_delta_from_past_last_over_std
  >= 0.7595631100372521
```

## 4. Validation Fold Results

| Fold | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| cut3750 | 变好，风险也变好 | metric positive, negative series reduced | `1 -> 0` |
| cut4000 | 小幅变差，但风险没变差 | metric negative, downside neutral | `1 -> 1` |
| cut4250 | 变好，风险没变差 | metric positive, downside neutral | `3 -> 3` |

通俗解释：

```text
这条规则不是每一折都赚钱。

cut4000 是小幅变差的。

但它有两个重要特点：

  1. 三个 validation folds 合起来是正的。
  2. 没有任何一折增加 negative series。

所以它比上一轮单特征规则更稳。
```

专业解释：

```text
The validation gate selected a rule with positive combined validation metric
delta, zero combined negative-series regression, and zero fold-level
negative-series regressions. It still has one fold-level metric regression.
```

项目对应：

```text
combined_metric_delta:
  +0.0000602569

combined_negative_series_delta:
  0

fold_negative_regressions:
  0

fold_metric_regressions:
  1
```

## 5. Final Holdout Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最后考试里，小幅打赢当前 router | incremental improvement | metric delta +0.0000160188 |
| 没有增加亏损 series | no downside regression | negative series 2 -> 2 |
| 但仍然输给 fixed fallback | below fallback | relative lift negative |
| 所以不能发布 | not promotion-ready | blocked |

通俗解释：

```text
最终 holdout 的结果要分两层看：

  跟当前 router 比：
    变好了一点。

  跟 fallback 比：
    还是没打过。

这就像：

  原来考 58 分，
  现在考 59 分。

它是进步，
但不是及格。
```

专业解释：

```text
The final holdout validates an incremental policy improvement over the current
router selection, with no increase in negative series. However, the selected
feature-veto router remains below the fixed fallback, so it is not releasable.
```

项目对应：

```text
final_holdout:
  windows: 2500
  changed_windows: 9
  metric_delta: +0.0000160188
  negative_series: 2 -> 2

relative_lift_vs_fallback:
  original router: -0.144159%
  feature veto:   -0.127235%

overall verdict:
  incremental_positive_but_below_fallback
```

## 6. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 有信号，但 router 还弱 | adapter signal exists, policy weak | candidate families |
| multi-fold gate 比单 cut 更靠谱 | validation gate improves selection | selected rule changed |
| 单规则能改进一点，但不够深 | shallow policy has limited depth | 9 final changed windows |
| 下一步应该加深 router，不是乱加训练步数 | richer policy before rank/step escalation | multi-feature router |

通俗解释：

```text
现在我们看到一个更清楚的形状：

  LoRA adapter 家族不是完全没用。
  router 也确实能被 no-leak feature 改善一点。

但单一规则太浅。

它只能改 9 个 final holdout 窗口，
而且还没超过 fallback。

所以继续训练 LoRA rank 或 steps，
不一定是最高价值方向。

更该做的是：

  让 router 能同时看多个特征，
  并且用 multi-fold gate 选择。
```

专业解释：

```text
The bottleneck is now the router policy class. Multi-fold validation provides a
better selection seam, but a single-threshold policy lacks enough depth to beat
the fixed fallback on final holdout.
```

项目对应：

```text
candidate families:
  zero-shot
  full
  recent1500
  recent2000
  recent3000

current policy class:
  single-feature fallback veto

next policy class:
  multi-feature router or two-feature veto
```

## 7. The Important Lesson

Fact:

```text
Multi-fold validation selected a different rule than single-cut discovery.
```

Fact:

```text
The selected rule improves final holdout relative to the current router and
does not increase negative series.
```

Fact:

```text
The selected rule still remains below fixed fallback on final holdout.
```

Inference:

```text
Multi-fold validation is the right selection gate, but single-feature veto is
too shallow for release.
```

Recommendation:

```text
Keep the multi-fold gate. Next, test a richer router policy under the same gate:
two-feature veto first, then a small supervised router if two-feature rules are
still below fallback.
```

