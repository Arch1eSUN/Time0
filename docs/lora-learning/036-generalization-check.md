# 036 - Generalization Check

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-expanded-fallback-veto-generalization.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没训练新 LoRA | no new adapter training | same adapter portfolio |
| 换了一个评估面 | second router-row surface | `router-rows-expanded...` |
| 测正式 fallback-veto 是否还能赢 | generalization check | `--policy fallback_veto` |
| 结果失败 | negative transfer | delta below fallback |

通俗解释：

```text
上一轮我们已经证明：

  fallback-veto 在 alignment-normalized 表面上很好。

但这还不等于它真的泛化。

所以这轮我们故意换一个 router-row 表面：

  expanded surface

它少了一些我们后来加的强特征。
然后我们问：

  同一个正式 fallback-veto policy，
  到这个弱一点的表面上还能赢吗？
```

专业解释：

```text
This round evaluates formal `fallback_veto` on a second router-row surface:
`router-rows-expanded-market-macro-realized-vol-20-h20-r4.json`. This surface is
not alignment-normalized and lacks the latest alignment features.
```

项目对应：

```text
previous best surface:
  router-rows-early-regime-ablate-alignment-normalized...

generalization surface:
  router-rows-expanded...
```

## 2. What Is Generalization?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不是只在这张卷子考得好 | performance beyond one archive | second surface |
| 换数据还要有效 | out-of-sample robustness | later/broader rows |
| 换特征还要小心 | feature-surface shift | missing feature groups |
| 泛化失败也有价值 | negative evidence | promotion blocker |

通俗解释：

```text
如果一个策略只在一份数据上很好，
我们不能马上说它真的强。

这就像：
  你只背了一张考卷的答案。

generalization 要问：
  换一张卷子，你还会吗？

这轮就是换卷子。
结果是：
  它没完全会。
```

专业解释：

```text
Generalization means the policy preserves lift outside the archive or feature
surface used to discover it. A policy that fails this check remains a research
checkpoint, not a release candidate.
```

项目对应：

```text
alignment-normalized result:
  MAE delta = 0.0003088776
  split = 9/1

expanded result:
  MAE delta = -0.0000468273
  split = 5/5
```

## 3. What Changed Between The Two Surfaces?

| Feature group | Alignment-normalized surface | Expanded surface |
|---|---:|---:|
| `context` | yes | yes |
| `prediction_disagreement` | yes | yes |
| `prediction_summaries` | yes | yes |
| `prediction_context_alignment` | yes | no |
| `prediction_disagreement_normalized` | yes | no |

通俗解释：

```text
expanded surface 不是完全不同的数据领域。

但它少了两个重要信息：

  预测和历史上下文是否对齐
  预测分歧相对于历史尺度到底大不大

这两个信息在上一轮很可能帮 veto 判断：
  这次 KNN 的切换到底危险不危险。
```

专业解释：

```text
The expanded surface is a weaker feature surface. It lacks alignment and
normalized disagreement features, which means the local veto neighbor geometry
is not equivalent to the alignment-normalized surface.
```

项目对应：

```text
missing:
  prediction_context_alignment
  prediction_disagreement_normalized
```

## 4. Results

Sweep ranking on expanded surface:

| Rank | Policy | Min validation | Threshold | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|
| 1 | `fallback_veto` | 0.000 | 0.00015 | -0.0000468273 | 5 / 5 |
| 2 | `fallback_veto` | 0.005 | 0.00015 | -0.0000468273 | 5 / 5 |
| 3 | `fallback_veto` | 0.000 | 0.00020 | -0.0000737068 | 4 / 6 |
| 4 | `fallback_veto` | 0.005 | 0.00020 | -0.0000737068 | 4 / 6 |
| 7 | `validation_gated` | 0.000 | - | -0.0002021702 | 4 / 6 |
| 8 | `validation_gated` | 0.005 | - | -0.0002021702 | 4 / 6 |

通俗解释：

```text
这轮结果要分两层看：

第一层：
  fallback-veto 比 validation_gated 少亏。

第二层：
  但它还是亏。

所以不能说泛化成功。
只能说：
  veto 仍然有一点保护作用，
  但这个弱特征面不够让它真正打赢 fallback。
```

