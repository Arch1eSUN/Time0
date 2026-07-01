# 029 - Feature Ablation

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-feature-ablation.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把新特征一组一组拿掉 | feature ablation | `ablate_router_features.py` |
| 看少了哪组就变差 | measure marginal contribution | preset comparison |
| 不重新训练 LoRA | reuse existing adapters | same prediction archives |
| 不偷看答案 | preserve no-leak guard | runtime key validation |

通俗解释：

```text
上一轮我们给 router 加了很多新信息。

但我们还不知道：
到底是哪一类信息真的有用？

所以这轮做一个拆解实验：

只保留 A
只保留 B
保留 A+B
全部保留

然后看谁的结果最好。
```

专业解释：

```text
We performed feature-group ablation over no-leak router-row runtime features.
Each ablated report keeps the same rows, labels, adapters, and chronological
evaluation logic, changing only the visible runtime feature groups.
```

项目对应：

```text
new script:
  scripts/ablate_router_features.py

source rows:
  reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json

best preset:
  alignment-normalized
```

## 2. What Is Feature Ablation?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把零件拆掉看机器还转不转 | remove one feature group at a time | preset rows |
| 变差说明这个零件有用 | lower performance implies contribution | delta vs fallback |
| 变好说明这个零件可能干扰 | removal can reduce noise | context_regime |
| 不变说明这个零件暂时没价值 | no marginal signal | compare table |

通俗解释：

```text
假设你做了一碗汤，加了：
盐
糖
胡椒
酱油

现在汤变好喝了。

但你不知道是谁的功劳。

ablation 就是：
拿掉盐试试
拿掉糖试试
只留胡椒试试

最后判断哪个调料真的有用。
```

专业解释：

```text
Feature ablation isolates the contribution of feature groups by holding the
dataset, labels, model, and evaluation protocol constant while varying only the
input feature surface.
```

项目对应：

```text
held constant:
  rows = 5500
  cuts = early grid
  adapters = unchanged
  router policies = unchanged

changed:
  runtime feature groups visible to router
```

## 3. What Did Each Preset Mean?

| Preset | 通俗解释 | 专业解释 |
|---|---|---|
| baseline | 原来的信息 | context + prediction summaries + raw disagreement |
| context-regime | 加“当前市场状态” | add volatility/range/trend regime features |
| normalized-disagreement | 加“分歧相对当前波动有多大” | scale disagreement by context mean/std |
| alignment | 加“预测是否贴合当前历史” | prediction-context alignment features |
| regime-alignment | 市场状态 + 预测贴合 | context_regime + alignment |
| alignment-normalized | 预测贴合 + 相对分歧 | alignment + normalized disagreement |
| regime-no-alignment | 市场状态 + 相对分歧 | context_regime + normalized disagreement |
| all | 全部新特征 | full v2 feature surface |

通俗解释：

```text
baseline:
  router 看最基础的信息。

alignment:
  router 看每个 adapter 的预测是不是离过去太远。

normalized-disagreement:
  router 看 adapter 分歧大不大，
  而且这个“大”是相对当前波动来说的。

alignment-normalized:
  同时看“预测贴不贴过去”和“adapter 分歧相对大不大”。
```

专业解释：

```text
The ablation separates absolute context features from relative prediction-shape
features. This tests whether routing depends more on market regime scalars or
on how each adapter's forecast relates to the current context.
```

项目对应：

```text
best default-gated preset:
  alignment-normalized

best diagnostic preset:
  alignment-normalized
```

## 4. Ablation Results

Routed cuts only, MAE:

| Preset | Validation MAE | Delta vs fixed recent2000 |
|---|---:|---:|
| baseline | 0.0921934286 | -0.0001701487 |
| context-regime | 0.0919376472 | 0.0000856326 |
| normalized-disagreement | 0.0924055351 | -0.0003822553 |
| alignment | 0.0918978930 | 0.0001253869 |
| regime-alignment | 0.0920801016 | -0.0000568217 |
| alignment-normalized | 0.0917558798 | 0.0002674001 |
| regime-no-alignment | 0.0921409215 | -0.0001176417 |
| all | 0.0917723992 | 0.0002508807 |

通俗解释：

