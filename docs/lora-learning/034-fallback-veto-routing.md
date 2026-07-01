# 034 - Fallback Veto Routing

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-fallback-veto.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没训练新 LoRA | no new adapter training | same prediction archive |
| 保留 KNN-regret router | base validation-gated selector | `candidate_set=knn-regret` |
| 加一个拦截器 | fallback-veto layer | `evaluate_router_fallback_veto.py` |
| 只用过去数据判断风险 | no-leak chronological replay | prior cuts only |

通俗解释：

```text
上一轮我们知道：

  KNN-regret 有用。
  但它有时候会建议错误切换。

这轮我们没有重新训练 TimesFM。
我们做的是在 router 后面加一个小安全检查：

  KNN 说这次要换 adapter。
  veto 层问：
    过去有没有类似情况？
    类似情况下，这种切换是不是经常比 fallback 更差？

  如果历史相似案例显示风险高：
    不换。
    回到 fallback adapter。
```

专业解释：

```text
This run adds a no-leak fallback-veto diagnostic. The base selector remains
KNN-regret with validation gating. For each current override, the veto layer
retrieves historical override examples from completed prior cuts and estimates
mean regret versus fallback. If estimated regret exceeds a threshold, the
override is replaced with the fallback family.
```

项目对应：

```text
new script:
  scripts/evaluate_router_fallback_veto.py

base router:
  knn-regret validation_gated

fallback:
  recent2000
```

## 2. What Is Fallback?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 默认安全选择 | default baseline adapter | `recent2000` |
| 不知道选谁时用它 | fail-closed behavior | fallback family |
| 不是最强，但稳 | robust baseline | fixed recent window adapter |
| router 必须打赢它 | promotion baseline | delta vs fallback |

通俗解释：

```text
fallback 就是：

  当系统不确定该不该切换时，
  默认用哪个 adapter。

在我们现在的实验里，fallback 是 recent2000。

它不一定每次最好，
但它是目前比较稳的默认选择。
所以新策略必须回答：

  我比 recent2000 好多少？
  我有没有伤到很多序列？
```

专业解释：

```text
Fallback is the fixed adapter family used when a learned selector is not
trusted. It defines the fail-closed behavior and the evaluation baseline. A
router has not earned promotion unless it beats fallback under causal replay.
```

项目对应：

```text
fallback_family:
  recent2000

metric:
  selected_error - fallback_error

good override:
  selected_error < fallback_error

bad override:
  selected_error > fallback_error
```

## 3. What Is Veto?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 拦一下危险决定 | override rejection layer | fallback veto |
| 不重新选专家，只决定是否退回 | post-selector guard | selected -> fallback |
| 只看过去失败案例 | historical regret estimate | prior cuts |
| 保护不是预测答案 | no current-label usage | no leakage |

通俗解释：

```text
veto 不是另一个完整 router。

它不负责从 5 个 adapter 里重新选一个。

它只做一个动作：

  KNN 已经选好了 adapter。
  veto 判断这个选择是否危险。

如果危险：
  把选择改回 fallback。

如果不危险：
  保留 KNN 的选择。
```

专业解释：

```text
The veto layer is a binary post-selector. It receives the selected adapter
family from the base router and decides whether to keep that override or force
fallback. Its target is historical regret versus fallback, not the oracle best
family.
```

项目对应：

```text
base selected family:
  output of validation_gated KNN-regret

veto decision:
  keep selected family
  or force recent2000
```

## 4. What Is Regret?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 选错以后多亏多少 | excess error | selected_error - fallback_error |
| 正数代表伤害 | harmful override | worse than fallback |
| 负数代表收益 | beneficial override | better than fallback |
| veto 学的是这个 | supervised risk target | historical regret |

通俗解释：

```text
regret 可以理解成：

  如果我听了 KNN 的建议，
  比老老实实用 fallback 多错了多少？

如果 regret 是正数：
  KNN 这次害了我们。

如果 regret 是负数：
  KNN 这次帮了我们。
```

专业解释：

```text
For a historical override example:

regret_vs_fallback = selected_error - fallback_error

Positive regret means the override underperformed fallback. Negative regret
means the override improved on fallback. The veto layer estimates expected
regret from nearest historical override examples.
```

项目对应：

```text
historical example fields:
  runtime features
  selected adapter family
  selected_error - fallback_error
```

## 5. Why This Is No-Leak

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 当前答案不参与当前决策 | current-cut labels are hidden | chronological replay |
| 过去答案可以学 | completed cuts can supervise | prior cuts |
| 当前答案只用于最后打分 | labels only for offline evaluation | final metrics |
| 这是能发布前提 | causal validity | no-leak router |

通俗解释：

```text
我们不能这样做：

  看当前窗口哪个 adapter 真正错得少，
  然后说 router 选得好。

那是偷看答案。

这轮的做法是：

  当前 cut 只能使用它之前的 cut。
  过去 cut 已经结束了，所以可以拿来当训练案例。
  当前 cut 的真实误差只能在最后评分时打开。
```

专业解释：

```text
For each evaluation cut, the veto training set is built only from earlier cuts.
The current cut's family errors are excluded from the veto decision and used
only after selection to compute offline metrics.
```

项目对应：

```text
guardrail:
  The fallback-veto classifier trains only on completed prior cuts.
  Current-cut errors are used only for final offline scoring.
```

## 6. Results

Baseline before veto:

| Policy | Min validation | MAE delta | Positive / Negative series |
|---|---:|---:|---:|
| `validation_gated` | 0.000 | 0.0002705342 | 6 / 4 |
| `validation_gated` | 0.005 | 0.0002687244 | 7 / 3 |
| `series_risk_penalized` | 0.005 | 0.0002451542 | 8 / 2 |

