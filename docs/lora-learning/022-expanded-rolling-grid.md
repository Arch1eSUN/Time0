# 022 - Expanded Rolling Grid And Router Evidence

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-expanded-grid.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 多出几套考试卷 | expanded rolling cut grid | `cuts=3500..5500` |
| 每套卷子都让 5 个选手作答 | multi-family prediction archive | 5 adapter families |
| 让小裁判多看几次过去比赛 | more chronological supervision | 4500 router rows |
| 只允许它用过去经验选未来 | no-leak policy evaluation | `evaluate_prediction_router.py` |

通俗解释：

```text
上一轮我们只有 3 场考试：
4000, 5000, 5500。

问题是：
如果你只让一个小裁判看 3 场比赛，
它很难学会“什么情况下该选哪个 adapter”。

所以这轮我们不是换更大的 LoRA，
也不是把训练步数加大。

我们做的是：
增加考试场次。

现在有 9 个时间切分：
3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500。
每个切分有 500 个预测窗口。
每个窗口都保存 5 个 family 的预测和真实误差。
```

专业解释：

```text
We expanded the rolling validation grid to increase chronological supervision
for prediction-level adapter routing. The router still trains only on prior
cuts and evaluates on future cuts, so the extra data improves valid supervision
without introducing lookahead leakage.
```

项目对应：

```text
router rows: 4500
cuts: 9
families: zero-shot, full, recent1500, recent2000, recent3000
new trainable adapters: 24
prediction archives: 45
```

## 2. What Is A Rolling Grid?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把时间切成很多考试点 | chronological cut grid | `cut` |
| 每个考试点只看它之前的数据 | temporal holdout | `skip_windows=cut` |
| 后面的考试不能帮助前面的训练 | no lookahead | prior cuts only |
| 多个考试点比单次考试更可信 | rolling validation | expanded grid |

通俗解释：

```text
如果我们只在一天考试，可能刚好那天运气好。

如果我们在很多天考试，
每次都按时间顺序：
过去训练，未来测试，
那结果就更可信。

rolling grid 的意思就是：
不是只做一次训练/测试切分，
而是沿着时间轴移动考试点。
```

专业解释：

```text
A rolling grid is a set of chronological train/evaluate cut-points. Each cut
defines which windows are available for training and which windows are held out
for evaluation. It tests temporal generalization instead of random split
generalization.
```

项目对应：

```text
base grid:
  4000,5000,5500

expanded grid:
  3500,3750,4000,4250,4500,4750,5000,5250,5500
```

## 3. Why This Matters For LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 训练完不等于变强 | training completion is not evidence | adapter exists is not success |
| 一个点赢了不等于稳 | single split can be noise | cut-level variance |
| 不同时间段要选不同 adapter | regime-dependent adaptation | adapter routing |
| 小裁判也需要训练数据 | router needs supervision | router rows |

通俗解释：

```text
你可以把 TimesFM 想成一个通才。
LoRA adapter 是给它戴上的小专业工具。

但金融时间序列会变：
有些时间段 recent1500 好，
有些时间段 recent2000 好，
有些时间段 zero-shot 反而不差。

所以我们现在不只是问：
“某一个 LoRA adapter 强不强？”

我们开始问：
“在当前市场状态下，该选哪个 adapter？”
```

专业解释：

```text
The project is moving from single-adapter evaluation to policy evaluation. The
adapter family may contain useful specialization, but deployment requires a
selection policy that chooses among adapters using runtime-safe features.
```

项目对应：

```text
single adapter question:
  Is recent2000 better than zero-shot?

router question:
  Given current context and prediction disagreement, which family should serve
  this window?
```

## 4. Adapter Strong vs Router Strong vs Publishable

| 概念 | 通俗解释 | 专业解释 | 本轮结论 |
|---|---|---|---|
| adapter 变强 | 某个选手平均更强 | fixed-family baseline improves | yes, `recent2000` useful |
| router 会选 | 小裁判能选更好的选手 | learned policy beats fallback | weak but improving |
| 值得发布 | 未来也稳定有效 | promotion-ready evidence | no |

通俗解释：

```text
这三个东西一定要分开。

1. adapter 变强：
   recent2000 平均比 zero-shot 好。

2. router 会选：
   小裁判能不能在不同窗口选对 adapter。

3. 值得发布：
   这个选择能力是不是稳定、可复现、不会只是在这次数据上碰巧赢。

本轮是：
adapter 有价值。
router 有一点进步。
但还不能发布。
```

专业解释：

```text
Fixed-family improvement is not equivalent to routing competence. Routing
competence requires a no-leak policy to outperform a strong fallback. Release
readiness requires stable improvement over fallback across cuts and series.
```

项目对应：

```text
fixed recent2000 routed improvement vs zero-shot: 1.987592%
validation-gated routed improvement vs zero-shot: 2.116398%
extra relative lift over fallback MAE: 0.131419%
```

## 5. What Results Did We Get?

All 4500 rows:

| Family | Mean MAE |
|---|---:|
| zero-shot | 0.0945869804 |
| full | 0.0933575549 |
| recent1500 | 0.0932794720 |
| recent2000 | 0.0928097800 |
| recent3000 | 0.0931267339 |

通俗解释：

```text
如果永远只选一个 adapter，
现在最强的还是 recent2000。

它不是每个窗口都赢，
但平均看最稳。
```

专业解释：

```text
The strongest fixed-family baseline on the expanded grid is `recent2000`.
This makes it the correct fallback policy for learned routing.
```

Router 结果：

