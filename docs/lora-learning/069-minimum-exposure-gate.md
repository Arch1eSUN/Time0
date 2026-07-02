# 069 - Minimum Exposure Gate

Date: 2026-07-03

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-03-market-macro-min-exposure-gate-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不能只看模型有没有赢 | metric pass is not enough | `strict_positive` |
| 还要看它改了多少地方 | minimum exposure | `changed_windows` |
| 改太少的胜利不可信 | sparse-rule high variance | previous 1/3/11 fold exposure |
| 这轮给验证门加门槛 | promotion gate | `--min-validation-*` |

通俗解释：

```text
上一轮 false-positive penalty 有一个问题：

  它终于让 strict validation 通过了。

但它通过的方式很危险：

  第一个验证折只改了 1 个窗口。
  第二个验证折只改了 3 个窗口。
  第三个验证折只改了 11 个窗口。

这就像一个学生考试：

  一张卷子 100 题。
  他只做了 1 题。
  这 1 题碰巧做对了。

你不能说他已经掌握了整门课。
```

专业解释：

```text
The previous strict gate checked non-regression but not exposure size.
A policy can pass strict validation with a tiny number of changed windows.
That produces high-variance evidence and can fail future holdout.
```

项目对应：

```text
previous selected strict candidate:
  fold_changed_windows: 1, 3, 11
  final_changed_windows: 6
  final_metric_delta: -0.0000069200
```

## 2. What Is Exposure?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型真正出手了多少次 | policy intervention count | `changed_windows` |
| 不出手就没证据 | no treatment effect | `no_rule_exposure` |
| 出手太少也没证据 | weak statistical support | sparse exposure |
| 出手多才知道规则稳不稳 | enough evaluated interventions | min exposure gate |

通俗解释：

```text
我们这个 router 做的事情是：

  原本 selected adapter 会预测。
  logistic veto 判断要不要退回 fallback。

如果它决定退回 fallback，
这一个窗口就叫 changed window。

所以 changed_windows 的意思是：

  这个规则到底改变了多少次真实预测选择。
```

专业解释：

```text
Exposure means the number of evaluation windows where the policy changes the
selected family. In this script, it is measured by `veto.changed_windows`.
Without enough exposure, metric deltas are unstable because they come from too
few interventions.
```

项目对应：

```text
changed_windows = count(selected_family_before != selected_family_after)

if changed_windows == 0:
  verdict = no_rule_exposure
```

## 3. Why Metric Improvement Alone Is Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 赢了不代表可靠 | positive delta can be noisy | `metric_delta > 0` |
| 赢 1 个窗口可能是运气 | small-N variance | sparse fold |
| 金融里不能靠碰巧 | unstable edge risk | promotion blocked |
| 要看不同时间段是否都能站住 | chronological consistency | validation folds |

通俗解释：

```text
假设一个交易策略：

  只交易 1 次。
  那 1 次赚了钱。

你会不会马上上真钱？

不应该。

因为你不知道：

  它是真的有能力，
  还是刚好那一次运气好。

我们的 router 也是一样。

只改 1 个窗口然后赢了，
不能说明模型真的学会了金融时序规律。
```

专业解释：

```text
Metric improvement estimates policy value from observed interventions.
When the number of interventions is tiny, the estimate has high variance.
For chronological validation, this is especially dangerous because a sparse
win can disappear in the next time split.
```

项目对应：

```text
old strict requirement:
  combined_metric_delta > 0
  fold_metric_regressions = 0

new extra requirement:
  combined_changed_windows >= N
  each fold changed_windows >= M
```

## 4. What We Changed In Code

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 加了总出手次数门槛 | combined exposure threshold | `--min-validation-changed-windows` |
| 加了每折出手次数门槛 | per-fold exposure threshold | `--min-validation-fold-changed-windows` |
| 报告里记录每折出手次数 | exposure diagnostics | `fold_changed_windows` |
| strict 和 robust 都要过曝光门 | fail-closed promotion | `exposure_pass` |

通俗解释：

```text
这轮不是让 LoRA adapter 重新训练。

这轮是在训练后的 router 验证门上加规则：

  如果你说这个 veto 规则好，
  那你必须证明它真的出手了足够多次。

不是只碰 1 个窗口就说自己成功。
```

专业解释：

```text
The script now computes combined and fold-level intervention counts during
validation. A candidate can be considered validation-positive only if
`exposure_pass` is true.
```

项目对应：

```text
new CLI:
  --min-validation-changed-windows
  --min-validation-fold-changed-windows

new summary fields:
  combined_changed_windows
  fold_changed_windows
  fold_under_min_exposure
  exposure_pass
```

## 5. The Thresholds We Used

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总共至少改 20 次 | combined exposure floor | `20` |
| 每个验证折至少改 2 次 | per-fold exposure floor | `2` |
| 默认还是兼容旧逻辑 | backward-compatible default | `1` and `1` |
| 这不是最终答案，只是第一道门 | first calibrated guard | exploratory threshold |

通俗解释：

```text
这轮我们先设置一个很温和的门槛：

  三个验证折加起来，至少改 20 个窗口。
  每一个验证折，至少改 2 个窗口。

为什么不是 100？

因为我们还在探索。
门槛太高可能把所有规则都杀掉。

为什么不是 1？

因为上一轮已经证明 1 太低。
```

专业解释：

```text
The threshold is a validation contract, not a claim about statistical
significance. It removes obviously sparse policies while preserving enough
candidates for diagnostic comparison.
```

项目对应：

