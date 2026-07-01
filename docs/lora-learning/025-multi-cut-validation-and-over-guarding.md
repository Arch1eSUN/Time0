# 025 - Multi-Cut Validation And Over-Guarding

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-multicut-series-guard.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看最近一次小考 | multi-cut validation | `series_multicut_guarded` |
| 把多次小考平均起来 | aggregate validation gate | all prior validation rows |
| 每次小考都不能挂科 | worst-cut validation gate | `series_multicut_worst_guarded` |
| 看哪种护栏更适合 LoRA adapter 路由 | serving-policy ablation | router attribution report |

通俗解释：

```text
上一轮我们有一个问题：
只看最近一次 validation cut，证据有点薄。

所以这轮我们试了两种更“多看历史”的办法：

办法 A：
把多个历史 validation cut 合在一起看平均成绩。

办法 B：
每个历史 validation cut 单独看。
只要某个 series 在任何一次历史小考里输给 fallback，
未来就不让 learned router 接管这个 series。
```

专业解释：

```text
We extended router attribution with two multi-cut series gates:

1. `series_multicut_guarded`
   Aggregates all prior chronological validation cuts into one per-series gate.

2. `series_multicut_worst_guarded`
   Computes per-series validation for each prior chronological validation cut
   and blocks a series if it fails any historical cut-level gate.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/summarize_router_attribution.py

new policies:
  --policy series_multicut_guarded
  --policy series_multicut_worst_guarded

unchanged:
  training data
  adapter weights
  candidate adapter families
  fallback family = recent2000
```

## 2. What Is Multi-Cut Validation?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一次考试可能运气好 | one validation split can be noisy | latest validation cut |
| 多次考试更能看稳定性 | multiple chronological validation cuts | prior cuts |
| 但平均分会掩盖偏科 | aggregation can hide subgroup regressions | DGS10/SP500 risk |
| 每次都要过又可能太严格 | worst-case gate may over-block signal | DFF blocked |

通俗解释：

```text
假设一个学生：

第一次数学 100 分，英语 50 分。
第二次数学 50 分，英语 100 分。

如果只看总平均，他好像还不错。
但如果你要决定他能不能教别人英语，
平均分就会骗你。

我们的 series 也是这样。
一个 series 在某些历史切片里被 router 帮到，
在另一些历史切片里被 router 伤到。

所以 multi-cut validation 不是简单地“历史越多越好”。
关键是历史怎么用。
```

专业解释：

```text
Multi-cut validation replays adapter selection across earlier chronological
holdout cuts. It tests whether a serving policy generalizes over time before
using it on the target cut.

However, aggregating validation rows changes the loss geometry:

  aggregate gate = lower variance, but can hide local failures
  worst-cut gate = stronger safety, but can reject useful positive signal
  latest-cut gate = more reactive to recency, but less stable
```

项目对应：

```text
cut4000:
  available prior validation cuts: only 3750
  result: multi-cut is effectively the same as single-cut

cut4250:
  available prior validation cuts: 3750 and 4000
  result: aggregate multi-cut allowed all series
  result: worst-cut blocked DFF, DGS10, SP500
```

## 3. What Did We Compare?

Routed cuts only:

| Policy | Rule | MAE | MAE delta vs fallback | Relative lift vs fallback | Improvement vs zero-shot | Negative series |
|---|---|---:|---:|---:|---:|---:|
| validation-gated | global latest cut only | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-guarded | latest cut per series | 0.0956773586 | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-multicut | aggregate prior cuts per series | 0.0957538599 | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-multicut-worst | every prior cut must pass | 0.0957048950 | 0.0001749690 | 0.182488% | 2.166452% | 5 |

通俗解释：

```text
结果很清楚：

最好还是上一轮的 series-guarded。

multi-cut 平均法没有帮助：
它和普通 validation-gated 完全一样。

worst-cut 方法有帮助：
比普通 validation-gated 更好。

但 worst-cut 太保守：
它挡掉了一部分真正有用的 DFF 信号，
所以不如 latest-cut series guard。
```

专业解释：

```text
`series_multicut_guarded` collapsed to the same aggregate result as
`validation_gated` because the historical per-series aggregate gate allowed every
series at the routed cuts.

`series_multicut_worst_guarded` improved over validation-gated by reducing
cut4250 risk, but underperformed `series_guarded` because it blocked `DFF` after
a stale historical failure at validation cut 3750.
```

项目对应：

```text
best current policy remains:
  --policy series_guarded
  --min-series-validation-lift 0.0
```

## 4. What Failed?

| Failure | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| Aggregate multi-cut did nothing | 平均分把问题盖住了 | subgroup regressions were diluted | allowed all 10 series |
| Worst-cut over-blocked | 一次旧失败导致永远不信 | stale negative evidence dominated | blocked DFF at cut4250 |
| Thresholds did not rescue it | 调严格没救 | stricter gates removed signal | 0.5% and 1.0% worse |