| Policy | MAE | MAE improvement vs zero-shot |
|---|---:|---:|
| fixed `recent2000` | 0.0958798640 | 1.987592% |
| best learned diagnostic | 0.0959988452 | 1.865964% |
| validation-gated router | 0.0957538599 | 2.116398% |

通俗解释：

```text
最好看的数字是：
validation-gated router 到了 2.116398%。

但不能只看这个。

因为固定 recent2000 已经有 1.987592%。
router 真正额外多赢的是很小的一点：
MAE 只少了 0.0001260041。
相对 fallback 约多赢 0.131419%。
```

专业解释：

```text
The validation-gated policy beats the fixed fallback on routed cuts, but the
incremental gain over fallback is small. The best standalone learned diagnostic
still underperforms fixed recent2000, so the deployable policy improvement is
coming from conservative gating, not from a robust learned router by itself.
```

项目对应：

```text
best learned diagnostic: knn_regret_no_series_k50
fallback: fixed recent2000
validation gate: switch only if prior-cut validation clears 1% lift
```

## 6. What Did The Gate Actually Select?

| Cut | Selected config | Improvement vs zero-shot |
|---:|---|---:|
| 3500 | fixed:recent2000 | 0.640621% |
| 3750 | fixed:recent2000 | 0.816933% |
| 4000 | softmax_series | 3.635257% |
| 4250 | knn_regret_no_series_k50 | 6.677896% |
| 4500 | fixed:recent2000 | 1.500391% |
| 4750 | fixed:recent2000 | 0.669219% |
| 5000 | fixed:recent2000 | 0.678605% |
| 5250 | fixed:recent2000 | -0.812779% |
| 5500 | fixed:recent2000 | 2.010708% |

通俗解释：

```text
router 没有到处乱切。

它只在两个 cut 上切到了学习型选择：
4000 选 softmax_series。
4250 选 knn_regret_no_series_k50。

其他时候它回到 recent2000。

这就是 fail-closed 的作用：
没有把握，就别装聪明。
```

专业解释：

```text
The validation-gated policy selected learned routing only when the candidate
cleared the prior validation threshold. Otherwise it preserved the fallback
policy. This improves robustness but does not prove the learned router is
independently stable.
```

项目对应：

```text
learned switches: cuts 4000 and 4250
fallback selections: 7 cuts
promotion status: blocked
```

## 7. Why The Leaky Oracle Still Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 作弊裁判知道答案 | oracle uses future errors | invalid for runtime |
| 作弊裁判很强说明有空间 | selection headroom exists | 7.289511% MAE gain |
| 但它不能上线 | not deployable evidence | guardrail warning |
| 我们要学会不作弊地接近它 | no-leak router objective | future work |

通俗解释：

```text
leaky oracle 像一个已经看过答案的裁判。
它每个窗口都知道哪个 adapter 错得最少。

它这轮能做到 7.289511% MAE improvement。

这说明：
如果能选对 adapter，收益很大。

但它不能直接用。
因为真实预测时，我们不知道未来答案。
```

专业解释：

```text
The oracle-policy gap remains the central research signal. A high leaky oracle
gain indicates adapter choice has value, while weak no-leak router gain means
the current runtime features or supervision are not yet sufficient to recover
that value reliably.
```

项目对应：

```text
leaky oracle MAE: 0.0876920517
leaky oracle MAE improvement: 7.289511%
valid gated router MAE improvement: 2.116398%
```

## 8. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不是一次训练就完事 | adaptation is an evaluated family | multiple adapters |
| 不同训练窗口像不同专长 | training-window specialization | full/recent1500/2000/3000 |
| router 是 LoRA 系统的一部分 | selection policy is part of serving | adapter router |
| 证据要按时间顺序来 | chronological evidence | expanded grid |

通俗解释：

```text
你从 0 学 LoRA，最容易误解的一点是：
“我训练了一个 adapter，所以我完成了微调。”

更准确地说：
你只是制造了一个候选 adapter。

它要不要用，要看：
1. 它在未来窗口是否更准。
2. 它是否只在某些时间段有用。
3. 如果有多个 adapter，我们是否知道什么时候选谁。
4. 这个选择规则有没有偷看未来。
```

专业解释：

```text
LoRA fine-tuning produces adapters, but a deployable domain model requires an
evaluation protocol, a fallback policy, and a no-leak serving policy. Adapter
weights alone are not the product interface.
```

项目对应：

```text
current product seam:
  not ready

current research artifact:
  expanded rolling grid + prediction archives + no-leak router report
```

## 9. How To Understand This Round

Fact:

```text
The expanded grid produced 4500 aligned router rows across 9 cuts and 5
families.
```

Fact:

```text
`recent2000` is still the best fixed adapter family by mean MAE.
```

Fact:

```text
The validation-gated router reached 2.116398% routed-cut MAE improvement vs
zero-shot.
```

Fact:

```text
The validation-gated router only improves fixed recent2000 by 0.0001260041 MAE.
```

Inference:

```text
The router signal is no longer dead, but it is not strong enough to publish.
The gain is too small and still needs per-series stability review.
```

Recommendation:

```text
Continue with per-series analysis of validation-gated selections. Do not move
to Hugging Face release, Moirai integration, or larger LoRA rank yet.
```

## 10. Next Round

Next useful question:

```text
When validation-gated routing wins, which series and regimes create the win?
```

Why:

```text
If only one or two series create the whole router gain, the router is fragile.
If gains spread across multiple series and cuts, it becomes a stronger release
candidate.
```

Next artifact:

```text
per-series expanded router attribution report
```