```bash
--min-validation-changed-windows 20
--min-validation-fold-changed-windows 2
```

## 6. What Happened

| Surface | Gate | Strict-positive | Robust-pass | Final changed | Final delta | Verdict |
|---|---|---:|---:|---:|---:|---|
| no-series | strict | 0 | 5 | n/a | n/a | strict_gate_no_candidate |
| no-series | robust | 0 | 5 | 52 | +0.0000070437 | incremental_positive_but_below_fallback |
| include-series | strict | 0 | 2 | n/a | n/a | strict_gate_no_candidate |
| include-series | robust | 0 | 2 | 0 | +0.0000000000 | not_validated_no_future_exposure |

通俗解释：

```text
加了 exposure gate 之后：

  上一轮那种“只改几个点就通过”的规则被挡住了。

no-series robust 找到一个更像样的规则：

  验证集改了 144 个窗口。
  final 改了 52 个窗口。
  final 是小正数。

但是它仍然不能晋级。

原因是：

  三个验证折里，有两个折是亏的。
```

专业解释：

```text
The exposure gate changes the failure mode. Sparse strict positives disappear.
The best no-series robust candidate has enough intervention count, but it fails
strict validation because `fold_metric_regressions=2`.
```

项目对应：

```text
selected robust no-series:
  combined_changed_windows: 144
  fold_changed_windows: 76, 33, 35
  fold_metric_regressions: 2
  final_changed_windows: 52
  final_metric_delta: +0.0000070437
```

## 7. Why Robust Can Improve Final But Still Not Promote

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| final 小赢不等于验证通过 | holdout positive is not enough | `incremental_positive_but_below_fallback` |
| 两个验证折亏了 | chronological instability | `fold_metric_regressions=2` |
| 比 fallback 还差 | below fixed fallback | negative relative lift |
| 只能算信号，不能算版本 | diagnostic only | not promotable |

通俗解释：

```text
这点很重要：

  final 小赚，不代表项目成功。

因为我们不是在找一个碰巧 final 赢的规则。

我们要找的是：

  在不同历史时间段都相对稳定，
  到未来也能继续有用，
  并且整体强过固定 fallback 的规则。

这轮 robust 候选没有达到。
```

专业解释：

```text
Promotion requires validation stability before final holdout evidence.
The robust candidate improves final holdout slightly, but validation fold
direction is inconsistent and its final relative lift vs fallback remains
negative.
```

项目对应：

```text
validation_cut3750:
  metric_delta: -0.0000538052

validation_cut4000:
  metric_delta: -0.0003655074

validation_cut4250:
  metric_delta: +0.0013574278

final:
  metric_delta: +0.0000070437
  relative_lift_vs_fallback: -0.0013671695
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 微调不只是训练 adapter | adapter plus router plus validation | Time0 stack |
| 模型会学出很多看似有用的规则 | candidate overproduction | 200 configs |
| 验证门决定哪些规则能进入项目 | promotion contract | strict gate |
| 成功要同时满足多层证据 | multi-surface validation | folds and final |

通俗解释：

```text
你现在要形成一个很重要的 LoRA 项目观念：

  LoRA 微调不是“loss 下降就结束”。

真正做一个领域模型，要问：

  adapter 是否有用？
  router 是否知道什么时候用 adapter？
  验证集是否稳定？
  final 是否真的提升？
  提升是否强过 fallback？
  风险是否集中在某几个 series？

这些都过了，才叫接近可发布。
```

专业解释：

```text
Fine-tuned adapters create candidate specialization. The routing and validation
layers determine whether specialization transfers. Minimum exposure is part of
the validation contract because it prevents over-promoting low-intervention
rules.
```

项目对应：

```text
LoRA adapter:
  learns a domain specialization

router:
  chooses adapter or fallback

strict validation:
  decides whether a rule can touch final holdout

minimum exposure:
  prevents sparse validation wins from being over-promoted
```

## 9. Current State After This Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 上一轮的问题被修掉了 | sparse strict positives blocked | strict-positive 7 -> 0 |
| 新问题更清楚了 | fold direction instability | fold regressions remain |
| no-series 比 include-series 更值得继续 | better transfer surface | include-series final exposure 0 |
| 下一步要处理最差验证折 | worst-fold-aware objective | cut3750/cut4000 losses |

通俗解释：

```text
项目没有失败。

它是在变得更清楚：

  以前我们不知道为什么 strict 过了还会 final 失败。
  现在知道了：exposure 太小。

  这轮修了 exposure。
  然后发现新问题：不同时间折方向不一致。

这就是研究过程：

  每轮不是都要直接成功。
  每轮要把失败原因变得更精确。
```

专业解释：

```text
The blocker has moved from sparse exposure to chronological fold instability.
This is a better-defined failure mode and suggests a worst-fold-aware or
fold-consistency-aware objective.
```

项目对应：

```text
fixed blocker:
  sparse strict-positive promotion

current blocker:
  robust candidates still have fold_metric_regressions > 0

preferred next surface:
  no-series logistic or expected-regret router
```

## 10. Next Round

Recommendation:

```text
Keep:
  minimum exposure gate
  false-positive penalty support
  strict fail-closed promotion

Do not promote:
  robust no-series candidate
  include-series candidate

Next experiment:
  train or rank candidates with worst-fold-aware utility
```

Success target:

```text
strict_positive > 0
exposure_pass = true
fold_metric_regressions = 0
fold_negative_regressions = 0
final_changed_windows is not tiny
final_metric_delta > 0
final relative lift beats fixed fallback
```
