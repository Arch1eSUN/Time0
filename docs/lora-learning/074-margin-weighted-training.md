# 074 - Margin-Weighted Training

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-margin-weighting-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 输很多的样本更重要 | margin-weighted loss | `abs(regret_vs_fallback)` |
| 仍然不偷看未来 | no-leak discovery weighting | discovery examples only |
| 保留上一轮时间分桶 | temporal bin balance | `time-bin` |
| 最终仍要过曝光门 | final exposure gate | `min_final_changed_windows=20` |

通俗解释：

```text
上一轮的问题是：

  router 有时只改 1 个窗口，
  甚至看起来赢了，
  但证据太少。

这轮我们换训练目标的一部分：

  如果历史上 selected 比 fallback 差很多，
  这个样本训练时权重大一点。

  如果两者几乎打平，
  这个样本训练时权重小一点。

这叫 margin-weighted training。
```

专业解释：

```text
This run adds margin-based sample weights to the logistic fallback-veto loss.
The margin is `abs(regret_vs_fallback)`, computed only on the training split.
The tested mode combines chronological time-bin label balancing with bounded
regret-magnitude weights.
```

项目对应：

```bash
--training-weighting time-bin-margin-balanced
```

## 2. What Is A Margin?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 两个选择差多少 | decision margin | error gap |
| selected 错得越多，margin 越大 | regret magnitude | `abs(regret_vs_fallback)` |
| fallback 明显更好，是强正样本 | high-confidence positive | fallback-better label |
| selected 明显更好，是强负样本 | high-confidence negative | selected-better label |

通俗解释：

```text
假设某个窗口：

  selected adapter 的误差 = 0.020
  fallback adapter 的误差 = 0.005

那 selected 比 fallback 差很多。

这个样本应该更重要，因为它在告诉 router：

  以后看到这种情况，
  不要用 selected，
  要退回 fallback。
```

专业解释：

```text
`regret_vs_fallback = selected_error - fallback_error`.

If it is positive, fallback was better.
If it is negative or zero, selected was better or tied.

The margin is the absolute value of that regret. It measures how consequential
the historical routing decision was.
```

## 3. Why This Is Still No-Leak

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只看训练区间的输赢幅度 | train-split-only labels | discovery examples |
| 不看 validation 的结果 | no validation leakage | validation folds untouched |
| 不看 final 的结果 | no final leakage | final holdout untouched |
| 只是改变 loss 权重 | sample weighting | logistic loss |

通俗解释：

```text
我们没有用未来结果训练。

训练时只知道 discovery 区间里：

  哪些窗口 fallback 更好，
  哪些窗口 selected 更好，
  差距有多大。

validation 和 final 还是留到后面考试。
```

专业解释：

```text
The margin weights are recomputed from the examples passed into the training
split. During validation selection, they come from discovery examples. During
final evaluation, they come from the final-train examples. The final holdout
labels are never used to train the logistic weights.
```

## 4. How The Weight Is Built

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先做时间分桶平衡 | time-bin label balance | `time_bin_label_balanced_sample_weights` |
| 再乘上输赢幅度权重 | regret magnitude weight | `margin_sample_weights` |
| 防止极端样本爆炸 | bounded weights | `0.25` to `4.0` |
| 最后均值归一 | normalized sample weights | mean weight = 1 |

通俗解释：

```text
不是让最大的一两个样本完全控制训练。

我们给 margin 权重设了上下限：

  最小 0.25
  最大 4.0

意思是：

  大错样本最多重要 4 倍，
  小差距样本至少保留 0.25 倍。
```

专业解释：

```text
The margin weight is `abs(regret_vs_fallback) / median_nonzero_margin`, clipped
to `[0.25, 4.0]`, then normalized to mean 1. The final sample weight is the
product of class/time-bin balance and margin weight.
```

## 5. Discovery Margin Shape

| Field | Value |
|---|---:|
| examples | 442 |
| fallback better | 210 |
| selected better | 232 |
| mean abs regret | 0.0052084259 |
| median abs regret | 0.0016010391 |
| p90 abs regret | 0.0142864516 |
| max abs regret | 0.0733746976 |

通俗解释：

```text
这个分布说明：

  大部分窗口差距很小。
  少数窗口差距很大。

margin weighting 会让这些大差距窗口更影响训练。
```

专业解释：

```text
The discovery regret distribution is heavy-tailed. This gives margin weighting
real leverage, but it also risks making the policy too conservative when large
training errors do not transfer to the final regime.
```

## 6. What Happened

| Surface | Gate | Robust-pass | Strict-positive | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---|
| no-series | strict | 2 | 0 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 2 | 0 | 0 | 0.0 | not_validated_no_future_exposure |
| no-series | robust worst-fold | 2 | 0 | 0 | 0.0 | not_validated_no_future_exposure |
| include-series | strict | 0 | 0 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | 0 | 0 | 0 | 0.0 | not_validated_no_future_exposure |

通俗解释：

```text
结果不是成功。

margin weighting 让模型更保守：

  no-series robust-pass 从上一轮 4 个降到 2 个。
  include-series 直接没有 robust-pass。

但更保守不等于更好。

最终 final holdout 里：

  selected candidate 出手 0 次。

它没有真正被未来测试到。
```

专业解释：

```text
Margin weighting suppresses validation candidates but does not produce
deployable final exposure. The no-series robust candidate remains
validation-positive, but after retraining on the final-train split it has zero
intervention count on final holdout.
```

## 7. Why Zero Final Exposure Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没出手就没被测试 | no policy exposure | `changed_windows=0` |
| final delta 0 不代表安全 | no intervention, no evidence | `no_rule_exposure` |
| 不能说它好 | not validated | `not_validated_no_future_exposure` |
| 也不能说它坏 | diagnostic failure | no final action |

通俗解释：

```text
如果 router 在 final 里面一次都没改变选择，
那 final 分数不会变。

这不是成功。

这只是说明：

  它太保守了，
  没有形成能在未来出手的规则。
```

专业解释：

```text
Zero final exposure means the final holdout cannot estimate the policy's
effect. The correct verdict is not "safe"; it is "not validated".
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 微调不是只要减少错误 | objective shaping has tradeoffs | margin weighting |
| 保守策略可能没有收益 | abstention collapse | zero final exposure |
| adapter 需要使用策略 | adapter-routing policy | logistic veto |
| 使用策略也要能出手 | intervention coverage | exposure gate |

通俗解释：

```text
LoRA adapter 训练出来之后，
我们还要训练一个策略：

  什么时候用它？
  什么时候退回 fallback？

margin weighting 让策略更怕大错。

但它怕到 final 里不出手，
就没有实际价值。
```

专业解释：

```text
This is an abstention-collapse failure. The policy reduces risky validation
actions but does not preserve enough out-of-sample intervention coverage to be
useful.
```

## 9. What We Learned

Fact: `time-bin-margin-balanced` is no-leak and changes the training objective.

Fact: The discovery margin distribution is heavy-tailed enough for the mode to
have real leverage.

Fact: The mode reduces candidate count but collapses final exposure to 0.

Inference: Scalar sample weighting is not enough to solve the current router
transfer problem.

Recommendation: Stop this training lever. The next useful step should separate
two decisions:

```text
1. Is fallback predicted to be better?
2. Is confidence/exposure high enough to act?
```

That means a deeper router interface, not another single scalar loss weight.
