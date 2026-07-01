# 023 - Router Attribution: Who Helped And Who Got Hurt?

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-router-attribution.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 查小裁判赢在哪里 | router attribution | `summarize_router_attribution.py` |
| 看每条序列单独得失 | per-series contribution | `series_id` aggregation |
| 对比固定安全方案 | fallback comparison | fixed `recent2000` |
| 判断能不能发布 | promotion evidence | blocked |

通俗解释：

```text
上一轮我们看到一个表面好消息：

validation-gated router 比 zero-shot 好 2.116398%。
也比固定 recent2000 多赢了一点点。

但这还不够。

我们必须继续问：
这个赢，是大家都变好了？
还是一两个 series 变好了，其他 series 被伤害了？

这轮就是查这个。
```

专业解释：

```text
We ran per-series attribution for the expanded validation-gated router. The
script recomputes the same no-leak routing policy, then aggregates selected
window errors by series and compares them against the fixed recent2000 fallback.
```

项目对应：

```text
input: expanded router rows
policy: validation-gated router
fallback: fixed recent2000
output: router attribution report
```

## 2. What Is Attribution?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总分拆成每个人贡献 | contribution decomposition | per-series delta |
| 看谁让结果变好 | positive contributor | `delta_vs_fallback > 0` |
| 看谁被模型伤害 | negative contributor | `delta_vs_fallback < 0` |
| 防止平均数骗人 | disaggregated evaluation | promotion guard |

通俗解释：

```text
假设一个班平均分提高了。

这可能有两种情况：

1. 全班大多数人都提高了。
2. 一个学霸提高很多，其他人反而退步。

如果是第 2 种，
你不能说这个教学方法已经适合全班。

模型也是一样。
```

专业解释：

```text
Attribution decomposes aggregate metric change into subgroup contributions.
For this project, the subgroup is `series_id`. The metric is MAE delta relative
to the fixed fallback adapter.
```

项目对应：

```text
delta_vs_fallback_mae = fallback_recent2000_mae - router_selected_mae

positive:
  router better than fallback

negative:
  router worse than fallback
```

## 3. What Did We Find?

Routed cuts only:

| Metric | Value |
|---|---:|
| windows | 4000 |
| selected MAE | 0.0957538599 |
| fixed recent2000 MAE | 0.0958798640 |
| MAE delta vs fallback | 0.0001260041 |
| relative lift vs fallback | 0.131419% |
| positive delta windows | 412 |
| negative delta windows | 424 |

通俗解释：

```text
router 的确比固定 recent2000 好一点点。

但这个“一点点”很小：
平均 MAE 只少了 0.0001260041。

而且不是所有窗口都赢：
有 412 个窗口因为 router 变好，
也有 424 个窗口因为 router 变差。
大量窗口没有变化，因为仍然选 recent2000。
```

专业解释：

```text
The validation-gated policy has a small positive aggregate delta over fallback,
but positive and negative changed windows are nearly balanced. Most windows are
unchanged because the gate preserved the fallback.
```

项目对应：

```text
selected families:
  recent2000: 3164
  zero-shot: 306
  recent3000: 292
  recent1500: 131
  full: 107
```

## 4. Which Series Helped?

| Series | Delta sum vs fallback | Share of net delta |
|---|---:|---:|
| `DFF:realized_vol_20` | 0.7494884166 | 148.703165% |
| `VIXCLS:realized_vol_20` | 0.1037528657 | 20.585214% |
| `DGS2:realized_vol_20` | 0.0543806398 | 10.789457% |
| `DEXUSEU:realized_vol_20` | 0.0102083329 | 2.025365% |
| `DEXJPUS:realized_vol_20` | 0.0044602339 | 0.884927% |

通俗解释：

```text
最关键的是 DFF。

DFF 一个 series 的正贡献是总净收益的 148.7%。

这句话的意思是：
DFF 帮得非常多，
但其他 series 有一些在拖后腿，
所以最后总收益被抵消到只剩 100%。
```

专业解释：

```text
`DFF:realized_vol_20` contributes more than the net aggregate gain because
negative contributors offset the positive delta. This is a concentration risk.
```

项目对应：

```text
DFF mean MAE delta vs fallback: 0.0018737210
DFF selected counts:
  recent2000: 311
  full: 27
  recent1500: 27
  recent3000: 26
  zero-shot: 9
```

