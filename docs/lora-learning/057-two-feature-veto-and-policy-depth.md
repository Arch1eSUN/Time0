# 057 - Two-Feature Veto And Policy Depth

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-two-feature-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 单特征规则太浅，所以试两个特征一起判断 | two-feature policy class | AND veto |
| 两个条件都满足才退回 fallback | conjunction gate | `rule_A AND rule_B` |
| 仍然用 multi-fold gate 选规则 | chronological validation | `3750/4000/4250` |
| 最后只在 holdout 上验一次 | final holdout validation | `cut > 4250` |

通俗解释：

```text
上一轮我们发现：

  单特征规则能改善一点，
  但还是打不过 fallback。

所以这一轮问：

  如果规则不只看一个信号，
  而是同时看两个信号，
  会不会更准？

这就是 two-feature veto。

它的形式是：

  如果 A 条件满足，
  并且 B 条件也满足，
  那就退回 fallback。
```

专业解释：

```text
This run tests a two-feature conjunctive fallback veto. Candidate pair rules
are built from strong single-feature discovery rules, selected on chronological
validation folds, and evaluated once on the final holdout.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_two_feature_veto.py

report:
  reports/router-two-feature-veto-multifold-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Policy Depth?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 规则能表达多复杂的判断 | policy class capacity | single vs two-feature |
| 单特征只会问一个问题 | shallow threshold policy | one feature threshold |
| 双特征可以问两个问题 | deeper conjunctive policy | AND rule |
| 但更复杂不一定更好 | capacity vs exposure tradeoff | sparse triggers |

通俗解释：

```text
policy depth 可以理解成：

  这个 router 规则有多聪明。

单特征规则像是：

  只问一个问题。

双特征规则像是：

  先问问题 A，
  再问问题 B，
  两个都满足才行动。

它更精确，
但也更容易太严格，
导致很少触发。
```

专业解释：

```text
Policy depth is the expressive capacity of the router decision rule. A
two-feature conjunction can represent narrower regions of feature space than a
single threshold, but it may reduce validation exposure.
```

项目对应：

```text
single-feature:
  feature_A >= threshold

two-feature:
  feature_A >= threshold_A
  AND feature_B >= threshold_B
```

## 3. The Selected Two-Feature Rule

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 两个信号都来自预测和历史上下文的偏离 | prediction-context alignment | `prediction_context_alignment.*` |
| recent2000 的趋势偏离要大 | trend mismatch | first condition |
| recent1500 的均值偏离也要大 | mean mismatch | second condition |
| 满足时退回 recent2000 fallback | fallback intervention | `selected_family = recent2000` |

通俗解释：

```text
选出来的规则大概意思是：

  某些 adapter 的预测形状，
  跟刚刚看到的历史走势差得比较多。

这时候 router 的 override 可能不稳，
于是退回 fallback。
```

专业解释：

```text
The selected pair uses two prediction-context alignment thresholds. It vetoes
only when both a recent2000 trend mismatch and a recent1500 mean mismatch are
large.
```

项目对应：

```text
first:
  recent2000_predicted_trend_minus_past_trend >= 0.8012431066174683

second:
  recent1500_predicted_mean_delta_from_past_last_over_std >= 0.30731040774514196
```

## 4. Why The Rule Is Too Sparse

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 两个条件都满足，触发次数变少 | conjunction reduces exposure | sparse veto |
| 两个 validation folds 完全没触发 | fold no-exposure | cut3750/cut4000 |
| 没触发就不能证明有效 | no treatment, no treatment effect | robust gate fails |
| 所以不能叫 robust pass | insufficient fold exposure | `robust_pass=false` |

通俗解释：

```text
双特征规则的问题是：

  它更精确，
  但太挑剔。

在 validation 里：

  cut3750 没触发。
  cut4000 没触发。
  只在 cut4250 触发了 5 次。

这不能叫稳定。

因为前两折根本没考到它。
```

专业解释：

```text
The two-feature conjunction has sparse exposure. It improves the combined
validation metric, but fails the strict robust gate because two validation folds
have zero interventions.
```

项目对应：

| Fold | Changed windows | Metric delta | Negative series | Verdict |
|---|---:|---:|---:|---|
| cut3750 | 0 | 0.0000000000 | 1 -> 1 | no_rule_exposure |
| cut4000 | 0 | 0.0000000000 | 1 -> 1 | no_rule_exposure |
| cut4250 | 5 | +0.0000795744 | 3 -> 3 | rule_improves_split |

## 5. Final Holdout Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 比当前 router 好一点 | incremental improvement | metric delta positive |
| 没增加 negative series | downside neutral | `2 -> 2` |
| 比单特征改善更大 | stronger final delta | +0.0000844906 |
| 但仍低于 fallback | below fallback | negative relative lift |

通俗解释：

```text
最后 holdout 里：

  它确实让当前 router 变好。

而且比上一轮单特征规则改善更多。

但是：

  它还是没超过 recent2000 fallback。

这就说明：

  双特征规则方向有用，
  但还不够成为发布版本。
```

专业解释：

```text
The two-feature rule improves the selected router on final holdout and keeps
negative series unchanged. However, the resulting routed policy still has
negative lift relative to the fixed fallback.
```

项目对应：

```text
final_holdout:
  changed_windows: 7
  metric_delta: +0.0000844906
  negative_series: 2 -> 2

relative_lift_vs_fallback:
  original router: -0.144159%
  two-feature veto: -0.054892%

overall verdict:
  incremental_positive_but_below_fallback
```

## 6. Why More Hand-Written AND Rules Are Not The Next Best Step

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| AND 越多，越不容易触发 | conjunction sparsity | lower exposure |
| 触发太少，验证证据不足 | weak validation power | no robust pass |
| 它能修一点，但打不过 fallback | local repair, not release | below fallback |
| 下一步需要打分式 router | score-based/supervised policy | richer router |

通俗解释：

```text
如果继续加第三个条件：

  A AND B AND C

它可能更精准，
但也更少触发。

少触发的问题是：

  你很难证明它真的稳定有效。

所以继续手写更多 AND 规则，
不是最高价值方向。

更合理的是：

  让 router 给多个信号打分，
  而不是要求所有条件同时满足。
```

专业解释：

```text
The two-feature experiment shows that conjunctive hand-written policies improve
local precision but reduce exposure. The next policy class should combine
signals through a score or supervised model rather than stricter conjunctions.
```

项目对应：

```text
pair_candidate_count: 400
validation_robust_pass_count: 0

sensitivity pair_candidate_count: 1200
validation_robust_pass_count: 0
```

## 7. The Important Lesson

Fact:

```text
The two-feature rule improves final holdout more than the previous single-rule
veto and keeps negative series unchanged.
```

Fact:

```text
No two-feature candidate passes the strict multi-fold robust gate.
```

Fact:

```text
The two-feature final holdout remains below fixed recent2000 fallback.
```

Inference:

```text
Two-feature AND veto adds useful precision, but the policy is still too sparse
and too weak for release.
```

Recommendation:

```text
Move from hand-written AND vetoes to a score-based or supervised router under
the same multi-fold gate.
```

