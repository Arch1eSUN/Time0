# 038 - Guarded Fallback Veto

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-guarded-fallback-veto.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先让 router 选 adapter | base fallback-veto selector | `fallback_veto` |
| 再看这个 series 以前会不会被它坑 | per-series downside gate | `fallback_veto_series_guarded` |
| 风险高就退回保底答案 | fallback on risky series | `recent2000` |
| 目标不是最大平均分 | aggregate + coverage objective | delta plus split |

通俗解释：

```text
上一轮的问题是：

  router 平均分赢了，
  但 10 个 series 里 7 个变差。

这像一个交易策略：

  总收益是正的，
  但大多数品种都亏，
  只是少数品种赚很多。

这不能直接发布。

所以这轮我们加了一层保护：

  先让 fallback-veto 做选择。
  然后问：
    这个 series 在过去类似选择里，是不是经常被这个策略伤害？
  如果是：
    不切 adapter，退回 recent2000。
```

专业解释：

```text
This round adds `fallback_veto_series_guarded`, a composite no-leak router
policy. It first applies aggregate fallback-veto. Then it computes a recency-
weighted per-series historical risk gate from prior causal fallback-veto
selections and replaces risky overrides with the fallback family.
```

项目对应：

```text
new policy:
  fallback_veto_series_guarded

changed scripts:
  experiments/timesfm-lora/scripts/summarize_router_attribution.py
  experiments/timesfm-lora/scripts/sweep_router_policies.py
```

## 2. What Is A Per-Series Downside Guard?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 每个学生单独看错题 | series-level risk control | per-series gate |
| 不是全班平均赢就算赢 | aggregate lift is insufficient | split matters |
| 对容易受伤的 series 更保守 | fallback risky overrides | return to `recent2000` |
| 用过去判断现在 | causal prior-cut evidence | no current answer leakage |

通俗解释：

```text
如果我们只看平均分，
router 可能会这样：

  DGS2 赢很多
  VIX 赢很多
  DFF 赢一点
  其他 7 个 series 小亏

平均值可能还是正的。

但这不稳定。

per-series downside guard 的意思是：

  每条时间序列单独看历史表现。
  如果某条 series 过去经常因为切 adapter 变差，
  那这条 series 现在就不要乱切。
```

专业解释：

```text
The guard estimates per-series downside using only prior validation cuts. It
does not use current holdout errors. A current override is kept only if the
series-level historical selected metric stays within the configured downside
budget versus the fallback metric.
```

项目对应：

```text
fallback family:
  recent2000

guard evidence:
  prior cuts only

guarded action:
  selected_family -> recent2000 when series gate blocks
```

## 3. What Did We Add In Code?

| Module | Change |
|---|---|
| `summarize_router_attribution.py` | added `fallback_veto_series_guarded` policy |
| `summarize_router_attribution.py` | added `recency_weighted_selection_risk_gate` |
| `sweep_router_policies.py` | added sweep support for the new policy |

通俗解释：

```text
我们没有重写整个 router。

我们只是在原来的接口上加了一个新模式：

  fallback_veto_series_guarded

它复用原来的两块能力：

  fallback-veto:
    判断某个窗口的 adapter override 是否像历史坏邻居

  series risk gate:
    判断某条 series 历史上是否经常被 override 伤害
```

专业解释：

```text
The new policy composes existing seams instead of introducing a separate
evaluation script. `selection_for_cut` remains the public router-selection
interface used by both attribution and sweeps.
```

项目对应：

```text
selection_for_cut(..., policy="fallback_veto_series_guarded")
```

## 4. Why This Is Still No-Leak

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不看当前答案 | no current holdout label access | current `label` unused for selection |
| 只看过去考试 | prior-cut validation only | `prior_cuts` |
| 历史选择也按当时能知道的来 | causal replay | prior fallback-veto selections |

通俗解释：

```text
最危险的作弊方式是：

  当前这道题答案已经知道了，
  然后 router 再决定用哪个 adapter。

我们没有这样做。

guard 的证据来自：

  当前 cut 之前的 cuts。

而且历史上的 fallback-veto 选择，
也是按当时能看到的更早 cut 重新跑出来的。
```