专业解释：

```text
Fallback-veto reduced the validation-gated loss on the expanded surface, but it
did not clear the fallback baseline. Best expanded MAE delta remained negative:
`-0.0000468273`.
```

项目对应：

```text
validation_gated expanded:
  MAE delta = -0.0002021702

fallback_veto expanded:
  MAE delta = -0.0000468273

required for promotion:
  delta > 0
```

## 5. Why This Is A Useful Failure

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它告诉我们不能乱发布 | promotion blocked | delta negative |
| 它告诉我们特征很重要 | feature-surface dependency | missing alignment |
| 它保留了一点信号 | partial risk reduction | less negative than baseline |
| 它指出下一步 | build comparable later archive | same feature groups |

通俗解释：

```text
失败不是白跑。

它告诉我们：

  fallback-veto 不是“到哪里都能赢”的万能策略。

它更可能依赖：
  alignment-normalized 这套更强的特征。

所以我们不能把它包装成通用金融 adapter router。
现在只能说：
  它在 alignment-normalized surface 上是当前最好研究结果。
```

专业解释：

```text
This is negative transfer under feature-surface shift. The policy concept still
has signal because it reduces validation-gated loss, but it fails promotion
because the absolute delta against fallback is negative.
```

项目对应：

```text
promotion:
  blocked outside alignment-normalized surface

scope:
  current best only applies to alignment-normalized rows
```

## 6. Attribution

Top positive expanded series:

| Series | MAE delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | 0.0005268410 |
| `DGS2:realized_vol_20` | 0.0000272370 |
| `DEXJPUS:realized_vol_20` | 0.0000100944 |

Top negative expanded series:

| Series | MAE delta vs fallback |
|---|---:|
| `DGS10:realized_vol_20` | -0.0006345752 |
| `SP500:realized_vol_20` | -0.0001922201 |
| `VIXCLS:realized_vol_20` | -0.0001554748 |

通俗解释：

```text
这次最拖后腿的是：

  DGS10
  SP500
  VIXCLS

它们的损失超过了 DFF 等正收益序列带来的好处。
所以总分还是负的。
```

专业解释：

```text
The expanded result is dominated by negative contributions from DGS10, SP500,
and VIXCLS. Positive DFF lift is not enough to offset those losses.
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 一个好结果不能马上发布 | single-surface lift is insufficient | research checkpoint |
| 特征工程会改变 router 能力 | feature surface matters | alignment-normalized rows |
| 风控策略也会过拟合 | policy overfitting risk | archive-specific threshold |
| 泛化测试是必要步骤 | external validation | second surface |

通俗解释：

```text
LoRA 微调项目里，
不是看到一次好结果就结束。

我们还要问：

  换一批数据还好吗？
  换一个特征表面还好吗？
  换一个目标还好吗？

这轮答案是：
  换弱特征表面以后不好。

所以它提醒我们：
  当前成果还在研究阶段。
```

专业解释：

```text
Adapter routing quality depends on both the adapter portfolio and the runtime
feature surface. A policy discovered on one feature surface can fail under
feature shift even when the target and adapter families are unchanged.
```

项目对应：

```text
current best remains:
  alignment-normalized fallback_veto

not yet true:
  fallback_veto is universally promotable
```

## 8. Current Verdict

Fact: On the expanded surface, best fallback-veto MAE delta was
`-0.0000468273`, so it did not beat fallback.

Fact: Expanded fallback-veto still improved over expanded validation-gated,
which had MAE delta `-0.0002021702`.

Fact: Expanded rows lack `prediction_context_alignment` and
`prediction_disagreement_normalized`.

Inference: fallback-veto likely depends on the richer alignment-normalized
feature surface. The policy concept has signal, but it is not feature-agnostic.

Recommendation: Keep formal fallback-veto as the best alignment-normalized
research checkpoint. Do not promote it globally. Next, build or export a later
alignment-normalized archive and retest there.

## 9. Next Useful Step

```text
Build a later alignment-normalized router-row archive and rerun formal
fallback_veto there.
```

Why:

```text
expanded surface:
  tests feature-surface shift

later alignment-normalized surface:
  tests time generalization while keeping the feature interface comparable
```