Aggregate multi-cut:

```text
policy: series_multicut_guarded
routed MAE delta vs fallback: 0.0001260041
relative lift vs fallback: 0.131419%
same as validation-gated: yes
```

Worst-cut default:

```text
policy: series_multicut_worst_guarded
routed MAE delta vs fallback: 0.0001749690
relative lift vs fallback: 0.182488%
better than validation-gated: yes
better than series-guarded: no
```

Threshold sweep:

| Policy | min series lift | MAE delta vs fallback | Relative lift |
|---|---:|---:|---:|
| series-guarded | 0.25% | 0.0002025053 | 0.211207% |
| series-guarded | 0.50% | 0.0000418135 | 0.043610% |
| series-guarded | 1.00% | 0.0000580597 | 0.060555% |
| worst-cut | 0.25% | 0.0001749690 | 0.182488% |
| worst-cut | 0.50% | -0.0000077771 | -0.008111% |
| worst-cut | 1.00% | 0.0000084691 | 0.008833% |

通俗解释：

```text
我们没有因为一次失败就结束。
我们又调了严格程度。

结果：
严格一点没有变好。

这说明问题不是阈值没调对，
而是这个 gate 的形状不对。
```

专业解释：

```text
The negative result is structural, not only hyperparameter-related. Raising
`min_series_validation_lift` reduces adapter usage and removes positive routing
signal faster than it removes future error.
```

## 5. Why Latest-Cut Still Wins

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 金融市场会变 | non-stationarity | chronological cuts |
| 最近证据更像未来 | recency can dominate stale evidence | latest validation cut |
| 但最近证据也可能太少 | variance risk | cut4000 still weak |
| 所以下一步不是简单多看历史 | need risk scoring, not hard history averaging | series-risk penalty |

通俗解释：

```text
金融数据不像考试题库。

市场状态会变。
很久以前的失败，不一定代表现在一定失败。
很久以前的成功，也不一定代表现在一定成功。

所以：
只看最近一次，不够稳。
把所有历史平均，又太钝。
历史任何一次失败就封杀，又太死。

我们需要的是：
最近证据权重大，
旧证据也看，
但不要让旧证据一票否决。
```

专业解释：

```text
This is a recency-vs-stability tradeoff. The current best policy is not best
because it is theoretically complete. It is best because, on the current rolling
evidence, recent per-series validation captures the harmful cut4250 regime
without suppressing the DFF positive contribution.
```

项目对应：

```text
series_guarded:
  blocks DGS10/SP500 at cut4250
  keeps DFF active
  best routed MAE delta so far

series_multicut_worst_guarded:
  blocks DFF/DGS10/SP500 at cut4250
  safer than validation-gated
  worse than series_guarded
```

## 6. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不只是训练一个文件 | adapter weights are only one layer | adapter family |
| 什么时候用哪个 adapter 也很重要 | serving policy affects effective performance | router |
| 护栏不是越多越好 | guardrail shape matters | series gate |
| 验证集不是拿来安慰自己的 | validation must match future failure modes | no-leak cuts |

通俗解释：

```text
LoRA 微调后会得到 adapter。

但在真实项目里，问题不是：
“我有没有一个 adapter？”

更重要的问题是：
“什么时候该用这个 adapter？”
“什么时候该回到更稳的 baseline？”
“它会不会只帮一部分 series，却伤害另一部分？”

所以我们现在做的 router/guard，
不是偏离 LoRA。
它是 LoRA 走向可发布模型必须经过的阶段。
```

专业解释：

```text
Adapter training changes model parameters through a low-rank update. Router and
guard experiments do not change those weights; they change the serving policy
around a family of trained adapters.

For a domain LoRA release, adapter quality and serving policy quality are both
part of the model system. A strong adapter with a bad selection policy can still
regress out-of-sample performance.
```

项目对应：

```text
current adapter family:
  zero-shot
  full-history LoRA
  recent1500 LoRA
  recent2000 LoRA
  recent3000 LoRA

current best serving policy:
  validation gate
  plus latest-cut per-series guard
```

## 7. Current Verdict

Fact: aggregate multi-cut validation did not improve over validation-gated.

Fact: worst-cut validation improved over validation-gated but did not beat
`series_guarded`.

Fact: the best tested policy remains `series_guarded` with
`min_series_validation_lift=0.0`.

Inference: the next useful direction is not a stricter hard gate. It is a
series-risk score that can combine recency, repeated failures, and positive
contribution without letting one stale failure erase useful signal.

Recommendation: keep `series_guarded` as the current best valid policy, do not
publish yet, and test a recency-weighted series-risk penalty next.