专业解释：

```text
For each current cut, the guard builds its series risk evidence from prior cuts.
Historical fallback-veto selections are replayed causally by calling
`selection_for_cut` on each prior cut with `policy="fallback_veto"`.
```

项目对应：

```text
current cut:
  uses prior cuts only

prior cut replay:
  uses cuts earlier than that prior cut
```

## 5. Guard Parameters

| Parameter | 通俗解释 | 专业解释 |
|---|---|---|
| `min_validation_lift=0` | 总体只要不比 fallback 差就允许切 | aggregate validation gate requires break-even |
| `veto_k=25` | 看 25 个历史近邻 | KNN neighbor count |
| `veto_regret_threshold=0.00015` | 历史近邻平均后悔超过阈值就 veto | neighbor regret threshold |
| `series_risk_decay=0.25` | 越新的历史权重越高 | recency weighting |
| `min_series_validation_lift=-0.001` | 允许历史上最多约 0.1% 小亏 | 0.1% downside budget |

通俗解释：

```text
这里最容易误解的是：

  min_series_validation_lift = -0.001

它不是说我们希望亏。

它的意思是：

  如果一条 series 历史上只比 recent2000 差 0.1% 以内，
  仍然允许它尝试 router。

为什么要这样？

因为太严格会把很多有潜力的 series 全部锁回 fallback。
太宽松又会放出太多坏 override。

这轮 sweep 发现：

  -0.001 + decay 0.25

在平均收益和 series 覆盖之间更平衡。
```

专业解释：

```text
Negative `min_series_validation_lift` creates a small downside budget. With
`-0.001`, the weighted candidate metric may be up to 0.1% worse than fallback
before the series is blocked.
```

项目对应：

```text
balanced candidate:
  min_series_validation_lift = -0.001
  series_risk_decay = 0.25
```

## 6. Main Results

Comparison on routed cuts only:

| Policy | Delta vs fallback | Relative lift | Split | Selected MAE |
|---|---:|---:|---:|---:|
| Unguarded diagnostic `fallback_veto` | 0.0000302721 | 0.0003157294 | 3 / 7 | 0.0958495919 |
| Best guarded by delta | 0.0001033588 | 0.0010780034 | 4 / 6 | 0.0957765052 |
| Balanced guarded candidate | 0.0000998175 | 0.0010410687 | 5 / 5 | 0.0957800464 |

通俗解释：

```text
guard 之后，结果明显变好：

  平均收益从 0.00003027
  提到大约 0.00010

更重要的是：

  原来 3 赢 7 输
  现在能做到 5 赢 5 输

这不是最终成功，
但它是比上一轮更接近可用的 router。
```

专业解释：

```text
The guarded policy improves aggregate MAE delta by roughly 3.3x over the
unguarded diagnostic fallback-veto and improves cross-series coverage from 3/7
to 5/5 for the balanced candidate.
```

项目对应：

```text
unguarded diagnostic:
  delta = 0.000030272089724323048
  split = 3/7

balanced guarded:
  delta = 0.00009981752392164422
  split = 5/5
```

## 7. What Happened To SP500 And DGS10?

| Series | Unguarded delta | Balanced guarded delta |
|---|---:|---:|
| `SP500:realized_vol_20` | -0.0004575981 | -0.0000474838 |
| `DGS10:realized_vol_20` | -0.0003117676 | not in top-3 negatives |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0000633409 | -0.0001027449 |

通俗解释：

```text
上一轮最痛的两个问题：

  SP500
  DGS10

这轮明显被压住了。

SP500 还是小亏，
但亏损从约 -0.00046 降到约 -0.000047。

DGS10 不再是前三大亏损来源。

新的问题变成：

  BAMLH0A0HYM2
  DCOILWTICO
  SP500

所以 guard 有效，
但风险位置发生了转移。
```

专业解释：

