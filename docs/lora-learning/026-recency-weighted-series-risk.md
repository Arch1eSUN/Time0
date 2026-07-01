# 026 - Recency-Weighted Series Risk

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-series-risk-penalty.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最近的小考更重要 | recency-weighted validation | `--series-risk-decay` |
| 旧证据不是不要，而是降权 | exponential decay | older validation cut weight < recent cut |
| 每个 series 有自己的风险分 | per-series risk score | `risk_score` |
| 风险分不够就回到安全方案 | fallback on weak series evidence | fixed `recent2000` |

通俗解释：

```text
上一轮我们发现：

把所有历史平均，会太钝。
历史任何一次失败就封杀，又太死。

所以这轮换成第三种办法：

最近一次 validation 最重要。
更早的 validation 也看，
但它的权重变小。

这就像判断一个人最近状态：
昨天的表现最重要，
上个月的表现可以参考，
但不能让上个月的一次失误压过昨天的好表现。
```

专业解释：

```text
We added a recency-weighted series-risk gate. For a selected router candidate,
the policy replays prior chronological validation cuts and computes a per-series
weighted candidate-vs-fallback score. The most recent validation cut has weight
1.0; older cuts decay geometrically by `series_risk_decay`.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/summarize_router_attribution.py

new policy:
  --policy series_risk_penalized

default decay:
  --series-risk-decay 0.1

fallback:
  recent2000
```

## 2. What Is Decay?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 权重会变小 | exponential decay | `decay ** distance` |
| 最近证据权重 1 | most recent validation weight = 1.0 | cut4000 before cut4250 |
| 上一次之前的证据权重 0.1 | previous cut weight = 0.1 when decay=0.1 | cut3750 before cut4250 |
| decay 越大，旧历史越有影响 | slower decay keeps older evidence stronger | 0.5/1.0 regressed |

通俗解释：

```text
decay = 0.1 的意思是：

最近一次小考：
  权重 1.0

再早一次小考：
  权重 0.1

再再早一次小考：
  权重 0.01

所以旧历史还在，
但不会轻易压过最近状态。
```

专业解释：

```text
For validation cuts ordered from old to new, the weight is:

  weight = series_risk_decay ** distance_from_latest_validation_cut

With `decay=0.1`, the latest validation cut dominates the decision while older
cuts act as weak prior evidence.
```

项目对应：

```text
target cut: 4250
prior validation cuts used by risk policy:
  cut3750 weight 0.1
  cut4000 weight 1.0
```

## 3. What Is A Risk Score?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 正数表示 router 比 fallback 好 | positive lift vs fallback | `risk_score > 0` |
| 负数表示 router 有伤害风险 | negative lift vs fallback | `risk_score < 0` |
| 分数按 series 单独算 | subgroup-level metric | `series_id` |
| 分数不够就不让 router 接管 | serving-time guard | per-series fallback |

通俗解释：

```text
risk_score 不是模型训练 loss。

它是一个“是否允许接管”的分数。

如果某个 series 的 risk_score 是正的：
说明历史验证里 learned router 加权后比 recent2000 好。

如果 risk_score 是负的：
说明 learned router 对这个 series 有风险，
那这个 series 继续用 recent2000。
```

专业解释：

```text
The risk score is the relative improvement of weighted fallback MAE over
weighted candidate MAE:

  risk_score = (weighted_fallback_metric - weighted_candidate_metric)
               / weighted_fallback_metric

It is not a gradient-training objective. It is a causal serving-policy score
computed only from prior validation cuts.
```

项目对应：

```text
DFF at cut4250:
  risk_score = 0.0188600061
  allowed = true

DGS10 at cut4250:
  risk_score = -0.0009757999
  allowed = false

SP500 at cut4250:
  risk_score = -0.0012814833
  allowed = false
```

## 4. What Did We Compare?

Routed cuts only:

| Policy | Main rule | MAE delta vs fallback | Relative lift vs fallback | Improvement vs zero-shot | Negative series |
|---|---|---:|---:|---:|---:|
| validation-gated | global latest cut only | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-guarded | latest cut per series | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk decay 0.05 | recency-weighted series risk | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk decay 0.10 | recency-weighted series risk | 0.0002025053 | 0.211207% | 2.194601% | 5 |
| series-risk decay 0.25 | recency-weighted series risk | 0.0001436530 | 0.149826% | 2.134181% | 5 |
| series-risk decay 0.50 | recency-weighted series risk | 0.0001260041 | 0.131419% | 2.116398% | 5 |
| series-risk decay 1.00 | equal-weight historical risk | 0.0001260041 | 0.131419% | 2.116398% | 5 |

通俗解释：

