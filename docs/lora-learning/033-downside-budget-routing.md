# 033 - Downside Budget Routing

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-knn-downside-budget.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有训练新 LoRA | no new adapter training | same prediction archive |
| 继续测试 KNN-regret router | causal router replay | `--candidate-set knn-regret` |
| 给每条序列加亏损预算 | per-series downside budget | negative `min_series_validation_lift` |
| 看少伤几条序列值不值 | aggregate versus tail-risk tradeoff | MAE delta and series split |

通俗解释：

```text
上一轮我们得到一个还不错的 router：

  KNN-regret + validation gate

它的意思是：
  先找历史上相似的窗口
  看那些窗口哪个 adapter 更准
  如果最近验证里它没有输，就允许它接管

但问题是：
  总分变好，不代表每条金融序列都变好。

所以这轮我们问：

  如果某条序列过去被 router 伤过，
  能不能只在这条序列上少切换一点？
```

专业解释：

```text
This round adds a per-series downside-budget sweep on top of the KNN-regret
candidate set. It does not change model weights. It only changes the routing
policy that decides whether an adapter family may override fixed `recent2000`
for each series.
```

项目对应：

```text
input:
  router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

candidate set:
  knn-regret

tested policies:
  validation_gated
  series_guarded
  series_risk_penalized
```

## 2. What Is A Downside Budget?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 允许小亏，但不能亏太多 | tolerated validation regret | negative `min_series_validation_lift` |
| 太严格会错过收益 | over-guarding | `min_series=0` |
| 太宽松等于没保护 | under-guarding | very negative threshold |
| 这是安全阀，不是训练 | routing policy guard | no weight update |

通俗解释：

```text
假设 fallback adapter 是一个稳妥默认选择。

router 想说：
  我觉得这次应该换另一个 adapter。

downside budget 就是在问：
  好，你可以换。
  但你在这条序列过去的验证窗口里，
  最多只能比 fallback 差一点点。

如果差太多：
  这条序列就不让你换。
  继续用 fallback。
```

专业解释：

```text
The series gate compares candidate metric against fallback metric on prior
validation evidence for the same series.

The rule is:

required_metric = fallback_metric * (1 - min_series_validation_lift)
allowed = candidate_metric <= required_metric
```

项目对应：

```text
min_series_validation_lift = 0
  candidate must be no worse than fallback

min_series_validation_lift = -0.001
  candidate may be up to 0.1% worse than fallback

min_series_validation_lift = -0.0025
  candidate may be up to 0.25% worse than fallback

min_series_validation_lift = -0.005
  candidate may be up to 0.5% worse than fallback
```

## 3. Why Would We Allow Any Loss?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不要因为一点小亏错过大收益 | avoid over-guarding | previous hard guards lost delta |
| 验证集也有噪音 | validation estimate variance | small samples per series |
| 小亏可能换来整体更稳 | controlled regret | risk budget |
| 大亏必须挡住 | downside protection | fallback per series |

通俗解释：

```text
如果我们要求每条序列都绝对不能输，
听起来很安全。

但现实里验证窗口很小，
有时候只是噪音导致某条序列看起来小输。

如果门太严格：
  很多本来有用的切换会被挡掉。

所以我们允许非常小的亏损预算。
这不是放弃风控。
这是承认验证数据不完美。
```

专业解释：

```text
Strict per-series gating minimizes observed validation regret, but it can
overfit to small validation slices and collapse aggregate router lift. A small
negative `min_series_validation_lift` is a controlled-regret policy: it lets the
router tolerate bounded validation downside when the aggregate selector remains
strong.
```

项目对应：

```text
hard guard from earlier sweep:
  series_guarded, min_series=0
  MAE delta around 0.0001428194

soft budget this round:
  series_guarded, min_series=-0.005
  MAE delta 0.0002678626
```

## 4. Results

Top rows:

| Policy | Min validation | Min series | Decay | MAE delta | Positive / Negative series |
|---|---:|---:|---:|---:|---:|
| `validation_gated` | 0.000 | 0.0000 | 0.10 | 0.0002705342 | 6 / 4 |
| `validation_gated` | 0.005 | 0.0000 | 0.10 | 0.0002687244 | 7 / 3 |
| `series_guarded` | 0.000 | -0.0050 | 0.10 | 0.0002678626 | 6 / 4 |
| `series_risk_penalized` | 0.000 | -0.0050 | 0.05 | 0.0002678626 | 6 / 4 |
| `series_risk_penalized` | 0.005 | -0.0025 | 0.25 | 0.0002451542 | 8 / 2 |

通俗解释：

```text
这轮结论不是：
  新策略全面赢了。

更准确地说：

  普通 validation_gated 仍然总分最好。

  downside budget 可以让更多序列变正，
  但会牺牲一些总分。

所以它更像安全档位，
不是当前最快档位。
```

专业解释：

```text
The downside-budget sweep did not move the aggregate frontier. The best
aggregate policy remains `validation_gated mvl=0.0`. The best current
risk-spread policy is `series_risk_penalized mvl=0.005, min_series=-0.0025,
decay=0.25`, which improves series split to 8/2 at a lower MAE delta.
```

项目对应：

