# 054 - No-Leak Feature Veto

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-feature-veto-frozen-validation.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再硬写两个 series 名字 | avoid target-series hard-code | `include_series=false` |
| 从过去窗口里找一个能提前看到的特征 | no-leak runtime feature search | `context.past_trend` |
| 用这个特征决定什么时候退回 fallback | feature-based fallback veto | single-threshold veto |
| 冻结后去未来窗口考试 | frozen validation | `cut>3500` |

通俗解释：

```text
上一轮的问题是：

  我们知道 BAMLH0A0HYM2 和 DEXJPUS 有问题，
  但这是看完答案之后才知道的。

这轮换一种方式：

  不直接写 series 名字。
  不说“这两个 series 永远 fallback”。

我们让脚本去找：

  有没有一个预测前就能看到的特征，
  能帮助 router 判断：
    这次 override 可能不可靠，
    最好退回 fallback。
```

专业解释：

```text
This run searches for a single numeric no-leak runtime feature threshold on the
discovery split. The threshold is selected only from cuts <= 3500, then frozen
and applied to cuts > 3500.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_feature_veto_rule.py

report:
  reports/router-feature-veto-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A No-Leak Feature?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 预测前就已经知道的信息 | available-at-decision-time feature | `runtime_features` |
| 不能用未来真实答案 | no label leakage | no `actual`, no `family_errors` |
| 可以用历史上下文 | context-derived feature | `past_trend` |
| 可以用模型自己的预测形状 | prediction-derived feature | prediction summaries |

通俗解释：

```text
no-leak feature 就是：

  在模型做预测那一刻，
  它已经能看到的信息。

比如：

  过去一段时间的均值
  过去一段时间的波动
  过去一段时间的趋势
  不同 adapter 预测之间的分歧

不能用：

  未来真实值
  未来误差
  事后哪个 adapter 最准

因为这些在真实上线时还不知道。
```

专业解释：

```text
A no-leak feature is available at routing time. It may come from context
statistics or candidate forecast summaries, but it must not contain future
actuals, realized errors, or post-hoc labels.
```

项目对应：

```text
allowed:
  row.runtime_features.context
  row.runtime_features.context_regime
  row.runtime_features.prediction_disagreement
  row.runtime_features.prediction_context_alignment

not allowed for rule input:
  row.label.actual
  row.label.family_errors
  row.label.best_family_by_mae
```

## 3. What Is A Feature Veto?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| router 想 override 时，再加一道刹车 | fallback veto | selected family -> fallback |
| 特征命中时，不相信当前 override | threshold gate | `past_trend <= threshold` |
| 没命中时，保留原选择 | sparse intervention | only changed windows count |
| 它不是重新训练 LoRA | policy-layer intervention | no adapter weights changed |

通俗解释：

```text
可以把 router 想象成一个选择器：

  这次用 zero-shot？
  用 full adapter？
  用 recent1500？
  用 recent2000？
  用 recent3000？

feature veto 是一个刹车：

  如果 router 想选非 fallback adapter，
  但某个风险特征很危险，
  那就强制退回 fallback。

这一轮的 fallback 是：

  recent2000
```

专业解释：

```text
The feature veto is a policy-layer rule. It does not alter model weights. It
intercepts non-fallback selections and replaces them with the fallback family
when a frozen runtime feature threshold is satisfied.
```

项目对应：

```text
frozen rule:
  context.past_trend <= -0.3866836197

action:
  selected_family = recent2000
```

## 4. What Did The Rule Find?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最好的单特征是过去趋势很负 | strongest discovery feature | `context.past_trend` |
| 趋势小于阈值时更保守 | negative-trend fallback gate | `<= -0.3866836197` |
| 它不是 series 名字 | non-series feature | `include_series=false` |
| 它在未来真的触发了 | future exposure exists | 84 changed windows |

通俗解释：

```text
脚本找到的规则是：

  如果 past_trend <= -0.3866836197，
  而且 router 想 override，
  那就退回 recent2000。

past_trend 可以理解成：

  最近上下文窗口里，
  这条时间序列从开头到结尾的变化方向。

