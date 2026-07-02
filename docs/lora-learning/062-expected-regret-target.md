# 062 - Expected Regret Target

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-expected-regret-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 上一轮问“会不会错” | binary classification | logistic fallback probability |
| 这一轮问“会错多少” | regression target | expected regret |
| 错得多才退回 fallback | thresholded predicted regret | `regret_threshold` |
| 仍然不能偷看未来 | chronological validation | strict gate |

通俗解释：

```text
上一轮 logistic router 像是在问：

  这个 adapter 会不会比 fallback 差？

答案只有两类：

  会。
  不会。

这一轮 expected-regret router 换了问题：

  如果这个 adapter 比 fallback 差，
  大概会差多少？

这更接近金融预测。
因为金融里不是只关心“对/错”，
而是关心“错的时候亏多少”。
```

专业解释：

```text
This run replaces binary fallback-better classification with continuous
regret regression. The target is selected_adapter_error - fallback_error.
The model predicts expected regret and vetoes adapter overrides when predicted
regret crosses a threshold.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_expected_regret_veto.py

reports:
  reports/router-expected-regret-veto-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-expected-regret-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Expected Regret?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 后悔值 | regret | adapter error minus fallback error |
| 正数代表 adapter 更差 | positive regret | fallback should have been used |
| 负数代表 adapter 更好 | negative regret | adapter was useful |
| 预测后悔值 | expected regret | ridge prediction |

通俗解释：

```text
想象你有两个选择：

  A: 用 adapter
  B: 用 fallback recent2000

跑完以后发现：

  adapter 错误 = 0.120
  fallback 错误 = 0.100

那么：

  regret_vs_fallback = 0.120 - 0.100 = +0.020

意思是：

  我刚才用 adapter 后悔了。
  如果用 fallback，会少错 0.020。

如果反过来：

  adapter 错误 = 0.090
  fallback 错误 = 0.100

那么：

  regret_vs_fallback = 0.090 - 0.100 = -0.010

意思是：

  adapter 比 fallback 好。
  不应该退回 fallback。
```

专业解释：

```text
Regret is the opportunity cost of selecting one policy instead of another.
Here the comparator is fixed fallback `recent2000`, and the selected policy is
the current router-selected adapter. A positive regret means the selected
adapter had larger error than fallback.
```

项目对应：

```python
regret_vs_fallback = selected_error - fallback_error
```

## 3. Classification vs Regression

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 分类回答是/否 | classification | fallback better: 0 or 1 |
| 回归回答数值大小 | regression | regret value |
| 分类会丢掉幅度 | label compression | small loss equals big loss |
| 回归保留亏损大小 | magnitude-aware target | expected regret |

通俗解释：

```text
分类像这样：

  fallback 是否更好？
  是。

但它不会告诉你：

  fallback 只是好一点点？
  还是好很多？

这两个情况在分类标签里都是 1。

回归像这样：

  fallback 预计好 0.0003。
  fallback 预计好 0.0200。

这两个数字明显不一样。

金融模型更需要第二种信息。
因为“小错”和“大亏”不是一回事。
```

专业解释：

```text
Binary labels collapse all positive-regret examples into one class.
Continuous regret keeps the magnitude of the loss difference. This gives the
router a richer supervision signal, especially when downside size matters more
than event frequency.
```

项目对应：

```text
previous target:
  1 if regret_vs_fallback > 0 else 0

current target:
  regret_vs_fallback as a real number
```

## 4. What Ridge Regression Means Here

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给每个信号一个权重 | linear regression | feature weights |
| 不让权重乱飞 | L2 regularization | `l2` |
| 用历史窗口拟合 | supervised fit | discovery examples |
| 输出一个预计后悔值 | predicted continuous target | `predicted_regret` |

通俗解释：

```text
ridge regression 可以理解成：

  看很多历史例子。
  学每个信号的影响。

比如：

  预测分歧很大，预计 regret 增加。
  当前 regime 和训练期很像，预计 regret 降低。
  某个 adapter 经常在这种窗口吃亏，预计 regret 增加。

