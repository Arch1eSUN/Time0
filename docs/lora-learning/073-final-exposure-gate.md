# 073 - Final Exposure Gate

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-final-exposure-gate-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不能只赢 1 次就说模型变强 | tiny holdout exposure is not evidence | `final_changed_windows=1` |
| 最终测试集也要有最小出手次数 | final exposure gate | `--min-final-changed-windows 20` |
| 训练验证和最终发布要分开 | validation selection vs final promotion | validation folds / final holdout |
| 保留旧命令兼容 | backward-compatible default | default is `1` |

通俗解释：

```text
上一轮我们看到一个很危险的情况：

  include-series robust
  final delta 是一个很小的正数
  但它只改了 1 个窗口

这就像：

  一个交易策略一年只交易 1 次，
  那 1 次刚好赚钱，
  然后我们说它很强。

这不可靠。

所以这轮我们加一条规则：

  final holdout 里面至少要真实出手 20 次，
  不然不能算最终验证通过。
```

专业解释：

```text
This run adds a final holdout exposure gate. A candidate may still be evaluated
on final holdout, but its promotion verdict is downgraded when the final
intervention count is below `min_final_changed_windows`.
```

项目对应：

```bash
--min-final-changed-windows 20
```

## 2. Important Vocabulary

| 通俗说法 | 专业说法 | 在本项目里是什么意思 |
|---|---|---|
| 出手次数 | exposure / intervention count | router 改变原选择的窗口数 |
| 最终考试 | final holdout | validation 后完全留到最后看的时间段 |
| 小样本运气 | high-variance estimate | 改动太少，结果不稳定 |
| 不能发布 | not promotable | 还不能作为 release 证据 |
| 降级判决 | promotion verdict downgrade | split delta 正，但证据不足 |

通俗解释：

```text
router 的作用是：

  原来系统想用 adapter A。
  router 说：这次别用 A，用 fallback。

每一次这种“改主意”，就是一次 changed window。

如果 changed window 很少，
我们就不知道 router 到底学会了规律，
还是碰巧猜中。
```

专业解释：

```text
`changed_windows` measures decision exposure. It is the number of evaluation
windows where the veto/router policy changes the selected forecasting family
relative to the original selected policy.

Low exposure increases estimator variance. A positive aggregate metric delta
from one or two interventions is not sufficient evidence for deployment.
```

## 3. Validation Gate vs Final Gate

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| validation 是选模型时的考试 | model selection split | `validation_cuts=3750,4000,4250` |
| final 是最后一次考试 | held-out promotion split | `cut > 4250` |
| validation 曝光不足，不能选 | selection exposure gate | `min_validation_changed_windows` |
| final 曝光不足，不能发布 | promotion exposure gate | `min_final_changed_windows` |

通俗解释：

```text
我们有两层考试：

1. validation:
   用来挑哪个 router 候选更值得看。

2. final:
   用来判断这个候选能不能算真正有效。

上一轮我们已经要求 validation 不能只出手很少。
但 final 还没有同样的硬门槛。

这轮补上 final gate。
```

专业解释：

```text
Validation exposure protects candidate selection from sparse validation wins.
Final exposure protects promotion from sparse final wins.

These are separate because a candidate can have enough validation exposure but
almost no final exposure after retraining or after time-regime changes.
```

## 4. What Changed In Code

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 加一个参数 | CLI control | `--min-final-changed-windows` |
| 判断 final 出手够不够 | exposure predicate | `final_exposure_pass` |
| 不够就降级 | promotion verdict override | `not_validated_final_underexposed` |
| split 结果仍保留 | separate raw split verdict | `final_holdout.verdict` |

通俗解释：

```text
我们没有把原始结果删掉。

报告里现在同时有两件事：

  split_verdict:
    这次 final split 本身是涨还是跌。

  promotion_verdict:
    证据够不够支持我们说它可用。

这样不会混淆：

  “这 1 次确实赢了”
  和
  “这个策略值得发布”
```

专业解释：

```text
The code keeps the raw split verdict and adds a promotion verdict. This avoids
losing diagnostic signal while still preventing sparse positives from being
treated as deployable evidence.
```

项目对应：

```text
final_holdout.verdict = rule_improves_split
final_holdout.promotion_verdict = not_validated_final_underexposed
```

## 5. What Happened

| Surface | Gate | Strict-positive | Final changed | Exposure pass | Final delta | Verdict |
|---|---|---:|---:|---|---:|---|
| no-series | strict | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 0 | 54 | true | -0.0000143517 | not_promotable |
| include-series | strict | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | 0 | 1 | false | +0.0000001652 | not_validated_final_underexposed |

