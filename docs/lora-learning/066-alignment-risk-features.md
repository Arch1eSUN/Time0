# 066 - Alignment-Risk Features

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-alignment-risk-features.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给路由器多看一组信息 | add a feature surface | `--feature-surface alignment-risk` |
| 让它看预测和历史像不像 | prediction-context alignment | `prediction_context_alignment` |
| 看 selected adapter 是否比 fallback 更危险 | selected-vs-fallback displacement | derived alignment-risk features |
| 用 strict gate 判断能不能晋级 | fail-closed validation | `strict_gate_no_candidate` |

通俗解释：

```text
这一轮不是继续训练更多 epoch，
也不是改 LoRA rank。

这一轮是在问：

  adapter router 做决定时，
  要不要多看一些“预测和历史上下文是否冲突”的信息？

如果这些信息有用，
router 应该更知道什么时候退回 fallback，
什么时候不要错杀某个 adapter。
```

专业解释：

```text
This run adds an opt-in alignment-risk feature surface to the expected-regret
fallback veto. The target remains expected regret versus fallback. The change is
only the input representation used by the veto model.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/router_fallback_veto.py
  experiments/timesfm-lora/scripts/validate_multifold_expected_regret_veto.py

flag:
  --feature-surface alignment-risk
```

## 2. What Is A Feature Surface?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型能看见的桌面 | feature surface | model input representation |
| 同一件事换个观察角度 | representation change | base vs alignment-risk |
| 不是标签 | no future labels | no-leak runtime features |
| 会影响模型学到什么 | inductive bias | expected-regret model input |

通俗解释：

```text
假设你判断一个人今天会不会迟到。

你可以只看：

  昨天有没有迟到。

也可以多看：

  今天下不下雨。
  距离公司远不远。
  是否高峰期。

这些“你能看的信息”，就是 feature surface。

feature surface 不是答案。
它只是模型做判断时能看到的线索。
```

专业解释：

```text
A feature surface is the full input representation exposed to a learned module.
For this project, the learned module is not TimesFM itself. It is the adapter
router/veto model deciding whether a selected adapter should be kept or replaced
by the fallback adapter.
```

项目对应：

```text
base surface:
  normalized runtime features
  prediction summaries
  selected family one-hot

alignment-risk surface:
  base surface
  plus selected/fallback alignment displacement features
```

## 3. Why This Matters For LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 不是孤立使用的 | adapter is part of a system | TimesFM + adapters + router |
| 选错 adapter 也会输 | routing risk | selected family can hurt |
| router 也是训练对象 | learned decision module | expected-regret veto |
| 输入设计会决定上限 | representation bottleneck | feature surface |

通俗解释：

```text
我们最后想要的不是“有一个 LoRA 文件”。

我们想要的是：

  在金融时序里，
  系统知道什么时候用 zero-shot，
  什么时候用 recent1500，
  什么时候用 recent2000，
  什么时候用 recent3000，
  什么时候干脆退回 fallback。

所以 LoRA 项目真正训练的是一套系统：

  base model
  adapter pool
  router
  fail-closed validation
```

专业解释：

```text
Adapter specialization has two layers. The adapter changes model behavior, while
the router decides when that specialized behavior should be used. If the router
feature surface is weak, a stronger adapter can still lower system-level
performance because the wrong adapter is selected on the wrong windows.
```

项目对应：

```text
adapter families:
  zero-shot
  full
  recent1500
  recent2000
  recent3000

fallback:
  recent2000
```

## 4. What Alignment-Risk Means

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 预测走势和过去走势差很多 | trend displacement | predicted_trend_minus_past_trend |
| 预测最后值离历史最后值很远 | last-value displacement | predicted_last_delta_from_past_last_over_std |
| 预测均值离历史最后值很远 | mean displacement | predicted_mean_delta_from_past_last_over_std |
| selected 比 fallback 更极端 | relative adapter risk | selected-minus-fallback abs displacement |

通俗解释：

```text
如果过去一段时间很平稳，
但某个 adapter 预测突然大跳，
这不一定是错。

但是它更危险。

如果 fallback 比 selected 稳，
router 可能应该退回 fallback。

如果 selected 的大跳正好是必要信号，
router 不应该退。

alignment-risk 特征就是把这种“危险程度”显式告诉 router。
```

专业解释：

```text
The added features are deterministic transforms of existing no-leak runtime
features. They measure selected adapter displacement, fallback displacement,
selected-minus-fallback displacement, family maximum displacement, and direction
mismatch against the past context.
```

项目对应：

```text
extra feature examples:
  selected_abs_predicted_trend_minus_past_trend
  fallback_abs_predicted_trend_minus_past_trend
  selected_minus_fallback_abs_predicted_trend_minus_past_trend
  selected_predicted_trend_sign_mismatch
```

