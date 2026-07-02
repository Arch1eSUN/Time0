# 053 - Frozen Rule Validation

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-target-fallback-frozen-validation.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 上一轮我们事后发现两个 series 的 override 窗口会拖后腿 | post-hoc residual downside diagnosis | `BAMLH0A0HYM2`, `DEXJPUS` |
| 这一轮不直接相信这个发现 | leakage-aware validation | avoid post-hoc promotion |
| 我们把规则冻结在发现它之后 | frozen rule validation | `freeze_after_cut=3500` |
| 再看它在后面的时间段有没有真实触发 | future exposure check | `future_after_freeze_cut` |

通俗解释：

```text
上一轮我们发现：

  如果把两个表现差的 series 强制退回 fallback，
  整体结果会更好。

但这有一个大问题：

  我们是看完答案之后才知道这两个 series 表现差。

所以这一轮要做一个更严格的测试：

  假设我们在 cut3500 之后才把这条规则写下来，
  然后让它去面对 cut3500 之后的未来窗口。

如果它在未来也能触发，并且触发后变好，
那才更像一个可以发布的规则。
```

专业解释：

```text
This run converts a post-hoc target-series counterfactual into a frozen-policy
validation test. The target list is discovered from completed diagnostics, so
only decisions made after the freeze cut can count as no-leak validation
evidence.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_target_fallback_rule.py

report:
  reports/router-target-fallback-frozen-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A Frozen Rule?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 先把规则写死，再去考未来题 | frozen policy | rule fixed before validation labels |
| 不能边看答案边改规则 | no adaptive selection on holdout | no-leak guardrail |
| 未来表现才算证据 | future holdout evidence | `validation_split` |
| 过去表现只能解释问题 | discovery evidence | `discovery_split` |

通俗解释：

```text
规则冻结，就是：

  从某个时间点开始，
  不再根据后面的答案修改规则。

比如这条规则是：

  如果 series 是 BAMLH0A0HYM2 或 DEXJPUS，
  并且 router 想选非 fallback adapter，
  那就强制退回 recent2000 fallback。

这条规则一旦冻结，
后面的数据只能用来考试，
不能再用来改答案。
```

专业解释：

```text
A frozen rule is a policy whose parameters, target list, thresholds, and
selection logic are fixed before evaluating a validation segment. This prevents
selection leakage from future labels into the deployed decision interface.
```

项目对应：

```text
target_series:
  BAMLH0A0HYM2:realized_vol_20
  DEXJPUS:realized_vol_20

fallback_family:
  recent2000

freeze_after_cut:
  3500
```

## 3. Discovery Split vs Validation Split

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 发现问题用的区间 | discovery split | through `cut3500` |
| 验证规则用的区间 | validation split | after `cut3500` |
| 发现区间变好不够 | in-sample improvement is insufficient | not release evidence |
| 验证区间要真实触发才有意义 | future policy exposure required | changed windows > 0 |

通俗解释：

```text
这次数据被分成两段：

  discovery split：
    用来发现这条规则。

  validation split：
    用来检查这条规则未来有没有用。

如果一条规则只在 discovery split 变好，
它可能只是记住了旧题。

如果它在 validation split 也触发、也变好，
它才开始像一个真正有用的规则。
```

专业解释：

```text
The discovery split measures whether the post-hoc intervention explains the
observed failure. The validation split measures whether the frozen intervention
has out-of-sample decision exposure and improves the selected metric without
using future labels.
```

项目对应：

| Split | Windows | Changed windows | Verdict |
|---|---:|---:|---|
| through freeze cut | 1000 | 89 | `rule_improves_split` |
| future after freeze cut | 4000 | 0 | `no_rule_exposure` |

## 4. What Is Rule Exposure?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 规则真的出手了几次 | policy exposure | `changed_windows` |
| 出手次数为 0，就无法证明它有效 | no treatment means no treatment effect | `changed_windows=0` |
| 没亏不等于有用 | non-harm is not validation | unchanged selection |
| 要证明有用，必须看到触发后的结果 | causal-ish validation requires intervention | changed future windows |

通俗解释：

```text
rule exposure 可以理解成：

  这条规则到底有没有真正改变模型选择？

