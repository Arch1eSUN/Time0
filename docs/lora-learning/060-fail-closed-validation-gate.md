# 060 - Fail-Closed Validation Gate

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-supervised-strict-gate.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不够稳就不准进入 final | fail-closed selection gate | `--selection-gate strict` |
| 不再只看 validation 总分 | fold-level validation | per-cut folds |
| 每一折都不能倒退 | zero fold regressions | `fold_metric_regressions == 0` |
| 没有合格候选就不选模型 | no candidate, no promotion | `selected_config=null` |

通俗解释：

```text
上一轮 supervised router 有一个问题：

  validation 总体看起来不错，
  但 final holdout 失败了。

这说明：

  旧 gate 太宽松。

所以这一轮我们加了更严格的规则：

  如果一个候选在任意 validation fold 上倒退，
  就不能进入 final holdout。

如果没有候选满足这个条件：

  不选模型。
  不跑 final promotion。
  直接 fail closed。
```

专业解释：

```text
This run adds a fail-closed strict validation gate to the supervised KNN-regret
router. Candidate selection now can require positive combined validation, no
downside regression, no fold-level metric regression, and no exposure failure
before any final holdout policy is selected.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_supervised_veto.py

new flag:
  --selection-gate strict

strict reports:
  reports/router-supervised-veto-strict-gate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-supervised-veto-strict-gate-include-series-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Does Fail-Closed Mean?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不确定时默认拒绝 | fail-closed behavior | no selected config |
| 证据不够就不发布 | conservative promotion gate | `strict_gate_no_candidate` |
| 不让 final 被反复试错污染 | holdout protection | `final_holdout_evaluated=false` |
| 宁可少发布，不乱发布 | safety over false positive | finance gate |

通俗解释：

```text
fail-open 是：

  没看清，也先放行。

fail-closed 是：

  没看清，就拒绝。

金融预测里我们要 fail-closed。

因为错放一个不稳定模型，
比少放一个模型更危险。
```

专业解释：

```text
Fail-closed means uncertainty defaults to rejection. In model selection, this
prevents weak validation evidence from being converted into a deployed or
promoted policy.
```

项目对应：

```text
if validation_strict_positive_count == 0:
  selected_config = null
  final_holdout_evaluated = false
  verdict = strict_gate_no_candidate
```

## 3. Why Combined Validation Was Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总分好不代表每场都好 | aggregate masking | combined validation |
| 某一折倒退可能被另一折补回来 | fold regression hidden by average | `fold_metric_regressions` |
| 金融 regime 会变 | temporal instability | chronological cuts |
| 每折都稳才更可信 | fold robustness | strict gate |

通俗解释：

```text
假设有三场模拟考：

  第一场 +10 分
  第二场 -3 分
  第三场 -2 分

总分还是 +5。

旧 gate 会说：

  总体是正的，可以考虑。

strict gate 会说：

  不行。
  你有两场倒退。

这更符合金融预测。
因为市场不会一直像你表现最好的那一折。
```

专业解释：

```text
Combined validation can hide fold-level regressions. In chronological
forecasting, each fold represents a different temporal slice, so fold-level
failure is evidence of regime instability.
```

项目对应：

```text
old loose positive:
  validation_positive_count: 6

new strict positive:
  validation_strict_positive_count: 0
```

## 4. Strict Gate Criteria

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总体要变好 | positive aggregate metric | `combined_metric_delta > 0` |
| 负收益 series 不能增加 | downside non-regression | `combined_negative_series_delta <= 0` |
| 每折 downside 不能变坏 | fold downside guard | `fold_negative_regressions == 0` |
| 每折 metric 不能变坏 | fold metric guard | `fold_metric_regressions == 0` |
| 每折必须真触发 | exposure guard | `fold_no_exposure <= max` |

通俗解释：

```text
strict gate 要求很直白：

  1. 总体要变好。
  2. 负收益 series 不能更多。
  3. 每个 validation fold 的 downside 不能坏。
  4. 每个 validation fold 的 MAE 不能坏。
  5. 规则必须真的触发，不能靠没考到混过去。