```text
最好的不是“全部特征都上”。

最好的组合是：
alignment-normalized

也就是：
  预测是否贴合过去
  adapter 分歧相对当前波动是否异常

这说明：
router 真正需要的不是更多杂乱信息，
而是更贴近“现在该相信哪个预测形状”的信息。
```

专业解释：

```text
The best feature surface is not the largest feature surface. The best default
validation-gated MAE result comes from prediction-context alignment plus
normalized prediction disagreement.
```

项目对应：

```text
baseline delta:
  -0.0001701487

all feature delta:
  +0.0002508807

alignment-normalized delta:
  +0.0002674001
```

## 5. Why `alignment-normalized` Won

| Observation | Meaning |
|---|---|
| `alignment` alone is positive | forecast/context shape matters |
| `normalized-disagreement` alone is negative | disagreement scale alone is noisy |
| `alignment-normalized` is best | disagreement helps after forecasts are context-grounded |
| `context-regime` helps alone but hurts some combos | raw regime scalars can add noise |

通俗解释：

```text
只看 adapter 分歧不够。

为什么？

因为两个 adapter 分歧很大，
不一定说明谁对谁错。

但如果你先看：
这个预测是不是贴合过去？

再看：
adapter 分歧相对当前波动是否异常？

router 就更容易判断：
现在该信哪一种 adapter。
```

专业解释：

```text
Normalized disagreement is useful as an interaction feature, not as a standalone
feature group. Its signal becomes useful when paired with prediction-context
alignment.
```

项目对应：

```text
normalized-disagreement alone:
  negative

alignment alone:
  positive

alignment-normalized:
  best
```

## 6. Robustness Checks

`alignment-normalized`, routed cuts only:

| Check | Metric | Delta vs fixed recent2000 |
|---|---:|---:|
| MAE validation-gated | 0.0917558798 | 0.0002674001 |
| SMAPE validation-gated | 0.1846992897 | 0.0001627004 |
| MAE series-guarded | 0.0920084609 | 0.0000148190 |
| MAE series-risk | 0.0920084609 | 0.0000148190 |

通俗解释：

```text
这次比上一轮更强。

因为它不只是 MAE 赢：
SMAPE 也赢。
series guard 也略微赢。

但注意：
series guard 只赢一点点。

所以它不是“可以发布”，
而是“方向明显对了”。
```

专业解释：

```text
The best ablation passes the default MAE gate, the SMAPE gate, and the
series-aware MAE guard, but the series-aware margin remains too small for
promotion.
```

项目对应：

```text
positive routed series under validation-gated:
  4

negative routed series under validation-gated:
  6

positive routed series under series-guarded:
  6

negative routed series under series-guarded:
  4
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不是东西越多越好 | larger feature surface can add noise | all < alignment-normalized |
| 要知道哪个信号真有用 | ablation finds causal-ish contribution | preset comparison |
| adapter 选择也是学习问题 | router is its own model | no-leak selector |
| LoRA 成功不只看 adapter loss | downstream selection matters | prediction router |

通俗解释：

```text
现在我们的项目已经不是：
“训练一个 LoRA adapter 看看准不准”。

已经进入下一层：
“多个 LoRA adapter 各有偏向，
我们要训练一个选择器，
让它在不同市场状态下选对 adapter。”

这就是为什么 ablation 很重要。
它告诉我们：
router 应该看什么。
```

专业解释：

```text
LoRA adapter specialization creates a portfolio of biased forecasters. A
no-leak router needs a compact, high-signal runtime feature surface to exploit
that portfolio without current-window leakage.
```

项目对应：

```text
current best adapter-selection feature surface:
  alignment-normalized

current release status:
  blocked

next experiment:
  tune series-risk policy around alignment-normalized
```

## 8. Current Verdict

Fact: `alignment-normalized` is the best feature preset in this ablation.

Fact: it improves MAE, SMAPE, and series-aware MAE over fixed `recent2000`.

Fact: series-aware lift is still very small.

Inference: the router feature direction is now validated, but promotion still
requires broader and more stable per-series gains.

Recommendation: keep `alignment-normalized` as the current router feature
surface and tune the risk policy around it before doing more LoRA adapter
training.