## 5. Which Series Got Hurt?

| Series | Delta sum vs fallback | Share of net delta |
|---|---:|---:|
| `DGS10:realized_vol_20` | -0.2748701807 | -54.535954% |
| `SP500:realized_vol_20` | -0.1073125770 | -21.291483% |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0347256513 | -6.889785% |
| `DCOILWTICO:realized_vol_20` | -0.0011436877 | -0.226912% |
| `DTWEXBGS:realized_vol_20` | -0.0002219409 | -0.044034% |

通俗解释：

```text
最大的问题是 DGS10 和 SP500。

router 在整体上看起来更好，
但它伤害了 DGS10 和 SP500。

如果我们把这个 router 发布出去，
用户可能会在某些序列上得到更差预测，
而平均指标会把这个问题藏起来。
```

专业解释：

```text
The router has negative subgroup effects. `DGS10` and `SP500` are the largest
negative contributors, so the aggregate improvement fails the broad-stability
requirement for promotion.
```

项目对应：

```text
DGS10 mean MAE delta vs fallback: -0.0006871755
SP500 mean MAE delta vs fallback: -0.0002682814
```

## 6. Why Cut-Level Attribution Matters

| Cut | Selected config | MAE delta vs fallback |
|---:|---|---:|
| 4000 | `softmax_series` | 0.0013556099 |
| 4250 | `knn_regret_no_series_k50` | -0.0003475770 |

通俗解释：

```text
router 真正切换 away from recent2000 的 cut 只有两个：

cut4000：切换是好的。
cut4250：切换是坏的。

这说明小裁判不是完全没用。
但它还不稳。
```

专业解释：

```text
The validation gate selected learned routing on two cuts. One cut produced
positive fallback delta and one produced negative fallback delta. The policy
therefore lacks cut-level stability.
```

项目对应：

```text
cut4000 selected config: softmax_series
cut4250 selected config: knn_regret_no_series_k50
other routed cuts: fixed recent2000
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 平均分会骗人 | aggregate metrics can hide subgroup harm | per-series attribution |
| 小提升不等于可发布 | small aggregate lift is insufficient | promotion blocked |
| LoRA 系统还包括选择规则 | adapter serving policy matters | router |
| 先保护弱项，再追求更强 | guardrails before capacity | series-aware gate |

通俗解释：

```text
你现在要记住一个很重要的 LoRA 工程经验：

训练出 adapter 只是第一步。
平均指标变好也只是第二步。

真正要发布，需要知道：
谁变好了？
谁变差了？
变差的是不是关键 series？
这种变差能不能被规则挡住？

如果这些问题没回答，
就不能因为一个平均数好看而发布。
```

专业解释：

```text
Domain adaptation must be evaluated at subgroup level. A LoRA adapter or router
can improve the average while creating unacceptable subgroup regressions.
Promotion requires stable, explainable improvement across relevant slices.
```

项目对应：

```text
current router:
  aggregate positive
  subgroup fragile
  not promotion-ready
```

## 8. What Should We Do Next?

Recommendation:

```text
Do not increase LoRA rank yet.
Do not publish the adapter/router yet.
Do not integrate into Moirai yet.

Next experiment:
  series-aware validation gate
```

通俗解释：

```text
下一步不是让模型更大。

下一步是让小裁判更谨慎：

如果某个 series 在历史验证里经常被 router 伤害，
那这个 series 就继续用 recent2000，
不要让 learned router 接管。
```

专业解释：

```text
The next policy should add a series-level guardrail. A learned router may switch
only when both global validation and series-level validation clear the fallback
threshold.
```

项目对应：

```text
candidate policy:
  validation_gated + per_series_guard

blocked series candidates:
  DGS10
  SP500
```

## 9. How To Understand This Round

Fact:

```text
The validation-gated router improves routed-cut MAE over fixed recent2000 by
0.0001260041.
```

Fact:

```text
DFF contributes 148.703165% of the net positive delta.
```

Fact:

```text
DGS10 and SP500 are the largest negative contributors.
```

Inference:

```text
The router has localized signal, not broad promotion-ready reliability.
```

Recommendation:

```text
Continue with a series-aware guardrail before any release or larger LoRA
capacity experiment.
```