## 5. Why More Features Can Hurt

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 线索多了也可能乱 | feature noise | alignment-risk underperforms base |
| 模型可能记住偶然规律 | overfitting | validation fold regression |
| 总体好不代表未来稳 | aggregate positive is insufficient | robust vs strict |
| strict gate 防止自欺欺人 | fail-closed promotion gate | strict positive = 0 |

通俗解释：

```text
给模型更多信息，不等于模型更聪明。

有时候更多信息会让模型学到：

  某一段 validation 的偶然规律。

看起来它在某些地方更积极，
但换一个时间段就伤害更多。

这就是为什么我们不用“看起来有提升”当成功标准。
```

专业解释：

```text
The alignment-risk surface increased loose no-series robust-pass candidates
from 14 to 16, but utility-positive candidates fell from 5 to 0. This suggests
the extra features add degrees of freedom without improving fold-level
generalization.
```

项目对应：

```text
base no-series:
  robust_pass: 14
  utility_positive: 5
  strict_positive: 0

alignment-risk no-series:
  robust_pass: 16
  utility_positive: 0
  strict_positive: 0
```

## 6. Strict Gate vs Robust Diagnostic

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| strict 是能不能发布 | promotion gate | `--selection-gate strict` |
| robust 是看有没有信号 | diagnostic gate | `--selection-gate robust` |
| strict 不过就不看 final | fail closed before holdout | final untouched |
| robust 可以看 final 但不能当发布证据 | diagnostic final check | not promotion |

通俗解释：

```text
strict gate 的规则更狠：

  validation 每一折都不能坏。

robust gate 更宽：

  总体不错，就拿去 final 看看。

所以：

  strict 代表能不能晋级。
  robust 代表值不值得继续研究。
```

专业解释：

```text
Strict validation requires zero fold metric regressions and zero downside
regressions under the configured gate. Robust mode can evaluate final holdout
for diagnosis, but it is not sufficient for release because it permits
validation fold regressions.
```

项目对应：

```text
alignment-risk include-series strict:
  strict_positive: 0
  verdict: strict_gate_no_candidate

alignment-risk include-series robust:
  final_metric_delta: +0.0001575894
  final_relative_lift: +0.0002233868
  verdict: future_validated_positive
```

## 7. What The Result Means

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 这轮没有成功晋级 | no promoted candidate | strict_positive = 0 |
| alignment-risk 有信号但不够稳 | signal with instability | fold regression remains |
| include-series 比 no-series 更接近 | identity helps here | one small bad fold |
| 不能把它设成默认 | no promotion | keep opt-in |

通俗解释：

```text
这轮不是“模型更强了”。

更准确地说：

  我们找到了一个有信息量的观察角度，
  但这个观察角度太粗，
  直接塞进去会带来噪声。

所以它应该保留为实验开关，
不能作为最终金融 adapter-router 的默认方案。
```

专业解释：

```text
The raw alignment-risk feature surface is a negative promotion result. It
improves some diagnostic surfaces but does not beat the base feature surface on
strict validation or final robust comparison.
```

项目对应：

```text
base include-series robust final_metric_delta:
  +0.0001617361

alignment-risk include-series robust final_metric_delta:
  +0.0001575894

base is still slightly better.
```

## 8. The LoRA Lesson From This Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练不是一直加东西 | model development is controlled ablation | one lever per run |
| 负结果也有价值 | falsification | do not promote alignment-risk |
| router 输入就是能力边界 | representation controls decision quality | feature surface |
| 下一步要变小变稳 | reduce degrees of freedom | compact/regularized surface |

通俗解释：

```text
做 LoRA 微调项目时，
不要只问：

  loss 有没有下降？
  final 有没有一处变好？

要问：

  哪个模块变了？
  它看到了什么输入？
  它在哪些时间折上失败？
  失败是偶然一两个窗口，还是系统性问题？

这才是把模型训练成垂直领域模型的过程。
```

专业解释：

```text
This run is an ablation over representation, not adapter weights. The evidence
rejects the raw alignment-risk surface as a promotion candidate while preserving
it as a diagnostic seam for smaller feature selection or stronger
regularization.
```

项目对应：

```text
keep:
  --feature-surface alignment-risk

do not promote:
  alignment-risk as default surface

next:
  smaller selected-only alignment surface
  stronger regularization
  feature selection around cut4000 failures
```

## 9. Next Round

Recommendation:

```text
Do not add more raw alignment columns.

Next test should reduce the surface:

  selected-only alignment risk
  or top-k alignment features from attribution
  or stronger l2/feature regularization

The target is still:

  strict_positive > 0
  zero fold metric regressions
  final holdout evaluated only after strict pass
```