```text
结果不是“新策略超过旧策略”。

结果是：

如果最近证据非常重，
risk policy 能恢复当前最好结果。

如果旧证据权重稍微变大，
结果就退化。

这告诉我们：
这个金融时序任务里，近期 regime 信号比旧平均历史更重要。
```

专业解释：

```text
The recency-weighted policy ties the previous best when decay is 0.05 or 0.1.
It does not exceed `series_guarded`. Performance degrades as older validation
cuts receive more weight, confirming that stale positive evidence can hide
recent series-level regressions.
```

项目对应：

```text
best current policy:
  series_guarded
  or series_risk_penalized with series_risk_decay=0.1

promotion:
  still blocked
```

## 5. What Happened At Cut4250?

| Series | cut3750 lift | cut4000 lift | decay 0.1 risk score | Decision |
|---|---:|---:|---:|---|
| DFF | -0.412462% | 2.002505% | 1.886001% | allow |
| DGS10 | 3.886813% | -0.357423% | -0.097580% | block |
| SP500 | 1.150351% | -0.205523% | -0.128148% | block |

通俗解释：

```text
DFF：
  旧小考失败，但最近小考赢很多。
  所以保留它。

DGS10：
  旧小考赢，但最近小考输了。
  所以挡掉它。

SP500：
  旧小考赢，但最近小考输了。
  所以挡掉它。
```

专业解释：

```text
At cut4250, the risk policy keeps the dominant positive contributor DFF because
recent validation evidence is strongly positive. It blocks DGS10 and SP500
because their weighted MAE lift turns negative once the latest validation cut
dominates stale positive evidence.
```

项目对应：

```text
cut4250 selected config:
  knn_regret_no_series_k50

blocked series:
  DGS10:realized_vol_20
  SP500:realized_vol_20

kept positive contributor:
  DFF:realized_vol_20
```

## 6. Why This Still Does Not Promote The Model

| Blocker | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| 没超过当前最佳 | 只是追平，不是突破 | no incremental lift over best policy | same as `series_guarded` |
| cut4000 证据仍然太少 | 那时只有一次 prior validation | sparse early validation history | only cut3750 available |
| 负 series 仍然存在 | 还有 series 被伤害 | residual subgroup regressions | 5 negative routed series |
| DFF 仍然贡献过大 | 收益集中在少数 series | concentration risk | DFF = 92.526997% of net delta |

通俗解释：

```text
这轮不是失败，也不是成功发布。

它证明了一件事：

我们不能靠“更复杂的 guard”自然超过当前最好结果。

真正的问题是：
前面的历史切片太少，
router 学不到足够稳定的早期风险。

所以 cut4000 还是会有盲区。
```

专业解释：

```text
The policy adds a deeper diagnostic interface, but it is not Promotion Ready
evidence. The limiting factor is not only gate shape; it is the amount and
placement of chronological supervision before early routed cuts.
```

项目对应：

```text
cut4000:
  prior validation evidence = cut3750 only
  risk policy has no extra cut to learn from

next useful direction:
  expand earlier chronological cut grid
  or add richer no-leak runtime features
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA adapter 不是单独发布就完事 | adapter needs serving evidence | router guard |
| 最近数据可能比旧数据更重要 | non-stationary time-series validation | decay 0.1 |
| 复杂策略不一定更强 | added policy must beat baseline | no promotion |
| 负结果能省掉错误路线 | negative result narrows search space | stop hard-gate tuning |

通俗解释：

```text
LoRA 微调本身只是让模型学到一个新补丁。

但真实系统要回答：

什么时候用这个补丁？
什么时候不要用？
旧数据和新数据冲突时信谁？

这轮给出的答案是：
在当前金融风险任务里，新数据更重要。
但光靠这个还不够发布。
```

专业解释：

```text
LoRA adaptation and adapter-serving policy are separate Modules. The adapter
changes the forecast distribution; the serving policy decides whether that
adapter should be trusted for a future window. For non-stationary financial
series, validation evidence must preserve chronological locality.
```

项目对应：

```text
current best:
  series_guarded
  series_risk_penalized decay 0.1 ties it

not enough:
  no new net lift
  no broad per-series stability
  no publication
```

## 8. Current Verdict

Fact: `series_risk_penalized` with decay `0.1` ties the previous best
`series_guarded` policy.

Fact: decay `0.25+` degrades performance; decay `0.5+` falls back to the same
result as validation-gated.

Fact: the policy keeps DFF at cut4250 and blocks DGS10/SP500.

Inference: recency weighting is the right direction, but the current data grid
does not contain enough earlier chronological evidence to beat the latest-cut
guard.

Recommendation: stop tuning hard guard shapes for now. The next controlled
experiment should expand the earlier rolling cut grid so cut4000 has more prior
validation evidence, or add richer no-leak runtime features for series risk.
