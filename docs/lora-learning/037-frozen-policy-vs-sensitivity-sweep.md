# 037 - Frozen Policy vs Sensitivity Sweep

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-expanded-alignment-normalized-fallback-veto.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 换成同样强的特征表面再考一次 | comparable feature-surface retest | expanded + alignment-normalized |
| 先用上一轮固定参数 | frozen policy evaluation | `mvl=0.005`, `k=50`, `threshold=0.0002` |
| 再做小范围探测 | diagnostic sensitivity sweep | `k=25/50/75`, thresholds |
| 结果变复杂了 | aggregate gain but weak robustness | positive delta, bad series split |

通俗解释：

```text
上一轮我们发现：

  expanded surface 旧版本太弱，
  少了 alignment-normalized 的关键特征。

所以这轮我们不是重新训练模型，
而是把已有预测档案重新整理成一张更公平的考试卷：

  expanded cuts
  但使用 alignment-normalized 特征面

然后分两步看：

  1. 用上一轮已经定下来的正式参数考一次
  2. 小范围改几个旋钮，看有没有接近可用的方向
```

专业解释：

```text
This round rebuilds router rows from existing prediction archives for the
expanded cut grid, then applies the same `alignment-normalized` feature preset
used by the previous best surface. The first evaluation is frozen-policy
generalization. The second sweep is diagnostic only.
```

项目对应：

```text
new full-feature rows:
  reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json

new comparable feature surface:
  reports/router-rows-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A Frozen Policy?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 考试前就定好规则 | pre-registered config | formal fallback-veto parameters |
| 不能看到新卷子再改答案 | no target-surface retuning | no post-hoc threshold picking |
| 结果更可信 | cleaner generalization evidence | frozen policy gate |

通俗解释：

```text
frozen policy 就是：

  规则先定死，
  然后去新数据上考试。

不能这样：

  看了新考试卷以后，
  再偷偷改规则，
  然后说自己泛化成功。

所以 frozen policy 更严格。
它回答的是：

  上一轮找到的正式策略，
  原封不动搬到新表面上，
  还行不行？
```

专业解释：

```text
A frozen policy is a fixed router configuration evaluated on a new surface
without using that surface to tune hyperparameters. It is stronger evidence than
a sweep because it reduces post-hoc selection bias.
```

项目对应：

```text
frozen fallback_veto:
  candidate-set = knn-regret
  min-validation-lift = 0.005
  veto-feature-mode = global
  veto-k = 50
  veto-regret-threshold = 0.0002
```

## 3. Frozen Policy Result

| Metric | Value |
|---|---:|
| Routed windows | 4000 |
| Selected MAE | 0.0959202509 |
| Fallback MAE | 0.0958798640 |
| MAE delta vs fallback | -0.0000403870 |
| Relative lift vs fallback | -0.0004212248 |
| Positive / negative routed series | 6 / 4 |

通俗解释：

```text
冻结参数没有赢。

它比固定 recent2000 稍微差一点点：

  差 0.0000403870 MAE

这不是灾难性失败。
但发布线很简单：

  必须大于 0。

所以 frozen policy 不能算泛化成功。
```

专业解释：

```text
The frozen formal fallback-veto policy remains below the fixed recent2000
fallback baseline on the expanded alignment-normalized surface. It is close to
break-even but still negative.
```

项目对应：

```text
frozen formal result:
  delta_vs_fallback = -0.000040386979742845774
  split = 6/4
```

## 4. What Is A Sensitivity Sweep?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 小范围拧旋钮 | hyperparameter sensitivity check | `k`, threshold, validation lift |
| 看方向有没有救 | diagnostic search | not release evidence |
| 不能当正式胜利 | post-hoc tuning risk | promotion still blocked |

通俗解释：

```text
sensitivity sweep 不是正式考试。

它更像：

  我们发现 frozen policy 差一点，
  所以看看是不是某个旋钮太死。

如果扫参后有一个组合赢了，
这只能说明：

  这个方向可能还有价值。

不能马上说：

  模型已经成功泛化。

因为这个参数是看了这张新卷子以后才挑出来的。
```

专业解释：

```text
A sensitivity sweep probes whether nearby hyperparameters can recover lift.
Positive sweep results are hypothesis-generating unless they are confirmed on a
third surface or held-out target.
```

项目对应：

```text
diagnostic sweep:
  min-validation-lift = 0, 0.005
  veto-k = 25, 50, 75
  threshold = 0.0001, 0.00015, 0.0002, 0.00025