Best fallback-veto:

| Base | Feature mode | k | Regret threshold | Vetoed windows | MAE delta | Positive / Negative series |
|---|---|---:|---:|---:|---:|---:|
| `mvl=0.005` | `global` | 50 | 0.0002 | 304 | 0.0003088776 | 9 / 1 |

通俗解释：

```text
这是目前最好的结果。

它做到了两件事：

  总体 MAE delta 从 0.0002705342 提高到 0.0003088776。
  受益/受伤序列从 6/4 或 7/3 改善到 9/1。

也就是说：
  不只是总分变高，
  被伤到的金融序列也明显减少。
```

专业解释：

```text
The no-leak fallback veto moves both aggregate and per-series frontiers. The
best row uses global runtime features, k=50 historical override neighbors, and
a regret threshold of 0.0002. It vetoes 304 routed windows.
```

项目对应：

```text
new best:
  selected_metric = 0.0917144023
  fallback_metric = 0.0920232799
  MAE delta = 0.0003088776
  relative lift = 0.0033565156
  series split = 9/1
```

## 7. Why Global Beat Series Here

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不记具体序列名，泛化更好 | no series one-hot | `feature_mode=global` |
| 看窗口形态和预测分歧 | runtime feature similarity | context/disagreement/alignment |
| 避免记住某条序列过去坏 | less memorization | better frontier |
| 后续还要验证 | needs future archive test | research checkpoint |

通俗解释：

```text
global 的意思是：

  不直接把序列名字喂给 veto。

它主要看：
  这个窗口过去走势怎样？
  各 adapter 的预测分歧大不大？
  预测和上下文是否对齐？
  KNN 选的是哪个 adapter？

这轮 global 更好，说明风险信号可能不是某条序列专属，
而是某类窗口形态本身容易让 KNN 选错。
```

专业解释：

```text
The best row uses global features rather than explicit series one-hot features.
This suggests the veto signal may generalize through runtime geometry and
selected-family context, instead of relying only on per-series identity.
```

项目对应：

```text
feature groups:
  context
  prediction_disagreement
  prediction_disagreement_normalized
  prediction_context_alignment
  prediction_summaries
  selected family one-hot
```

## 8. How To Read k=50 And Threshold=0.0002

| 参数 | 通俗解释 | 专业解释 |
|---|---|---|
| `k=50` | 找 50 个历史相似切换案例 | nearest historical override count |
| `threshold=0.0002` | 平均多亏超过这个数就拦 | max tolerated expected regret |
| `vetoed_windows=304` | 304 次切换被改回 fallback | forced fallback count |

通俗解释：

```text
对于当前一次 KNN 切换建议：

  1. 找过去 50 个最像它的切换案例。
  2. 看这些案例平均有没有比 fallback 更差。
  3. 如果平均多亏超过 0.0002，就 veto。

这不是说 0.0002 是宇宙真理。
它只是当前 archive 上最好的风险阈值。
```

专业解释：

```text
The veto layer estimates local expected regret using nearest historical
override examples. `threshold=0.0002` is the maximum tolerated mean neighbor
regret before forcing fallback.
```

项目对应：

```text
best row:
  feature_mode = global
  k = 50
  regret_threshold = 0.0002
  vetoed_windows = 304
```

## 9. What This Means For LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA adapter 是专家池 | adapter portfolio | full/recent windows/zero-shot |
| KNN 是选专家的人 | local selector | KNN-regret |
| veto 是风控员 | post-selector risk guard | fallback veto |
| 真正系统是组合 | serving policy | selector plus veto |

通俗解释：

```text
现在 Time0 的 LoRA 工作已经不只是：

  训练一个 adapter。

更像：

  训练/收集多个 adapter。
  用 router 选择 adapter。
  用 veto 避免危险切换。
  用 rolling/no-leak 评估确认没有偷看答案。

这比单纯多训练几轮更有价值。
因为我们已经看到：
  同一批 adapter，
  只要选择策略更好，
  效果就能明显推进。
```

专业解释：

```text
LoRA fine-tuning produced the adapter portfolio. The new performance gain comes
from serving-time model selection: KNN-regret proposes an adapter, and fallback
veto rejects overrides with high historical local regret. This is still part of
the LoRA system because it determines how adapter specialization is used.
```

项目对应：

```text
adapter layer:
  full
  recent1500
  recent2000
  recent3000
  zero-shot

selection layer:
  KNN-regret

risk layer:
  fallback veto
```

## 10. Current Verdict

Fact: `knn-regret validation_gated mvl=0.005 + global fallback-veto k50
threshold=0.0002` produced MAE delta `0.0003088776`.

Fact: The same row improved routed-series split to `9/1`.

Fact: The only remaining negative series in that row was
`DEXJPUS:realized_vol_20`.

Fact: `mvl=0.005 + veto` beat `mvl=0.0 + veto`, even though `mvl=0.0` was the
previous best aggregate baseline before veto.

Inference: The router should not simply route more aggressively. The stronger
pattern is moderate validation gating followed by a local fallback-veto risk
layer.

Recommendation: Treat fallback-veto as the new best research checkpoint. Do
not call it release-ready until it is tested on a later archive or a second
target.

## 11. Next Useful Step

```text
Turn fallback-veto from a diagnostic script into a formal router policy, then
test whether the same policy holds on another target or a later archive.
```

This matters because:

```text
diagnostic script:
  proves the signal exists

formal router policy:
  makes it part of the reusable Time0 serving/evaluation surface

second archive or target:
  tests whether the gain generalizes
```