通俗解释：

```text
结果很清楚：

no-series:
  出手 54 次，样本够。
  但结果是负的。

include-series:
  结果是很小的正数。
  但只出手 1 次。
  所以不算通过。
```

专业解释：

```text
The no-series candidate has sufficient final exposure but fails on metric
delta. The include-series candidate has positive raw final delta but fails the
minimum final exposure gate.
```

项目对应：

```text
no-series robust:
  final_changed_windows: 54
  final_exposure_pass: true
  promotion_verdict: not_promotable

include-series robust:
  final_changed_windows: 1
  final_exposure_pass: false
  promotion_verdict: not_validated_final_underexposed
```

## 6. Why This Matters For LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 本身不是全部 | adapter needs a usage policy | router/veto layer |
| 什么时候用 adapter 很重要 | adapter selection problem | selected family vs fallback |
| 小样本赢不能说明专业化成功 | sparse positive is not domain adaptation proof | 1 changed window |
| 发布要看可重复收益 | reproducible out-of-sample benefit | final promotion gate |

通俗解释：

```text
LoRA 微调不是只训练出一个 adapter 文件就结束。

真正使用时还要回答：

  什么时候用这个 adapter？
  什么时候不用？
  它在哪些市场状态下更可靠？

router 就是在回答这个问题。

如果 router 只在 final 里出手 1 次，
那它没有真正证明“我知道什么时候用 LoRA 更好”。
```

专业解释：

```text
Domain adaptation includes both the adapted forecasting weights and the policy
that decides when those weights should be used. A LoRA adapter with an
unvalidated routing policy can still overfit deployment decisions.
```

## 7. Why `include-series` Is Risky

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它知道是哪条资产序列 | series identity feature | `--include-series` |
| 可能记住局部规律 | memorization risk | series-aware logistic model |
| 更容易变得保守到几乎不出手 | sparse intervention risk | final changed = 1 |
| 正收益也可能只是运气 | high variance | tiny final delta |

通俗解释：

```text
include-series 就像告诉模型：

  这是 VIX。
  这是日元汇率。
  这是高收益债利差。

这可能有帮助。
但也可能让模型变成：

  只在某个很特殊的资产、很特殊的窗口出手一次。

这不是我们想要的金融领域规律。
```

专业解释：

```text
Series-aware features can improve calibration when there is enough
out-of-sample exposure. But when final exposure collapses, the apparent gain is
more likely a sparse identity-conditioned artifact than a transferable routing
rule.
```

## 8. What Counts As Success Now

| 层级 | 通俗标准 | 专业标准 |
|---|---|---|
| 训练成功 | 代码能跑完不够 | training completion only |
| validation 成功 | 多个验证 fold 不坏 | no fold metric/downside regressions |
| exposure 成功 | 出手次数够 | validation and final changed windows pass |
| final 成功 | 最后考试也变好 | positive final metric delta |
| release 成功 | 比 fallback 稳定更强 | beats fallback and clears downside gates |

通俗解释：

```text
从现在开始，不能这样说：

  final delta 是正的，所以成功。

必须这样问：

  它出手够多吗？
  validation 里面每个 fold 稳吗？
  final 里面真的变好吗？
  有没有伤害某些序列？
  是否比 fallback 更好？
```

专业解释：

```text
Promotion requires metric improvement under adequate intervention exposure and
without hidden fold or series downside regressions. Exposure is a statistical
power requirement, not just an engineering field in the report.
```

## 9. What We Learned

Fact: The no-series candidate had enough final exposure but negative final
metric delta.

Fact: The include-series candidate had positive raw final delta but only 1 final
changed window.

Inference: The include-series positive is not reliable evidence of finance
domain specialization.

Recommendation: Keep the final-exposure gate as part of the project success
criteria. The next training lever should improve transfer stability, not loosen
the gates.

## 10. Next Round

通俗解释：

```text
现在问题变成：

  我们能不能让 router 既敢出手，
  又不伤害 final holdout？

如果继续只靠调阈值，
很可能是在原地打转。
```

专业解释：

```text
The next useful experiment should affect the training target or model class:

1. better no-leak labels that penalize fold regressions during training;
2. monotonic or constrained logistic training;
3. separate abstention calibration from fallback-benefit prediction;
4. new feature surface with fewer identity-conditioned sparse positives.
```
