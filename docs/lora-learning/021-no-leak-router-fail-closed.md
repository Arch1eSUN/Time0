# 021 - No-Leak Router And Fail-Closed Selection

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-prediction-router.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练一个小裁判选 adapter | prediction-level router | `evaluate_prediction_router.py` |
| 只用过去考试训练 | chronological no-leak evaluation | train prior cuts only |
| 如果小裁判证据不够，就别让它上场 | fail-closed validation gate | fallback `recent2000` |
| 看它是否比固定选择更好 | baseline comparison | fixed `recent2000` |

通俗解释：

```text
上一轮我们做出了 router rows。

这轮我们开始问：
能不能真的训练一个小 router，
让它看到当前窗口的过去走势和 5 个 adapter 的预测，
然后判断该选哪个 adapter？

答案：
现在还不能。

不是因为 router 没有任何信号，
而是因为它还没有稳定超过固定 recent2000。
```

专业解释：

```text
We evaluated no-leak prediction-level adapter routing. Learned policies train
only on prior cuts and evaluate on future cuts. Labels are used only during
offline training/evaluation, never as runtime features.
```

项目对应：

```text
input: router rows JSON
model family: softmax classifier + kNN regret diagnostics
fallback: fixed recent2000
gate: require 1% validation lift before switching away from fallback
```

## 2. What Is A No-Leak Router?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只根据已发生的信息做决定 | decision-time feature constraint | runtime_features only |
| 训练可以用历史答案 | supervised training on prior outcomes | prior labels |
| 测未来时不能偷看未来答案 | chronological holdout | future cut evaluation |
| 选择 adapter 也是模型行为 | policy evaluation | router report |

通俗解释：

```text
如果我们要预测 cut5500，
router 可以用 cut4000 和 cut5000 里已经发生过的结果学习。

但它不能看 cut5500 的真实未来。

这就像：
你可以复习以前考过的卷子，
但不能在考试时看本次考试答案。
```

专业解释：

```text
A no-leak router is a policy whose training data is strictly earlier than the
evaluation cut. The evaluation cut can be used only after selection, to score
the chosen family.
```

项目对应：

```text
cut5000:
  train: cut4000
  evaluate: cut5000

cut5500:
  train/validation: cut4000/cut5000
  evaluate: cut5500
```

## 3. What Policies Did We Test?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 永远选同一个 adapter | fixed-family baseline | `fixed:recent2000` |
| 学一个线性分类器 | softmax classifier | `softmax` |
| 找历史上相似的窗口 | k-nearest-neighbor regret router | `knn_regret_*` |
| 先在历史验证集上过关再启用 | validation-gated policy | `validation_gated` |

通俗解释：

```text
我们没有只看一个 router。

我们同时看了几类选择方法：

1. 固定选 recent2000
2. 用线性模型学“什么窗口选什么 adapter”
3. 找历史相似窗口，看当时哪个 adapter 错得少
4. 如果学习型 router 没有明显超过 fallback，就继续用 fallback
```

专业解释：

```text
The evaluation separates learned-router diagnostics from a deployable
validation-gated policy. Diagnostics show whether signal exists. The gate
decides whether the learned policy is safe to use on a future cut.
```

项目对应：

```text
best diagnostic: knn_regret_series_k100
deployable policy: validation_gated
fallback family: recent2000
```

## 4. What Did The Results Show?

Routed cuts only:

| Policy | MAE | MAE improvement vs zero-shot |
|---|---:|---:|
| fixed `recent2000` | 0.1037657315 | 1.507294% |
| best learned diagnostic | 0.1040911166 | 1.198444% |
| validation-gated router | 0.1037657315 | 1.507294% |
| leaky per-window oracle | 0.1003816976 | 4.719363% |

通俗解释：

```text
最强的学习型 router 没有打过固定 recent2000。

所以如果我们强行让 router 上线，
反而会变差。

validation-gated router 做对了一件事：
它没有逞强。
它发现学习型 router 证据不够，
于是继续用 recent2000。
```

专业解释：