L2 是一个刹车。
它防止模型把某个信号权重拉得过大。
```

专业解释：

```text
Ridge regression minimizes squared prediction error with an L2 penalty on
weights. The penalty reduces variance and is useful for small supervised
router datasets where unstable weights can overfit chronological discovery
windows.
```

项目对应：

```text
l2 values:
  0.0, 0.001, 0.01, 0.1, 1.0

candidate configs:
  5 l2 values * 7 regret thresholds * 3 positive weights = 105
```

## 5. What Positive Weight Means

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 更重视亏损样本 | asymmetric sample weighting | `positive_weight` |
| 正 regret 是坏事 | downside emphasis | fallback better |
| 权重大代表更怕亏 | loss-sensitive objective | 1.0, 2.0, 4.0 |
| 但不能自动解决泛化 | weighting is not validation | strict gate still needed |

通俗解释：

```text
如果正 regret 代表 adapter 比 fallback 差，
那这些样本就是我们最害怕的样本。

positive_weight 的意思是：

  这些坏样本训练时算更重。

比如 weight = 4.0：

  一个 adapter 吃亏样本，
  在训练里像 4 个普通样本一样重要。

这会让模型更敏感地识别风险。
但它不是魔法。
如果未来时间段的规律变了，
weight 再高也可能过拟合。
```

专业解释：

```text
Positive-regret examples receive larger sample weights during ridge fitting.
This biases the regression toward fitting harmful adapter overrides more
carefully. It is a training objective choice, not a validation guarantee.
```

项目对应：

```text
positive_weight values:
  1.0, 2.0, 4.0

positive target:
  regret_vs_fallback > 0
```

## 6. Why We Still Use Strict Gate

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 平均变好还不够 | aggregate lift is insufficient | combined metric |
| 每段时间不能倒退 | fold non-regression | validation folds |
| downside 也不能变差 | risk guard | negative series |
| 不过关就不看最终考卷 | holdout protection | `final_holdout_evaluated=false` |

通俗解释：

```text
一个模型可能这样：

  在 2024 年那段表现很好。
  在 2025 年那段表现很差。

平均下来还是正的。

但金融模型不能只看平均。
因为真实使用时你不知道未来是哪种行情。

所以 strict gate 要求：

  validation 的每一折都不能明显倒退。

只要某些时间折倒退，
就不允许进入 final holdout。
```

专业解释：

```text
Strict selection requires zero fold-level metric regressions, zero fold-level
negative-series regressions, and no missing exposure beyond the configured
limit. It prevents aggregate-positive but temporally unstable candidates from
consuming final holdout evidence.
```

项目对应：

```text
required:
  fold_metric_regressions == 0
  fold_negative_regressions == 0
  fold_no_exposure <= 0
```

## 7. What Happened

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 信号更强了 | more aggregate-positive candidates | 14 no-series positives |
| 加 series 后信号变少 | identity sensitivity | 7 series-aware positives |
| 但 strict 还是 0 | no promotable candidates | strict count 0 |
| final 仍然没动 | fail closed | final false |

通俗解释：

```text
这一轮比 logistic 更有信号。

no-series:
  有 14 个 validation 总体正的候选。

series-aware:
  有 7 个 validation 总体正的候选。

但关键问题没变：

  没有一个候选能做到每个 validation fold 都不倒退。

所以结果还是：

  不能发布。
  不能说这个 router 已经可靠。
  不能用 final holdout 美化结论。
```

专业解释：

```text
Expected-regret regression improves the loose validation frontier but fails
the strict promotion gate. The model class has better signal extraction, but
the learned policy still lacks chronological transfer stability.
```

项目对应：

```text
no-series:
  validation_robust_pass_count: 14
  validation_positive_count: 14
  validation_strict_positive_count: 0
  verdict: strict_gate_no_candidate

series-aware:
  validation_robust_pass_count: 7
  validation_positive_count: 7
  validation_strict_positive_count: 0
  verdict: strict_gate_no_candidate