如果 changed_windows = 0，
意思是：

  未来 4000 个窗口里，
  router 本来就没有在这两个 series 上选非 fallback adapter。

所以规则没有机会发挥作用。

这不是坏结果，
但也不是成功结果。

它只能说明：

  这段未来数据没有考到这条规则。
```

专业解释：

```text
Exposure is the count of validation decisions modified by the frozen policy.
When exposure is zero, the validation segment cannot estimate the policy's
treatment effect because the policy produced the same selected families as the
baseline router.
```

项目对应：

```text
validation_windows: 4000
validation_changed_windows: 0
validation_verdict: no_rule_exposure
overall_verdict: not_validated_no_future_exposure
```

## 5. Why This Does Not Mean The Rule Failed

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 它没有被未来真正测试到 | no validation exposure | future changed windows = 0 |
| 所以不能说它未来有用 | no positive evidence | not promotable |
| 也不能说它未来有害 | no negative evidence | no intervention |
| 只能说证据不够 | inconclusive validation | continue research |

通俗解释：

```text
这里要分清楚三个结论：

  失败：
    规则在未来触发了，而且让结果变差。

  成功：
    规则在未来触发了，而且让结果变好。

  没被考到：
    规则在未来没有触发。

我们这轮是第三种：

  没被考到。

所以不能发布，
但也不用因此删掉这个方向。
它仍然告诉我们：

  之前的坏结果集中在少数 override 决策上。
```

专业解释：

```text
The result is under-identified, not negative. A validation split with zero
interventions cannot support a promotion claim, but it also does not falsify
the localized-router-failure hypothesis.
```

项目对应：

```text
posthoc all rows:
  changed_windows = 89
  negative_series = 0
  relative_lift_vs_fallback = 0.327293%

future validation:
  changed_windows = 0
  verdict = no_rule_exposure
```

## 6. How This Connects To LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 学的是候选能力 | adapter specialization | full/recent adapters |
| router 决定什么时候用哪个能力 | policy selection layer | fallback-veto router |
| 坏结果可能来自 adapter，也可能来自 router | attribution problem | adapter vs selector |
| 本轮更像 router 问题 | localized selection failure | bad overrides |

通俗解释：

```text
LoRA 本身不是一个完整产品。

它只是给 TimesFM 增加了一组更专门的能力：

  full adapter
  recent1500 adapter
  recent2000 adapter
  recent3000 adapter

真正上线时还需要一个选择器：

  什么时候用 zero-shot？
  什么时候用 full？
  什么时候用 recent2000？
  什么时候退回 fallback？

这轮的问题不完全是：

  LoRA adapter 有没有学到东西？

更像是：

  router 在少数窗口不知道该不该相信 adapter。
```

专业解释：

```text
The adapter family provides candidate forecasters. The router is a policy over
candidate families. This round evaluates a policy-level intervention rather
than retraining the LoRA weights. The observed opportunity is selection
locality, not evidence that a larger LoRA rank is needed.
```

项目对应：

```text
adapter layer:
  candidate forecast families

router layer:
  selected family per series/cut/window

current blocker:
  per-series downside and no-leak selection evidence
```

## 7. The Important Lesson

Fact:

```text
The post-hoc target fallback counterfactual reaches 0 negative series on the
completed 5000-window report.
```

Fact:

```text
The frozen future validation split contains 4000 windows but 0 changed windows.
```

Inference:

```text
The target fallback rule remains a useful diagnosis, but it is not a validated
release rule.
```

Recommendation:

```text
Do not keep tuning thresholds blindly. The next useful experiment should create
future exposure: either add a later prediction archive, or train/evaluate a
causal no-leak feature that predicts bad override windows before labels are
known.
```