```

## 5. Diagnostic Sweep Result

Best diagnostic row:

| Metric | Value |
|---|---:|
| Policy | `fallback_veto` |
| Min validation lift | 0.000 |
| Veto k | 25 |
| Veto threshold | 0.00015 |
| Routed windows | 4000 |
| Selected MAE | 0.0958495919 |
| Fallback MAE | 0.0958798640 |
| MAE delta vs fallback | 0.0000302721 |
| Relative lift vs fallback | 0.0003157294 |
| Positive / negative routed series | 3 / 7 |

Top sweep rows:

| Rank | `mvl` | `k` | Threshold | Delta | Split |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.000 | 25 | 0.00015 | 0.0000302721 | 3 / 7 |
| 2 | 0.000 | 25 | 0.00020 | 0.0000286664 | 3 / 7 |
| 3 | 0.000 | 25 | 0.00025 | 0.0000256533 | 4 / 6 |
| 4 | 0.000 | 25 | 0.00010 | 0.0000232337 | 3 / 7 |
| 5 | 0.005 | 75 | 0.00010 | 0.0000131057 | 5 / 5 |

通俗解释：

```text
扫参后确实找到一个 aggregate 正收益组合。

但是这个组合有一个严重问题：

  只有 3 个 series 赢
  7 个 series 输

也就是说：

  总分赢了，
  但班里多数学生变差了。

这在金融领域尤其危险。
因为我们不只关心平均分，
还关心哪些资产、利率、信用利差、波动率被伤害。
```

专业解释：

```text
The best diagnostic configuration clears aggregate MAE delta but fails the
cross-series robustness gate. The lift is concentrated in a few series and does
not provide a stable vertical adapter-router release candidate.
```

项目对应：

```text
diagnostic best:
  delta_vs_fallback = 0.000030272089724323048
  split = 3/7

release-quality expectation:
  aggregate delta > 0
  and per-series split should not be majority-negative
```

## 6. Where Did It Help And Hurt?

Best diagnostic positives:

| Series | Delta vs fallback |
|---|---:|
| `DGS2:realized_vol_20` | 0.0006113791 |
| `VIXCLS:realized_vol_20` | 0.0004381169 |
| `DFF:realized_vol_20` | 0.0001653772 |

Best diagnostic negatives:

| Series | Delta vs fallback |
|---|---:|
| `SP500:realized_vol_20` | -0.0004575981 |
| `DGS10:realized_vol_20` | -0.0003117676 |
| `BAMLH0A0HYM2:realized_vol_20` | -0.0000633409 |

通俗解释：

```text
这个 router 比较会处理：

  短端利率 DGS2
  VIX 波动率
  联邦基金利率 DFF

但它会伤害：

  SP500
  10 年期国债利率 DGS10
  高收益信用利差 BAMLH0A0HYM2

所以它不像一个稳定的金融通用 router。
它更像一个偏科策略。
```

专业解释：

```text
The positive aggregate result is driven by large gains in a small subset of
series. SP500 and DGS10 remain recurring downside contributors, which suggests
that the next seam should combine aggregate routing with a per-series downside
guard.
```

项目对应：

```text
repeated risk series:
  SP500:realized_vol_20
  DGS10:realized_vol_20

potential guard direction:
  allow aggregate fallback_veto only when per-series historical downside is acceptable
```

## 7. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 本身不是最后一步 | adapter training is only one module | router decides adapter use |
| 平均赢不等于产品可用 | aggregate metric can hide downside | 3/7 split |
| 不能看新数据再定规则 | avoid post-hoc overfitting | frozen policy first |
| 下一步是保护亏损面 | downside-aware router seam | per-series guard |

通俗解释：

```text
到现在我们已经不是只在训练 LoRA。

我们在做一个更完整的系统：

  多个 LoRA adapter
  多个时间切片
  一个 no-leak router
  一个 fallback 保护规则

LoRA 只是生产候选答案的人。
router 才是决定用谁答案的人。

如果 router 会让多数 series 变差，
即使总平均稍微变好，也不能发布。
```

专业解释：

```text
The adapter portfolio creates candidate forecasts, but model quality is governed
by the selection policy under no-leak constraints. A production-worthy router
needs both aggregate lift and downside control across series.
```

项目对应：

```text
current state:
  frozen formal policy = not generalized
  diagnostic tuned policy = aggregate positive, per-series fragile

next useful seam:
  fallback_veto + per-series downside guard
```

## 8. Fact / Inference / Recommendation

Fact: Rebuilding expanded router rows with `alignment-normalized` features
improved the fallback-veto evaluation surface.

Fact: The frozen formal fallback-veto policy still missed the fixed recent2000
baseline by `0.00004038698` MAE.

Fact: A diagnostic nearby configuration produced positive aggregate delta:
`0.00003027209`.

Fact: That diagnostic winner had a weak `3/7` positive/negative series split.

Inference: The fallback-veto concept is not dead. It becomes useful on the
right feature surface, but it is still too aggregate-driven.

Recommendation: Do not promote the diagnostic winner. The next round should add
or test a per-series downside guard on top of the aggregate fallback-veto router.

## 9. Next Round

```text
Test a guarded fallback-veto policy:

  base selector:
    diagnostic aggregate-positive fallback_veto

  added constraint:
    block or soften overrides for series with repeated historical downside

success criteria:
  aggregate delta > 0
  positive/negative series split at least 5/5
  SP500 and DGS10 downside reduced
```