很负，说明过去窗口在明显往下走。
在这种环境里，一些 override 选择更容易不稳。
```

专业解释：

```text
The best discovery rule was a context-derived threshold. It uses the recent
context trend, not target labels or series identity. That makes it a candidate
for causal routing research rather than a post-hoc target-series exception.
```

项目对应：

```text
best_rule:
  feature_name: context.past_trend
  direction: <=
  threshold: -0.3866836197
  include_series: false
```

## 5. Discovery Result vs Future Result

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 过去发现区间明显改善 | in-discovery improvement | metric delta +0.0001999397 |
| 未来区间也有小幅改善 | out-of-sample aggregate gain | metric delta +0.0000128143 |
| 这次未来真的触发了 | non-zero future exposure | 84 changed windows |
| 但风险分布变差 | downside regression | negative series 1 -> 2 |

通俗解释：

```text
这轮比上一轮强的地方：

  上一轮 frozen target rule 在未来 0 次触发。
  这一轮 feature rule 在未来触发了 84 次。

所以它真的被未来数据考到了。

结果：

  总 MAE 小幅变好。

但同时：

  negative series 从 1 个变成 2 个。

这说明它有信号，
但还不够安全。
```

专业解释：

```text
The frozen feature rule passes aggregate future exposure and aggregate metric
direction, but fails the per-series downside gate. The result is not promotable
even though the aggregate metric improves.
```

项目对应：

| Split | Changed windows | Harmful vetoed | Beneficial blocked | Metric delta | Negative series |
|---|---:|---:|---:|---:|---:|
| discovery | 67 | 42 | 25 | +0.0001999397 | 3 -> 2 |
| future | 84 | 36 | 48 | +0.0000128143 | 1 -> 2 |

## 6. Why Aggregate Improvement Is Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 平均分高一点不代表能上线 | aggregate metric insufficient | release gate still blocked |
| 金融模型怕局部爆雷 | downside concentration matters | negative series gate |
| 多挡掉好 override 也可能平均仍小赢 | magnitude beats count | 36 harmful vs 48 beneficial |
| 但多一个亏损 series 不可接受 | per-series regression | 1 -> 2 negative series |

通俗解释：

```text
你可以把它想成：

  一次考试平均分涨了 0.1 分，
  但多了一门课不及格。

这不能叫真正成功。

金融方向尤其不能只看平均值。

因为真实使用时，
一个局部 series 的风险集中，
可能比平均指标小幅改善更重要。
```

专业解释：

```text
The finance adapter/router release gate is multi-objective. Aggregate MAE lift
is necessary but not sufficient. A candidate that increases negative routed
series remains blocked because it worsens downside distribution.
```

项目对应：

```text
future aggregate:
  rule_improves_split

overall verdict:
  aggregate_positive_downside_regressed
```

## 7. How This Connects To LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 给我们多个专精候选模型 | adapter family | full/recent adapters |
| router 学会选哪个候选模型 | selection policy | prediction router |
| feature veto 是 router 的安全层 | risk gate | fallback intervention |
| 当前不是训练更多，而是选择更准 | policy improvement > rank escalation | no weight update |

通俗解释：

```text
这轮没有重新训练 TimesFM LoRA。

原因是：

  当前问题不一定是 adapter 不够强。
  更像是 router 不知道什么时候该相信 adapter。

所以我们先训练/验证选择逻辑。

如果选择逻辑已经能用过去特征提前识别风险，
再考虑把它升级成更正式的 router。
```

专业解释：

```text
LoRA adaptation created candidate forecasters. The next bottleneck is the
policy seam that routes between those candidates. A no-leak feature veto is a
minimal policy experiment that tests whether routing risk can be detected from
decision-time information.
```

项目对应：

```text
adapter layer:
  zero-shot, full, recent1500, recent2000, recent3000

policy layer:
  no-leak router + feature veto

current result:
  aggregate signal exists
  downside gate still fails
```

## 8. The Important Lesson

Fact:

```text
The frozen no-series feature rule changed 84 future windows and improved future
aggregate MAE by +0.0000128143.
```

Fact:

```text
The same rule increased future negative routed series from 1 to 2.
```

Inference:

```text
We found a real no-leak signal, but not a release-ready policy.
```

Recommendation:

```text
The next useful experiment should make feature veto selection downside-aware.
Do not promote a rule that improves aggregate MAE while increasing negative
series.
```