```

专业解释：

```text
The strict gate turns validation from an aggregate objective into a
multi-condition promotion contract. A candidate must be positive, downside-safe,
fold-stable, and exposed before it can be selected.
```

项目对应：

```text
combined_metric_delta > 0
combined_negative_series_delta <= 0
fold_negative_regressions == 0
fold_metric_regressions == 0
fold_no_exposure <= max_fold_no_exposure
```

## 5. What Happened

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| no-series 没有严格候选 | no strict candidate | count 0 |
| series-aware 也没有严格候选 | no strict candidate | count 0 |
| 没选任何模型 | fail closed | `selected_config=null` |
| 没跑 final promotion | holdout preserved | `final_holdout_evaluated=false` |

通俗解释：

```text
这轮结果看起来像“什么都没选”。

但这正是我们想要的。

因为上一轮已经证明：

  宽松 gate 会让不稳定模型进入 final。

这轮 strict gate 发现：

  没有候选真正每折都稳。

所以它拒绝选择。
```

专业解释：

```text
Both no-series and series-aware supervised candidate sets have zero strict
validation-positive configs. The script therefore returns a fail-closed report
instead of selecting a policy for final evaluation.
```

项目对应：

```text
no-series strict:
  validation_robust_pass_count: 5
  validation_positive_count: 6
  validation_strict_positive_count: 0
  selected_config: null
  final_holdout_evaluated: false

series-aware strict:
  validation_robust_pass_count: 0
  validation_positive_count: 0
  validation_strict_positive_count: 0
  selected_config: null
  final_holdout_evaluated: false
```

## 6. Why This Is Progress

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它修的是验收标准 | evaluation correction | stricter gate |
| 它阻止了假阳性 | false-positive control | no final chasing |
| 它保护 final holdout | holdout hygiene | not evaluated |
| 它告诉下一轮该改模型 | model quality bottleneck | no strict candidate |

通俗解释：

```text
模型研究不是每轮都要数字变好。

有时最重要的进展是：

  我们发现原来的考试太松。
  然后把考试改严。

这能防止我们骗自己。

这轮 strict gate 把上一轮的失败模式提前拦住了。
所以这是项目质量上的进展。
```

专业解释：

```text
This improves the evaluation Interface. It reduces false-positive promotion and
preserves the final holdout as a cleaner acceptance surface. The failure now
points to candidate quality rather than gate ambiguity.
```

项目对应：

```text
previous failure:
  loose validation selected a final-losing policy

new behavior:
  strict validation rejects all current policies before final
```

## 7. What This Teaches About LoRA Work

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 微调不是只看训练 loss | training is not enough | LoRA adapter |
| router 也要严格验证 | policy validation | adapter selection |
| final 不能被反复试 | holdout leakage risk | final hygiene |
| gate 是项目资产 | evaluation contract | release guard |

通俗解释：

```text
LoRA 项目里最容易犯的错是：

  看到某个实验数字好一点，
  就觉得模型变强了。

但真正做垂直模型时，
更重要的是：

  这个提升是不是稳定？
  是不是每个时间段都不坏？
  是不是没有牺牲某些 series？
  是不是没有偷看未来？

所以 gate 本身就是模型项目的一部分。
```

专业解释：

```text
Evaluation gates are part of the model system. For LoRA specialization, adapter
weights, router policy, validation protocol, and release criteria are coupled.
A weak gate can overstate adapter value.
```

项目对应：

```text
model stack:
  TimesFM base
  LoRA adapters
  router policy
  validation gate
  release gate
```

## 8. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不要放松 gate | keep strict gate | promotion criterion |
| 提高候选质量 | improve model class | calibrated router |
| 输出概率而不是硬判断 | calibrated probability | risk score |
| downside 进训练目标 | downside-aware objective | per-series safety |

通俗解释：

```text
下一轮不能做：

  gate 太严了，我们放松一点。

这会回到自欺欺人。

下一轮应该做：

  保持 strict gate。
  换一个更好的 supervised router。

比如让模型输出：

  这个 override 有多少概率会比 fallback 差？

然后只在概率很高、
并且 downside 风险不增加时，
才退回 fallback。
```

专业解释：

```text
The next experiment should keep the strict promotion gate and improve the model
class. A calibrated supervised probability model with explicit downside-aware
selection is more appropriate than further KNN threshold sweeps.
```

项目对应：

```text
next candidate:
  calibrated supervised fallback-veto probability

must keep:
  --selection-gate strict
  chronological validation
  final holdout once
  per-series downside reporting
```
