# 063 - Utility-Aware Selection

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-utility-regret-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看赚多少 | utility-aware selection | utility score |
| 也看风险扣分 | downside penalty | negative series penalty |
| 时间段不稳也扣分 | fold regression penalty | fold metric penalty |
| strict gate 仍然不放松 | fail-closed promotion | final untouched |

通俗解释：

```text
上一轮 expected regret 找到了更强的平均收益信号。

但问题是：

  平均收益好看，
  不代表金融模型可靠。

这一轮我们加了一个评分：

  收益加分。
  风险扣分。
  时间折倒退扣分。
  没曝光也扣分。

这个分数叫 utility score。
```

专业解释：

```text
This run adds a utility score over validation candidates. The score combines
aggregate metric lift with penalties for negative-series regressions,
fold-level downside regressions, fold-level metric regressions, and missing
fold exposure.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_expected_regret_veto.py

reports:
  reports/router-expected-regret-veto-utility-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-expected-regret-veto-utility-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Utility?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最终值不只是收益 | utility | benefit minus cost |
| 收益是 MAE 改善 | reward term | `combined_metric_delta` |
| 成本是风险和不稳定 | penalty terms | fold/downside penalties |
| utility 大于 0 才值得看 | positive utility | `utility_positive` |

通俗解释：

```text
假设一个候选模型：

  平均收益 +10 分。

但它带来：

  风险 -6 分。
  时间段不稳定 -5 分。

那最终不是 +10。

最终是：

  +10 - 6 - 5 = -1

这就是 utility 的想法：

  不看单项收益。
  看扣掉风险之后还剩多少。
```

专业解释：

```text
Utility is an objective that combines rewards and costs into one decision
surface. In this run the reward is validation metric improvement, and costs are
explicit penalties for instability or downside.
```

项目对应：

```text
utility_score =
  combined_metric_delta
  - downside penalties
  - fold instability penalties
  - no-exposure penalties
```

## 3. Why This Matters For LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| adapter 有时很强 | specialized adapter gain | LoRA override |
| adapter 有时会害人 | adapter downside | fallback better |
| router 要会选择 | policy selection | fallback-veto |
| utility 教 router 怕风险 | risk-aware model selection | utility diagnostic |

通俗解释：

```text
LoRA adapter 像一个专业选手。

它在某些场景会比基础模型强。
但在另一些场景会犯错。

所以真正的系统不是：

  训练一个 LoRA，然后永远使用它。

而是：

  训练 LoRA。
  评估它什么时候强。
  用 router 决定什么时候用它。
  不确定时退回 fallback。

utility score 是在训练 router 的判断标准。
它告诉我们：

  这个选择不只是有没有提升，
  还要看提升够不够支付风险成本。
```

专业解释：

```text
Domain LoRA deployment is a policy problem as much as an adapter-training
problem. Utility-aware selection makes the promotion surface closer to the
actual operating objective: stable lift under downside constraints.
```

项目对应：

```text
adapter:
  TimesFM LoRA candidate family

router:
  expected-regret fallback-veto

utility:
  validation-time risk-adjusted candidate score
```

## 4. The Formula

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先拿收益 | reward | `combined_metric_delta` |
| negative series 变多扣分 | downside penalty | `combined_negative_series_delta` |
| 某折风险变差扣分 | fold downside penalty | `fold_negative_regressions` |
| 某折指标变差扣分 | fold metric penalty | `fold_metric_regressions` |
| 某折没触发也扣分 | exposure penalty | `fold_no_exposure` |

通俗解释：

```text
我们这轮用的默认公式是：

  utility =
    平均 MAE 改善
    - negative series 惩罚
    - fold downside 惩罚
    - fold metric 惩罚
    - no exposure 惩罚

每个惩罚默认是 0.001。

为什么是 0.001？

因为这一轮候选的 MAE 改善量级大概也是 0.001。

意思是：

  如果一个候选只提升 0.001，
  但它有一个严重稳定性问题，
  那这个收益不够支付风险成本。
```

专业解释：

```text
The penalty scale is intentionally comparable to observed validation lift.
This makes one fold-level regression large enough to cancel a marginal
aggregate improvement.
```

项目对应：

```text
utility_score =
  combined_metric_delta
  - 0.001 * max(combined_negative_series_delta, 0)
  - 0.001 * fold_negative_regressions
  - 0.001 * fold_metric_regressions
  - 0.001 * fold_no_exposure
```

## 5. This Is Not Relaxing Strict Gate

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| utility 是诊断分 | diagnostic ranking | validation only |
| strict gate 是发布门 | promotion gate | final holdout guard |
| utility positive 不能发布 | not sufficient | strict still required |
| final 没被动过 | holdout protected | `final_holdout_evaluated=false` |

通俗解释：

```text
这里要分清楚两件事：

  utility score:
    帮我们更聪明地看 validation 候选。

  strict gate:
    决定能不能进入 final holdout。

utility 分数高，
不等于可以发布。

它只是说：

  这个候选扣掉风险以后看起来还值得研究。

但如果它还有任何 fold metric regression，
strict gate 仍然会拒绝。
```

专业解释：

```text
Utility scoring is a ranking and diagnostic layer. It does not replace the
promotion gate. Final holdout remains inaccessible unless strict validation
passes.
```

项目对应：

```text
selection_gate:
  strict