```text
best aggregate:
  validation_gated, mvl=0.0
  MAE delta = 0.0002705342
  series split = 6/4

current best research checkpoint:
  validation_gated, mvl=0.005
  MAE delta = 0.0002687244
  series split = 7/3

conservative risk candidate:
  series_risk_penalized, mvl=0.005, min_series=-0.0025, decay=0.25
  MAE delta = 0.0002451542
  series split = 8/2
```

## 5. How To Read 8/2

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 10 条序列里 8 条变好 | positive per-series delta count | `positive_routed_series_count=8` |
| 还有 2 条变差 | negative per-series delta count | `negative_routed_series_count=2` |
| 不是 80% 准确率 | not classification accuracy | per-series aggregate MAE delta |
| 不代表可以发布 | not enough promotion evidence | still one data archive |

通俗解释：

```text
8/2 不是说模型预测方向 80% 正确。

它的意思是：

  在这 10 条金融时间序列里，
  router 对 8 条的平均 MAE 比 fallback 更低，
  对 2 条的平均 MAE 比 fallback 更高。

所以 8/2 是“伤到的序列更少”，
不是“模型已经很准”。
```

专业解释：

```text
The 8/2 split is a per-series attribution summary over routed evaluation cuts.
Each series contributes one positive or negative sign according to its aggregate
MAE delta versus fixed `recent2000`.
```

项目对应：

```text
conservative risk candidate:
  positive series: 8
  negative series: 2

negative series:
  BAMLH0A0HYM2:realized_vol_20
  DEXJPUS:realized_vol_20
```

## 6. What Changed Inside Adapter Selection?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 更常回到默认 adapter | more fallback use | more `recent2000` |
| 少用冒险切换 | fewer overrides | lower non-fallback counts |
| DGS2 被救回来了 | one negative series flipped positive | DGS2 positive delta |
| BAMLH0A0HYM2 仍然难 | residual harmed series | still negative |

通俗解释：

```text
downside budget 的作用不是让 KNN 变聪明。

它做的是：
  当某条序列看起来危险时，
  少相信 KNN 的切换建议。

所以 adapter 分布会变保守：
  recent2000 用得更多
  full / recent1500 / recent3000 / zero-shot 用得更少
```

专业解释：

```text
The conservative risk candidate routes more windows back to the fallback family.
This reduces harmful overrides and flips DGS2 from negative to positive, but it
also removes some beneficial overrides, lowering aggregate MAE delta.
```

项目对应：

```text
validation_gated mvl=0.005 selected_counts:
  full: 431
  recent1500: 570
  recent2000: 2462
  recent3000: 629
  zero-shot: 908

downside budget selected_counts:
  full: 307
  recent1500: 409
  recent2000: 3116
  recent3000: 483
  zero-shot: 685
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不是只训练一次就结束 | adapter portfolio lifecycle | multiple adapters |
| 后半段重点是怎么用 | model selection layer | router policy |
| 安全策略会牺牲收益 | risk-return tradeoff | 8/2 with lower delta |
| 发布要看最差伤害 | downside-aware promotion | per-series attribution |

通俗解释：

```text
LoRA 微调完以后，
我们手里不是只有一个模型。

我们有一个 adapter 组合：
  full
  recent1500
  recent2000
  recent3000
  zero-shot

然后真正的问题变成：
  当前窗口该用哪个？
  哪些情况下不该切换？
  哪些序列容易被切换伤到？

这就是为什么我们现在很多工作在 router 上。
不是因为不训练了，
而是因为“训练出来的多个 adapter 怎么组合使用”已经成为更大的杠杆。
```

专业解释：

```text
LoRA specialization creates a portfolio of adapter behaviours. The router is a
model-selection layer over that portfolio. Downside-budget gating turns router
promotion from a pure aggregate metric decision into a risk-aware decision.
```

项目对应：

```text
current portfolio:
  fixed recent windows plus zero-shot baseline

current selector:
  KNN-regret over historical prediction archive

current safety dial:
  per-series downside budget
```

## 8. What Did We Learn This Round?

Fact: Downside-budget routing did not beat the best aggregate KNN-regret policy.

Fact: `validation_gated mvl=0.005` remains the best current research checkpoint
for balancing aggregate lift and series spread: MAE delta `0.0002687244`, split
`7/3`.

Fact: `series_risk_penalized mvl=0.005, min_series=-0.0025, decay=0.25` produced
the best series spread: MAE delta `0.0002451542`, split `8/2`.

Inference: Per-series downside control is useful as a safety dial, but not yet
as the main policy.

Recommendation: Do not replace the current KNN-regret checkpoint with the
downside-budget row. Keep it as a conservative release candidate and continue
investigating why `BAMLH0A0HYM2` and `DEXJPUS` remain hard to route.

## 9. Current Verdict

```text
frontier moved:
  no

risk surface improved:
  yes

best aggregate:
  knn-regret validation_gated mvl=0.0

best current research checkpoint:
  knn-regret validation_gated mvl=0.005

best conservative risk candidate:
  knn-regret series_risk_penalized
  mvl=0.005
  min_series=-0.0025
  decay=0.25

promotion:
  still blocked
```

Next useful question:

```text
Can we predict before routing which series/window combinations should be forced
back to fallback, instead of using only prior per-series validation gates?
```