```

## 8. Reading The Best Loose Candidates

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最好看的平均收益很大 | high aggregate lift | `+0.0014757435` |
| 但 downside 变差 | more negative series | delta 2 |
| 时间折也倒退 | fold regressions | count 2 |
| 所以它是假阳性 | rejected false positive | strict gate |

通俗解释：

```text
no-series 里按平均指标看，
最好看的候选是：

  l2 = 0.01
  regret_threshold = 0.002
  positive_weight = 4.0

它的 combined_metric_delta 是：

  +0.0014757435

这比上一轮 logistic 的松散候选更强。

但它有两个硬伤：

  negative series 增加 2 个。
  validation fold metric regression 有 2 个。

所以这个候选不是突破。
它只是一个更诱人的假阳性。
```

专业解释：

```text
The highest aggregate no-series candidate improves combined metric delta but
increases negative-series count and has fold-level metric regressions. Under a
finance release gate, this is not acceptable evidence.
```

项目对应：

```text
top no-series loose candidate:
  l2: 0.01
  regret_threshold: 0.002
  positive_weight: 4.0
  combined_metric_delta: +0.0014757435
  combined_negative_series_delta: 2
  fold_metric_regressions: 2
  fold_negative_regressions: 1
```

## 9. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 微调不是只训练 adapter | LoRA is one part of the system | adapter plus router |
| 还要决定什么时候用它 | policy selection | fallback-veto |
| 金融里最难是稳定 | distribution shift | fold regressions |
| 训练信号要贴近损失 | loss-aligned supervision | expected regret |

通俗解释：

```text
你可以把 LoRA adapter 想成一把专用刀。

但系统还需要知道：

  什么时候拿这把刀？
  什么时候不要拿？
  什么时候退回通用工具？

router 就是做这个选择的。

如果 router 只知道“好/坏”，它太粗。
如果 router 能估计“会差多少”，它更接近真实风险控制。

这就是 expected regret 的意义。
```

专业解释：

```text
For domain LoRA, adapter quality and adapter selection are separate problems.
Expected-regret routing aligns the selector with the downstream evaluation
loss, which is more appropriate than treating every fallback-better event as
equally important.
```

项目对应：

```text
adapter:
  specialized TimesFM LoRA candidate

router:
  no-leak policy that selects adapter or fallback

current blocker:
  router transfer stability
```

## 10. What We Learned

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 方向更对了 | better target | continuous regret |
| 结果还没过关 | no promotion | strict count 0 |
| 问题从模型形式转向稳定性 | transfer bottleneck | fold regressions |
| 下一步要把风险写进选择目标 | utility-aware selection | downside-aware utility |

通俗解释：

```text
这一轮不是失败到没价值。

它有价值的地方是：

  expected regret 比 logistic 分类更能挖出信号。

但它也告诉我们：

  信号强不等于可发布。
  平均收益不等于金融可靠性。
  时间折不稳定，项目就不能停。
```

专业解释：

```text
The result moves the research frontier from binary supervision to
loss-magnitude supervision. The remaining blocker is not the existence of
signal, but robust model selection under chronological distribution shift.
```

项目对应：

```text
status:
  diagnostic improvement
  no release candidate

blocked by:
  fold-level metric regressions
  negative-series sensitivity
```

## 11. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再只追平均收益 | risk-aware objective | utility score |
| 把 downside 加进选择分数 | downside penalty | negative-series delta |
| 继续保护 final holdout | fail-closed model selection | strict gate |
| 找真正稳定的 adapter policy | robust router | no fold regressions |

通俗解释：

```text
下一轮不应该做：

  放松 strict gate。
  只挑 combined_metric_delta 最大的候选。
  继续调 threshold 直到看起来好。

下一轮应该做：

  用一个风险感知的选择目标。

这个目标至少同时考虑：

  平均 MAE 有没有变好。
  每个 validation fold 有没有倒退。
  negative series 有没有增加。
  changed windows 是否有足够曝光。
```

专业解释：

```text
The next experiment should rank or train candidates with a utility function
that combines aggregate lift, fold robustness, exposure, and downside
penalties. Strict holdout protection should remain unchanged.
```

项目对应：

```text
candidate next script:
  validate_multifold_utility_regret_veto.py

must keep:
  no-leak features
  strict gate
  final holdout untouched unless strict candidate exists
```
