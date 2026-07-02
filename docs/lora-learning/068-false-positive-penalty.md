# 068 - False-Positive Penalty

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-false-positive-penalty-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 错杀 adapter 要更贵 | false-positive penalty | `--false-positive-weight` |
| 学会别乱退回 fallback | abstention pressure | conservative logistic veto |
| 目标还是 fallback 是否更好 | binary fallback-better target | logistic label |
| 用 strict gate 检查能否晋级 | fail-closed validation | strict-positive candidates |

通俗解释：

```text
上一轮我们发现：

  加 alignment 特征不够。
  压缩 alignment 特征也不够。
  强 L2 也不够。

所以这轮不再改“模型看什么”。

这轮改“模型怕什么”：

  让它更怕错杀一个本来有用的 adapter。
```

专业解释：

```text
This run adds cost-sensitive logistic training. Negative examples represent
cases where the selected adapter beats fallback. Increasing
`false_positive_weight` upweights those negative examples so the classifier is
penalized more heavily for harmful vetoes.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_logistic_veto.py

new argument:
  --false-positive-weight
```

## 2. What Is A False Positive?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型喊“该退回”但其实不该 | false positive veto | predicted fallback better but selected better |
| 错杀有用 adapter | harmful veto | metric delta < 0 |
| 比少赚一次更麻烦 | downside control | fold regression |
| 金融里尤其危险 | asymmetric risk | preserve specialization |

通俗解释：

```text
router 做的是这个决定：

  要不要从 selected adapter 退回 fallback？

如果它退回 fallback，
但事后发现 selected adapter 其实更准，
这就是 false positive。

简单说：

  它把好 adapter 错杀了。
```

专业解释：

```text
For a fallback veto classifier, the positive class means fallback has lower
error than the selected adapter. A false positive occurs when the classifier
predicts fallback should be used, but the selected adapter actually has lower
error.
```

项目对应：

```text
label 1:
  fallback_error < selected_error
  veto helps

label 0:
  fallback_error >= selected_error
  veto hurts or does not help
```

## 3. Why Penalize False Positives?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 宁可少退几次，也别乱退 | conservative decision rule | upweight label 0 |
| 错杀会破坏 adapter 专精 | specialization loss | selected adapter suppressed |
| 这是一种成本敏感训练 | cost-sensitive learning | weighted logistic loss |
| 它不是改数据 | same rows, different loss weights | same discovery examples |

通俗解释：

```text
如果一个保安系统太敏感：

  每个人都拦。

它看起来很安全，
但正常人也进不来。

fallback veto 也一样。

如果 router 太爱退回 fallback，
它会错杀很多本来有用的 adapter。

false-positive penalty 就是在训练时告诉它：

  错杀的代价更高。
```

专业解释：

```text
False-positive weighting changes the sample weights in logistic loss. It does
not change labels or leak future data. It changes the optimization objective so
misclassifying harmful-veto examples has larger gradient impact.
```

项目对应：

```python
sample_weight = balanced_weight
if label == 0:
    sample_weight *= false_positive_weight
```

## 4. What Changed In The Code

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 新增一个训练旋钮 | new hyperparameter | `false_positive_weight` |
| 默认不变 | backward compatible default | `1.0` |
| 只影响训练权重 | weighted loss only | `false_positive_sample_weights` |
| 报告记录该值 | reproducibility | report config |

通俗解释：

```text
如果不传参数：

  和以前一样。

如果传：

  --false-positive-weight 8

意思是：

  对“错杀 adapter”这种训练样本，
  惩罚变成 8 倍。
```

专业解释：

```text
The logistic config now includes `false_positive_weight`. Reports include the
weight, and old report configs remain readable because missing values default to
1.0.
```

项目对应：

```text
default smoke candidate count:
  28

penalty grid candidate count:
  200
```

## 5. What Happened

| Surface | Strict-positive | Final changed | Final delta | Verdict |
|---|---:|---:|---:|---|
| no-series | 7 | 6 | -0.0000069200 | not_promotable |
| include-series | 0 | n/a | n/a | strict_gate_no_candidate |

通俗解释：

```text
这是第一次：

  logistic no-series 出现 strict-positive candidates。

这说明 false-positive penalty 不是没用。

但最后还是没成功：

  final 只改了 6 个窗口。
  这 6 个窗口整体是负的。

所以它通过了 validation，
但没有通过 final。
```

专业解释：

```text
False-positive weighting created seven no-series candidates satisfying the
strict validation gate. The selected candidate had zero validation fold metric
regressions, but final holdout metric delta was negative with only six changed
windows.
```

项目对应：

```text
selected config:
  l2: 0.001
  probability_threshold: 0.5
  false_positive_weight: 8.0

validation:
  strict_positive_count: 7

final:
  changed_windows: 6
  metric_delta: -0.0000069200
```

## 6. Why Strict Passed But Final Failed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它改得太少 | tiny exposure | 1/3/11 validation windows |
| 小样本容易看起来稳定 | high variance | sparse validation exposure |
| strict 没坏不等于有足够证据 | non-regression is not sufficiency | exposure gate missing |
| final 也只有 6 个窗口 | weak future evidence | final changed_windows = 6 |

通俗解释：

```text
这个结果像这样：

  模拟考三次。
  第一次只做对 1 道题。
  第二次只做对 3 道题。
  第三次只做对 11 道题。

它确实没有做错。

但样本太少。

所以到了 final，
只改 6 个窗口，
稍微一偏就变负。
```

专业解释：

```text
The strict gate checks non-regression, but it does not currently require a
minimum number of changed windows. A sparse rule can pass strict validation by
having tiny positive deltas on very few windows, then fail future holdout due to
high variance.
```

项目对应：

```text
validation cut3750:
  changed_windows: 1

validation cut4000:
  changed_windows: 3

validation cut4250:
  changed_windows: 11

final:
  changed_windows: 6
```

## 7. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 目标函数真的会改变行为 | objective changes model behavior | strict positives appeared |
| 但验证门也要跟着升级 | validation contract must match risk | exposure gate |
| 不能只看过没过 | pass/fail is insufficient | exposure size matters |
| 小胜样本不能当可发布模型 | sparse policy risk | not_promotable |

通俗解释：

```text
这轮很重要。

因为它说明：

  改 loss/target 是有效方向。

但也说明：

  我们的 strict gate 还不够完整。

以前问题是：

  没有 candidate 能过 strict。

现在问题变成：

  有 candidate 能过 strict，
  但 exposure 太小，
  final 不稳。
```

专业解释：

```text
The experiment changes the failure mode from fold-regression rejection to sparse
strict-positive over-selection. This means the validation contract needs a
minimum-exposure condition before strict positives can be considered promotion
candidates.
```

项目对应：

```text
old blocker:
  validation_strict_positive_count = 0

new blocker:
  validation_strict_positive_count = 7
  final_verdict = rule_hurts_split
  final_changed_windows = 6
```

## 8. Next Round

Recommendation:

```text
Keep false-positive weighting.

Add a minimum exposure gate:

  combined validation changed windows >= N
  each validation fold changed windows >= M

Then rerun:

  logistic false-positive penalty
  no-series and include-series
  strict mode first
```

Success target:

```text
strict_positive > 0
fold_metric_regressions = 0
minimum validation exposure satisfied
final_metric_delta > 0
final exposure not tiny
```