result:
  selected_config: null
  final_holdout_evaluated: false
```

## 6. What Happened

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| no-series 假阳性少了 | loose positives filtered | 14 -> 5 |
| series-aware 全部被过滤 | no utility-positive configs | 7 -> 0 |
| strict 仍然是 0 | no promotion | strict count 0 |
| final 继续保护 | fail closed | final false |

通俗解释：

```text
结果非常清楚：

no-series:
  原来有 14 个松散 positive。
  utility 之后只剩 5 个。

series-aware:
  原来有 7 个松散 positive。
  utility 之后剩 0 个。

这说明：

  很多“看起来平均收益不错”的候选，
  扣掉风险以后其实不值得。
```

专业解释：

```text
Utility scoring narrows the loose validation frontier. It does not create a
strict-positive candidate, but it exposes which aggregate-positive candidates
are too unstable after risk adjustment.
```

项目对应：

```text
no-series:
  validation_positive_count: 14
  validation_utility_positive_count: 5
  validation_strict_positive_count: 0

series-aware:
  validation_positive_count: 7
  validation_utility_positive_count: 0
  validation_strict_positive_count: 0
```

## 7. Raw Lift vs Utility

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| raw lift 只看平均收益 | aggregate ranking | max metric delta |
| utility 看风险后收益 | risk-adjusted ranking | utility score |
| 最强 raw 候选被扣成负数 | false positive filtered | `-0.0035242565` |
| 最好 utility 候选仍未过 strict | cleaner but not promotable | one fold regression |

通俗解释：

```text
no-series 里纯看平均收益，
最好看的候选是：

  combined_metric_delta = +0.0014757435

这看起来不错。

但它有：

  negative series delta = 2
  fold metric regressions = 2
  fold negative regressions = 1

扣完以后：

  utility_score = -0.0035242565

所以它不是突破。
它是一个“平均收益很诱人，但风险太贵”的候选。
```

专业解释：

```text
The utility surface rejects the highest aggregate-lift candidate because the
risk-adjusted value is negative. The best utility-ranked candidate has no
negative-series or fold-downside regression, but still has one fold metric
regression, so it remains non-promotable.
```

项目对应：

```text
highest raw-lift no-series candidate:
  combined_metric_delta: +0.0014757435
  utility_score: -0.0035242565

best utility no-series candidate:
  combined_metric_delta: +0.0013203037
  utility_score: +0.0003203037
  fold_metric_regressions: 1
```

## 8. How To Think About This In Finance

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 平均赚钱不代表策略好 | mean return is insufficient | aggregate lift |
| 回撤和尾部风险很重要 | downside risk | negative series |
| 不同市场阶段要稳定 | regime robustness | validation folds |
| 策略要先活下来 | risk-adjusted objective | utility |

通俗解释：

```text
金融里一个策略可能这样：

  大部分时候小赚。
  某些时候大亏。

如果你只看平均，
它可能看起来不错。

但真实交易会关心：

  哪些资产被伤害？
  哪些市场阶段会失效？
  坏的时候会不会特别坏？

utility score 就是在把这些问题写进评分。
```

专业解释：

```text
For financial forecasting, aggregate error reduction is not enough. A useful
adapter policy needs risk-adjusted evidence across assets and chronological
regimes.
```

项目对应：

```text
aggregate:
  combined_metric_delta

cross-asset risk:
  negative_series_delta

time-regime risk:
  fold_metric_regressions
```

## 9. What We Learned

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| utility 有用 | diagnostic value | filters false positives |
| 但还不能发布 | no strict pass | final untouched |
| series-aware 更危险 | identity surface is fragile | 0 utility positives |
| 下一步要减少 fold regression | transfer stability | feature/objective work |

通俗解释：

```text
这一轮的价值不是“模型成功发布”。

这一轮的价值是：

  我们有了更好的筛选尺子。

这把尺子告诉我们：

  很多平均收益高的候选，其实风险太贵。
  series-aware 方向尤其不稳。
  当前 blocker 仍然是时间折稳定性。
```

专业解释：

```text
Utility scoring improves candidate diagnosis but does not solve chronological
transfer. The remaining blocker is generating candidates with zero fold metric
regressions, not merely ranking unstable candidates better.
```

项目对应：

```text
status:
  diagnostic improvement
  no release candidate

blocked by:
  fold_metric_regressions
```

## 10. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不放松 gate | preserve holdout | strict selection |
| 不继续只调阈值 | avoid threshold chasing | stop shallow tuning |
| 找减少时间折倒退的信号 | improve separability | feature search |
| 或直接训练 utility 目标 | train risk-aware objective | utility-aware model |

通俗解释：

```text
下一轮有两个合理方向：

  方向 A:
    找新特征，让 fold regression 变少。

  方向 B:
    不只是训练 regret，
    而是直接训练 utility-aware 目标。

不应该做的是：

  看到 no-series 还有 5 个 utility positive，
  就放松 strict gate 去跑 final。

那会污染 final holdout。
```

专业解释：

```text
The next experiment should either improve feature separability under the
existing expected-regret model, or move the utility objective into training
instead of applying it only as post-training validation ranking.
```

项目对应：

```text
must keep:
  no-leak features
  strict gate
  final holdout untouched unless strict candidate exists

next target:
  reduce fold_metric_regressions to 0
```
