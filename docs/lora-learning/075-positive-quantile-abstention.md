# 075 - Positive-Quantile Abstention

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-abstention-gate-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先判断 fallback 可能更好 | benefit prediction | logistic probability |
| 再判断够不够自信 | abstention gate | positive quantile |
| 不够自信就不出手 | abstain instead of veto | confidence-abstained windows |
| 用训练集校准自信 | train-split calibration | positive probability quantile |

通俗解释：

```text
上一轮 margin weighting 失败的原因是：

  它让 router 更怕犯错，
  最后变成 final 里面不出手。

这轮我们不再只调 loss 权重。

我们把 router 的问题拆成两步：

  1. 它觉得 fallback 会更好吗？
  2. 它有多确定？够不够确定到值得出手？
```

专业解释：

```text
This run adds an abstention gate on top of the logistic fallback-benefit
probability. The action policy requires both a raw probability threshold and a
training-positive probability quantile threshold.
```

项目对应：

```bash
--abstention-mode positive-quantile
--positive-probability-quantile 0.5
--positive-probability-quantile 0.75
--positive-probability-quantile 0.9
```

## 2. What Is Abstention?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 看不准就别乱动 | abstention | keep original selected adapter |
| 出手是 veto | intervention | switch selected family to fallback |
| 不出手不是失败本身 | no action can be correct | avoid false positive |
| 但一直不出手没价值 | abstention collapse | zero final exposure |

通俗解释：

```text
abstention 就是：

  我有一点怀疑 selected adapter 不好，
  但我不够确定。
  所以我不强行换成 fallback。

这比乱换好。

但如果永远不换，
那这个 router 也没有实际价值。
```

专业解释：

```text
Abstention is a second-stage decision that suppresses low-confidence actions.
It is useful only if it reduces harmful interventions while preserving enough
out-of-sample exposure.
```

## 3. Why This Is Different From A Normal Threshold

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 普通 threshold 是手写线 | fixed decision cutoff | `probability_threshold` |
| quantile 是训练集校准线 | train-calibrated cutoff | positive probability quantile |
| 两条线都要过 | conjunctive action rule | probability + abstention |
| 报告会分开记录 | separate observability | benefit / abstain / changed |

通俗解释：

```text
普通 threshold 是：

  只要概率超过 0.5 就出手。

positive quantile 是：

  看训练集中那些 fallback 真的更好的样本，
  它们通常预测到多高的概率。

然后要求新样本也达到这个“训练中正样本的自信水平”。
```

专业解释：

```text
The abstention gate is derived from the model's probability distribution on
training positives. For quantile 0.5, the gate is the median predicted
probability among training examples where fallback was actually better.
```

项目对应：

```text
positive_p50_probability: 0.5284044747
positive_p75_probability: 0.6214999260
positive_p90_probability: 0.7001317452
```

## 4. The New Counters

| Counter | 通俗解释 | 专业解释 |
|---|---|---|
| `benefit_signal_windows` | 模型觉得可能该退回 fallback | probability passed benefit threshold |
| `confidence_abstained_windows` | 但不够自信，所以没动 | failed abstention gate |
| `changed_windows` | 最后真的出手了几次 | actual intervention count |

通俗解释：

```text
以前我们只知道：

  改了多少窗口。

现在我们知道：

  有多少窗口模型觉得 fallback 可能更好，
  有多少窗口因为不够自信被压住，
  最后真正改了多少窗口。
```

专业解释：

```text
This separates model belief from policy action. That is important because a
router can fail either by missing benefit signals or by over-abstaining after
detecting them.
```

## 5. What Happened

| Surface | Gate | Objective | Robust-pass | Strict-positive | Quantile | Final changed | Final delta | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| no-series | strict | combined | 10 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | combined | 10 | 0 | 0.50 | 81 | +0.0000115310 | incremental_positive_but_below_fallback |
| no-series | robust | worst-fold | 10 | 0 | 0.75 | 43 | -0.0000162348 | not_promotable |
| include-series | strict | combined | 4 | 0 | n/a | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | combined | 4 | 0 | 0.50 | 1 | +0.0000001652 | not_validated_final_underexposed |

通俗解释：

```text
这轮比前几轮有进展：

  no-series robust final 改了 81 个窗口。
  final delta 是正的。
  negative series 没变坏。

但还不能发布：

  strict validation 还是 0。
  两个 validation fold 仍然是负的。
  final 仍然没有超过 fixed fallback。
```

专业解释：

```text
The no-series combined objective produces a partial-positive final diagnostic.
It has enough final exposure and improves the current selected policy, but it
still fails strict fold validation and remains below the fixed recent2000
fallback.
```

## 6. Best Diagnostic Candidate

```text
l2: 0.1
probability_threshold: 0.5
false_positive_weight: 1.0
training_weighting: time-bin-label-balanced
abstention_mode: positive-quantile
positive_probability_quantile: 0.5
```

Validation:

```text
combined_metric_delta: +0.0003628808
combined_changed_windows: 144
fold_metric_deltas:
  cut3750: -0.0000463270
  cut4000: -0.0000596526
  cut4250: +0.0011946219
fold_changed_windows: 76, 35, 33
fold_metric_regressions: 2
```

Final holdout:

```text
benefit_signal_windows: 82
confidence_abstained_windows: 1
changed_windows: 81
metric_delta: +0.0000115310
negative_series: 2 -> 2
promotion_verdict: incremental_positive_but_below_fallback
```

## 7. Why This Is Better But Still Not Success

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它终于在 final 里出手够多 | adequate final exposure | 81 changed windows |
| final 是正的 | positive held-out delta | +0.0000115310 |
| 没增加负序列 | downside unchanged | 2 -> 2 |
| 但 validation fold 还不稳 | fold regressions remain | 2 regressions |
| 还没超过 fallback | below fallback | `incremental_positive_but_below_fallback` |

通俗解释：

```text
这轮不是失败到没信号。

它说明：

  拆成 benefit + abstention 是对的方向。

但它还没强到能发布。

因为发布标准不是：

  final 有一点正数。

发布标准是：

  多个 validation fold 稳，
  final 也稳，
  比 fallback 更强，
  不伤害序列 downside。
```

专业解释：

```text
This is a partial-positive diagnostic. It improves the current routed policy on
final holdout with enough exposure, but fails strict validation and does not
beat the fixed fallback baseline.
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| adapter 不只是训练权重 | deployment policy matters | router/veto |
| 什么时候用 adapter 是独立问题 | adapter selection | fallback benefit |
| 不确定时可以不出手 | abstention policy | confidence gate |
| 但不出手也要被评估 | exposure accounting | changed windows |

通俗解释：

```text
LoRA 微调得到 adapter 之后，
真正上线前还有一个问题：

  我什么时候该相信这个 adapter？

positive-quantile abstention 就是在学：

  我不仅要知道 fallback 可能更好，
  还要知道我够不够确定。
```

专业解释：

```text
Domain adaptation is not only parameter adaptation. It also includes the
runtime policy that decides when the adapted model should be used, when it
should be vetoed, and when the system should abstain.
```

## 9. What We Learned

Fact: The two-stage abstention interface produced the strongest recent
no-series final diagnostic.

Fact: Strict validation still has zero passing candidates.

Fact: Include-series remains underexposed and should not be the next main path.

Inference: The next leverage point is fold-regression repair inside no-series,
not identity-aware routing or more scalar weighting.

Recommendation: Continue from the no-series positive-quantile path. The next
round should target the two weak validation folds directly, likely by adding a
fold-aware selection objective or training penalty that punishes cut3750 and
cut4000 regressions without losing final exposure.