```text
The per-series guard reduces the recurring SP500 and DGS10 downside that made
the unguarded diagnostic policy fragile. Remaining downside concentrates in
credit-spread and oil-volatility series.
```

项目对应：

```text
reduced recurring downside:
  SP500
  DGS10

new top downside:
  BAMLH0A0HYM2
  DCOILWTICO
  SP500
```

## 8. Sweep Ranking

Top guarded rows:

| Rank | `min_series_validation_lift` | `series_risk_decay` | Delta | Split |
|---:|---:|---:|---:|---:|
| 1 | 0.000 | 0.25 | 0.0001033588 | 4 / 6 |
| 2 | -0.001 | 0.05 | 0.0001001340 | 4 / 6 |
| 3 | -0.001 | 0.10 | 0.0001001340 | 4 / 6 |
| 4 | -0.001 | 0.25 | 0.0000998175 | 5 / 5 |
| 5 | 0.000 | 0.50 | 0.0000981008 | 4 / 6 |
| 6 | 0.000 | 0.75 | 0.0000981008 | 4 / 6 |

通俗解释：

```text
如果只追求最高平均分：

  rank 1 最好。

如果同时追求覆盖面：

  rank 4 更适合继续研究。

因为 rank 4 只少一点点平均收益，
但 split 从 4/6 改成 5/5。
```

专业解释：

```text
The best-by-delta row is not the best promotion candidate because it remains
majority-negative by series. The balanced row is a better frontier point.
```

项目对应：

```text
best delta:
  msvl = 0
  decay = 0.25
  split = 4/6

balanced candidate:
  msvl = -0.001
  decay = 0.25
  split = 5/5
```

## 9. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练 adapter 只是第一层 | LoRA creates candidate experts | adapter portfolio |
| 选 adapter 才是系统能力 | router controls deployment behavior | no-leak selector |
| 要防止平均值骗人 | aggregate lift can hide downside | split and attribution |
| guard 是模型产品化的一部分 | risk control layer | per-series downside guard |

通俗解释：

```text
现在我们做的已经不是：

  训练一个 LoRA，看平均误差。

而是：

  训练多个 LoRA
  保存每个窗口的预测
  训练/设计 router
  加 fallback 保护
  加 series 风险保护

这更接近真实模型产品。

因为真实发布时，用户不会只问：

  平均分是不是更好？

还会问：

  哪些场景会变差？
  变差能不能提前挡住？
```

专业解释：

```text
The adapter is no longer the only optimization target. Time0 is moving toward a
portfolio-and-router architecture where LoRA adapters provide candidate
forecasts and guarded no-leak routing controls deployment risk.
```

项目对应：

```text
current architecture:
  TimesFM base
  LoRA adapter portfolio
  prediction archive
  no-leak router
  fallback-veto
  per-series downside guard
```

## 10. Fact / Inference / Recommendation

Fact: `fallback_veto_series_guarded` was added to the existing router policy
interface.

Fact: The best guarded row by aggregate delta reached `0.0001033588`, but had
only a `4/6` positive/negative series split.

Fact: The balanced guarded row reached `0.0000998175` with a `5/5` split.

Fact: The balanced guard reduced SP500 downside from `-0.0004575981` to
`-0.0000474838`, and DGS10 was no longer a top-3 negative contributor.

Inference: Per-series downside control is a real improvement over unguarded
fallback-veto, but the router is still not broadly positive enough to publish.

Recommendation: Treat the balanced guarded row as the current best research
candidate, not a release. Next, test it on another target or a later comparable
archive, and inspect the remaining negative series: `BAMLH0A0HYM2`,
`DCOILWTICO`, and `SP500`.

## 11. Next Round

```text
Next useful experiment:

  keep balanced guarded fallback-veto fixed:
    mvl = 0
    msvl = -0.001
    decay = 0.25
    k = 25
    threshold = 0.00015

  test on:
    another target, or
    another comparable archive

success criteria:
  aggregate delta > 0
  positive/negative series split > 5/5 if possible
  no recurring major downside in SP500, DGS10, BAMLH0A0HYM2
```

