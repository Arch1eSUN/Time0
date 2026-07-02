# 061 - Calibrated Fallback Probability

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-logistic-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再只找相似案例 | parametric classifier | logistic model |
| 让模型输出风险概率 | calibrated probability | fallback-better probability |
| 概率高才退回 fallback | probability threshold | `probability_threshold` |
| 仍然必须过 strict gate | strict model selection | no fold regressions |

通俗解释：

```text
上一轮 KNN-regret 是：

  找过去最像的窗口，
  看它们平均有没有后悔。

这一轮换成 logistic model：

  它不只是找邻居。
  它学习一条判断边界。
  输出一个概率：

    当前这个 adapter override 有多大概率会比 fallback 差？

如果概率够高，
就退回 fallback。
```

专业解释：

```text
This run tests a logistic fallback-veto classifier. The model estimates
P(fallback_better | no-leak runtime features, selected adapter). Candidate
thresholds are selected only through chronological validation under the strict
gate.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_logistic_veto.py

reports:
  reports/router-logistic-veto-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-logistic-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Calibration?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型不只说是/否 | probability output | `P(fallback_better)` |
| 它说自己有多确定 | calibrated confidence | risk score |
| 70% 应该接近真的 70% | probability calibration | Brier score |
| 方便做阈值控制 | threshold policy | veto threshold |

通俗解释：

```text
普通规则像这样：

  退回 fallback。
  不退回 fallback。

概率模型像这样：

  我认为 fallback 更好的概率是 72%。

这更有用。

因为我们可以设置：

  只有概率超过 80%，才退回。

金融预测里这很重要。
因为很多时候不是非黑即白，
而是风险有多大。
```

专业解释：

```text
Calibration means predicted probabilities should correspond to observed event
frequencies. A calibrated 0.70 risk score should be correct roughly 70% of the
time over comparable samples. This run uses logistic probabilities and records
training Brier score as a simple calibration diagnostic.
```

项目对应：

```text
label:
  1 = fallback was better
  0 = selected adapter was better

prediction:
  probability that fallback is better

decision:
  probability >= threshold -> veto to recent2000
```

## 3. Why Logistic Regression?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 比 KNN 更像真正学边界 | parametric decision boundary | logistic weights |
| 不需要外部依赖 | numpy-only model | no sklearn |
| 能输出概率 | probabilistic classifier | sigmoid |
| 适合小样本实验 | simple baseline | 442 discovery examples |

通俗解释：

```text
logistic regression 可以理解成：

  它给每个信号一个权重。

比如：

  预测趋势偏离很大，风险加分。
  某个 adapter 被选中，风险加分或减分。
  历史波动形态不同，风险变化。

最后把这些分数合起来，
变成 0 到 1 之间的概率。
```

专业解释：

```text
Logistic regression learns a linear log-odds boundary and maps it through a
sigmoid to produce probabilities. It is a useful baseline before more complex
supervised routers because it is transparent and cheap to reproduce.
```

项目对应：

```text
features:
  no-leak runtime features
  selected adapter one-hot

model:
  sigmoid(X @ weights + bias)

regularization:
  L2 values: 0.0, 0.001, 0.01, 0.1
```

## 4. Why Strict Gate Still Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 概率模型也会过拟合 | probabilistic overfit | validation folds |
| 总体变好还不够 | aggregate is insufficient | combined validation |
| 每一折不能倒退 | fold-level robustness | strict positive |
| 不通过就不看 final | holdout protection | final not evaluated |

通俗解释：

```text
概率模型听起来更高级，
但它一样会骗我们。

如果它只在某一段 validation 表现好，
另外几段表现差，
那它还是不稳定。

所以 strict gate 不因为模型更高级就放松。

规则还是：

  每个 validation fold 都不能倒退。
```

专业解释：

```text
A probabilistic classifier does not remove the need for chronological
validation. Strict fold-level validation remains the promotion surface.
```

项目对应：

```text
selection_gate:
  strict

required:
  fold_metric_regressions == 0
  fold_negative_regressions == 0
  fold_no_exposure <= max_fold_no_exposure