```text
The best learned chronological diagnostic improved over zero-shot but
underperformed the fixed recent2000 baseline. The validation-gated policy
therefore stayed on the fallback and matched fixed recent2000.
```

项目对应：

```text
router success: no
fail-closed success: yes
promotion: blocked
```

## 5. What Is Fail-Closed?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不确定时回到安全默认值 | conservative fallback behavior | `fallback_family` |
| 不让弱模型替换强 baseline | baseline-protecting gate | `min_validation_lift` |
| 宁可不升级，也不要退步 | safety over novelty | promotion blocked |
| 这是工程质量，不是失败掩盖 | controlled rollout | validation gate |

通俗解释：

```text
fail-open 是：
“这个新 router 看起来挺聪明，直接用吧。”

fail-closed 是：
“它必须先证明自己明显更好，否则继续用老方案。”

我们现在用的是 fail-closed。
这对模型系统很重要，因为新模型很容易在某个切分上看起来有效，
但未来窗口反而更差。
```

专业解释：

```text
Fail-closed selection means the system preserves the fallback policy unless the
candidate policy clears a predeclared validation threshold. It reduces the risk
of deploying a model that wins by noise.
```

项目对应：

```text
fallback validation MAE: 0.0790878921
best learned validation MAE: 0.0785417045
required MAE to switch: 0.0782970132

best learned did not clear the threshold.
selected policy stayed fixed:recent2000.
```

## 6. Why Did The Router Not Win Yet?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 练习题太少 | insufficient chronological supervision | only 3 cuts |
| 只有一次真正的验证机会 | weak validation depth | cut5000 validates cut5500 |
| 作弊上限高，不代表可学习 | oracle-policy gap | 4.72% oracle vs 1.20% learned |
| 特征可能还不够表达 regime | feature insufficiency | context/disagreement only |

通俗解释：

```text
我们看到一个矛盾：

作弊 oracle 很强，
说明“如果知道谁会赢”，adapter 选择很有用。

但 no-leak router 不强，
说明它现在还不知道怎么提前判断谁会赢。

这不是要放弃 router。
这说明我们要给 router 更多历史切分，
让它看到更多“过去发生过的考试”。
```

专业解释：

```text
The oracle-policy gap suggests selection headroom exists, but the current
router features and training cuts are insufficient to learn that selection
function robustly.
```

项目对应：

```text
available cuts: 4000,5000,5500
real prior-validation decisions: 1
next need: expanded rolling cut grid
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 多个 LoRA adapter 不等于自动更强 | candidate experts need a valid selector | router required |
| selector 也要被严格测试 | routing policy is a model | no-leak eval |
| 有上限不等于能达到上限 | oracle headroom is not deployable evidence | promotion blocked |
| 好系统要会拒绝升级 | fail-closed model governance | fallback `recent2000` |

通俗解释：

```text
LoRA 微调不是：
训练几个 adapter，然后挑一个看起来最好的就结束。

真正要做成系统，需要三层证据：

1. adapter 自己有没有比 zero-shot 好
2. router 能不能在未来窗口选得更好
3. router 不确定时会不会退回安全 baseline

这一轮证明的是第 3 点做对了。
第 2 点还没过。
```

专业解释：

```text
Adapter routing is a second-stage model-selection problem. It requires its own
chronological validation and fallback policy. A high oracle score is a research
signal, not a promotion criterion.
```

项目对应：

```text
adapter candidate: recent2000 remains strongest fixed fallback
router candidate: not promotion-ready
next experiment: more cuts, not publication
```

## 8. What We Should Do Next

Recommendation:

```text
Do not publish the router.
Do not integrate into Moirai yet.
Do not jump to larger LoRA rank yet.
Expand the rolling cut grid first.
```

下一轮应该做：

```text
add cuts:
  3500
  3750
  4250
  4500
  4750
  5250

rerun archive export for the same 5 families
rebuild router rows
rerun no-leak router evaluation
```

成功标准：

```text
learned router beats fixed recent2000 on routed future cuts
validation-gated policy switches only after prior validation evidence
promotion remains blocked unless router beats fallback, not just zero-shot
```
