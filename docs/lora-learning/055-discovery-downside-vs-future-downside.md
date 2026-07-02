# 055 - Discovery Downside vs Future Downside

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-downside-aware-feature-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 上一轮规则平均变好，但风险分布变差 | aggregate-positive downside-regressed policy | `1 -> 2` negative future series |
| 这一轮让规则筛选时也看 discovery downside | downside-aware discovery objective | `selection_objective` |
| 先不加复杂模型，只改筛选目标 | objective-level experiment | same single-feature search |
| 看它能不能选出更稳的规则 | frozen validation | future split after `cut3500` |

通俗解释：

```text
上一轮我们找到一个规则：

  context.past_trend <= -0.3866836197

它有一个好消息：

  未来真的触发了 84 次，
  总体 MAE 小幅变好。

也有一个坏消息：

  未来 negative series 从 1 个变成 2 个。

所以这一轮的问题是：

  如果我们在发现阶段就要求规则不要增加 negative series，
  会不会选出更安全的规则？
```

专业解释：

```text
This run modifies the discovery objective for single-feature fallback veto
selection. Instead of selecting purely by aggregate metric delta, it adds
discovery-side negative-series constraints and a downside-first ranking mode.
The selected rule is then frozen and evaluated on the future split.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_feature_veto_rule.py

new args:
  --selection-objective downside-aware
  --selection-objective downside-first
```

## 2. What Is Discovery Downside?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 在旧时间段里，哪些 series 被规则弄亏 | in-discovery per-series downside | cuts <= 3500 |
| 它用来筛规则 | rule-selection criterion | `discovery_downside` |
| 它不是最终考试 | not final validation | future split separate |
| 它只能说明过去更稳 | in-sample downside evidence | not release proof |

通俗解释：

```text
discovery downside 就是：

  在用来找规则的那段历史里，
  规则有没有让更多 series 变差。

比如原来：

  3 个 negative series

规则后：

  2 个 negative series

这说明它在 discovery 段更稳。

但这还不能证明未来也更稳。
```

专业解释：

```text
Discovery downside is a per-series risk measure computed on the rule-selection
segment. It can constrain candidate selection, but it is still selected using
the discovery labels and must not be treated as out-of-sample evidence.
```

项目对应：

```text
discovery split:
  original negative series: 3
  feature-veto negative series: 2
  negative_series_delta: -1
```

## 3. What Is Future Downside?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 冻结规则后，在未来时间段里哪些 series 变亏 | out-of-sample per-series downside | cuts > 3500 |
| 它才是能不能发布的重点 | promotion gate evidence | future validation |
| 平均变好但 future downside 变差，仍然不能发布 | aggregate win insufficient | blocked release |
| 金融方向必须看风险分布 | downside distribution matters | negative series gate |

通俗解释：

```text
future downside 才是更重要的考试。

因为真实上线时，
我们不能只问：

  平均误差有没有下降？

还要问：

  有没有让某些市场/资产/宏观序列更危险？

这轮答案是：

  平均误差小幅下降，
  但未来 negative series 从 1 个变成 2 个。

所以不能发布。
```

专业解释：

```text
Future downside measures the frozen rule's per-series degradation on unseen
chronological cuts. A rule that improves aggregate MAE while increasing future
negative series fails the current finance promotion gate.
```

项目对应：

```text
future split:
  original negative series: 1
  feature-veto negative series: 2
  verdict: aggregate_positive_downside_regressed
```

## 4. The Three Objectives

| Objective | 通俗解释 | 专业解释 | 本轮结果 |
|---|---|---|---|
| `aggregate` | 只选平均误差改善最多的规则 | maximize discovery metric delta | selected `past_trend` rule |
| `downside-aware` | 先过滤掉让 discovery negative series 增加的规则 | constrain discovery downside, then maximize metric delta | same rule |
| `downside-first` | 先选 discovery negative series 改善最多的规则 | rank by discovery negative-series delta first | same rule |

通俗解释：

```text
我们尝试了三种选规则方式：

  第一种：
    谁平均分涨最多，选谁。

  第二种：
    先排除会让 discovery 风险变差的规则，
    再选平均分最高的。

  第三种：
    先选 discovery 风险改善最多的，
    再看平均分。

结果三种都选了同一条规则。
```

专业解释：

```text
The aggregate-best rule was already discovery-downside-compliant. It reduced
discovery negative series from 3 to 2, so stricter discovery-side ranking did
not alter the selected frozen policy.
```

项目对应：

```text
selected rule:
  context.past_trend <= -0.3866836197

positive discovery candidates:
  1150

selected candidates after downside filter:
  1150
```

## 5. Why The Result Still Blocks Release

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 过去更稳，不代表未来更稳 | discovery downside does not guarantee future downside | temporal generalization gap |
| 单一特征太粗 | low-capacity threshold policy | one feature, one threshold |
| 它能抓到一类坏 override | aggregate signal exists | future metric delta positive |
| 但不能控制风险落到哪个 series 上 | per-series allocation unresolved | future negative series 1 -> 2 |

通俗解释：

```text
这轮最重要的教训是：

  过去 risk 变好，
  不等于未来 risk 也会变好。

原因很简单：

  一个单特征阈值太粗。

它看到：

  past_trend 很负，应该更保守。

这确实能挡掉一些坏 override。

但它不知道：

  哪个 series 会因此受益，
  哪个 series 会因此被误伤。
```

专业解释：

```text
Single-feature threshold policies can expose no-leak aggregate signal, but they
do not model heterogeneous per-series treatment effects. The selected rule
improves discovery downside and aggregate future MAE, yet transfers downside to
an additional future series.
```

项目对应：

```text
discovery:
  negative series 3 -> 2

future:
  negative series 1 -> 2
```

## 6. How This Connects To LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 不是唯一问题 | adapter weights are not the only bottleneck | no retraining this round |
| 选择哪个 adapter 同样重要 | router policy seam | feature veto |
| 单规则已经到边界 | shallow policy exhausted | same rule selected |
| 下一步需要更深的 router，而不是盲目加 rank | richer policy before rank escalation | multi-feature/fold validation |

通俗解释：

```text
如果我们现在继续加 LoRA rank，
可能是在解决错问题。

当前证据说明：

  adapter 家族里有信号，
  router 也能用 no-leak feature 抓到一点信号，
  但单一规则无法稳定控制 downside。

所以更合理的下一步是：

  做更正式的 router 训练/验证，
  而不是马上训练更大的 LoRA。
```

专业解释：

```text
The bottleneck remains policy selection. The LoRA candidates are useful inputs,
but promotion depends on a router that can optimize aggregate accuracy and
per-series downside jointly under chronological validation.
```

项目对应：

```text
current evidence:
  no-leak aggregate signal: yes
  future downside control: no
  release-ready policy: no
```

## 7. The Important Lesson

Fact:

```text
The downside-aware and downside-first objectives selected the same rule as the
aggregate objective.
```

Fact:

```text
The rule improved discovery negative series from 3 to 2, but worsened future
negative series from 1 to 2.
```

Inference:

```text
Discovery downside constraints are not enough for future downside control when
the policy is only a single-feature threshold.
```

Recommendation:

```text
Stop escalating single-feature veto rules. The next useful experiment should
use multi-fold chronological validation or a multi-feature router objective
that directly selects for aggregate lift plus no future downside regression.
```