```

## 5. What Happened

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| no-series 有总体正信号 | aggregate-positive candidates | 6 positives |
| series-aware 也有一点信号 | aggregate-positive candidates | 1 positive |
| 但严格候选为 0 | no strict candidates | strict count 0 |
| 所以不跑 final | fail closed | final false |

通俗解释：

```text
结果很清楚：

  logistic model 比完全手写规则更像一个真正的 router。
  它能找到 validation 总体正的候选。

但是：

  每个好看的候选，
  都至少有一个 validation fold 倒退。

所以 strict gate 拒绝它。
```

专业解释：

```text
The logistic model improves the candidate interface but not the promotion
outcome. It produces loose validation-positive configs, but no config satisfies
strict fold-level non-regression.
```

项目对应：

```text
no-series:
  validation_robust_pass_count: 5
  validation_positive_count: 6
  validation_strict_positive_count: 0
  verdict: strict_gate_no_candidate

series-aware:
  validation_robust_pass_count: 1
  validation_positive_count: 1
  validation_strict_positive_count: 0
  verdict: strict_gate_no_candidate
```

## 6. Reading The Best Loose Candidates

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最好看的候选总体变好 | positive combined metric | `+0.0003127051` |
| downside 没增加 | downside neutral | delta 0 |
| 但有 fold 倒退 | fold metric regression | count 2 |
| 所以不能过 gate | strict reject | no final |

通俗解释：

```text
no-series 里最好看的候选是：

  L2 = 0.1
  threshold = 0.55

它总体 validation 是正的。
但它有 2 个 fold 的 metric regression。

这就是 strict gate 要拦的东西：

  总体好看，
  但分段不稳定。
```

专业解释：

```text
The top no-series candidate has positive combined metric delta and no combined
downside increase, but two fold-level metric regressions. It is therefore a
false positive under the older loose gate and correctly rejected by strict
selection.
```

项目对应：

```text
top no-series loose candidate:
  l2: 0.1
  probability_threshold: 0.55
  combined_metric_delta: +0.0003127051
  combined_negative_series_delta: 0
  fold_metric_regressions: 2
```

## 7. What We Learned

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型形式更好，但数据边界还不稳 | model class improved, transfer still weak | logistic fail |
| strict gate 继续有效 | gate catches false positives | no final |
| 只换 classifier 不够 | feature/label bottleneck | same no-leak surface |
| 下一步要改训练信号 | better supervision | richer labels |

通俗解释：

```text
这轮说明：

  概率模型是更正确的方向。

但它也说明：

  只把 KNN 换成 logistic 不够。

如果输入特征和标签还是不能稳定区分 regime，
模型再换一种形式，
也过不了 strict gate。
```

专业解释：

```text
The bottleneck appears to be supervision quality or feature separability rather
than classifier mechanics alone. The logistic model exposes a better decision
interface but does not produce fold-stable candidates.
```

项目对应：

```text
status:
  candidate interface improved
  strict promotion still blocked

blocked by:
  fold-level metric regressions
```

## 8. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不放松 strict gate | keep promotion discipline | strict gate |
| 改标签或特征 | improve supervision | richer no-leak rows |
| 预测收益大小而不只是好坏 | regression target | expected regret |
| downside 加进目标 | downside-aware training | per-series risk |

通俗解释：

```text
下一轮不应该做：

  threshold 再调细一点。

更应该做：

  让模型学的不只是“fallback 是否更好”，
  而是“fallback 大概会好多少”。

也就是从分类变成：

  预期 regret 大小。

这样 router 才能知道：

  哪些 override 只是小风险，
  哪些 override 是大风险。
```

专业解释：

```text
The next experiment should keep strict validation and move from binary
fallback-better classification to expected-regret regression or downside-aware
utility modeling.
```

项目对应：

```text
candidate next script:
  validate_multifold_expected_regret_veto.py

must keep:
  no-leak features
  strict gate
  final holdout untouched unless strict candidate exists
```
