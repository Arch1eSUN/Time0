# 051 - Hard Constraints And All-Fallback Failure

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-policy-history-constraint.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给每个 series 加硬门槛 | hard per-series constraint | `policy_history_series_threshold` |
| 只看这个 policy 过去的结果 | same-policy historical evidence | `policy_history_series_delta_summary` |
| 如果过去不够好，就强制退回 fallback | fail-closed override blocking | `apply_policy_history_series_constraint` |
| 看能不能负 series 清零还保留收益 | constrained release candidate | `best_no_negative_series` |

通俗解释：

```text
上一轮我们用软惩罚：

  收益 - 风险惩罚 * 伤害

但软惩罚没有把 negative series 清到 0。

所以这一轮换成硬约束：

  如果某个 series 在过去 cut 里，
  用同一个 router policy 后表现不够好，
  那未来遇到它就直接退回 fallback。

这比软惩罚更狠。
软惩罚只是扣分。
硬约束是不让它过门。
```

专业解释：

```text
This round adds a sequential no-leak per-series constraint. For each current
cut, the policy first applies its normal router/veto logic, then checks prior
completed cuts from the same policy. If a series has insufficient historical
mean delta versus fallback, current non-fallback selections for that series are
replaced by the fallback family.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/evaluate_router_fallback_veto.py

new report:
  reports/router-fallback-veto-policy-history-constraint-fine-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A Hard Constraint?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不满足就不能选 | feasibility constraint | gate before selection |
| 不是扣分，是禁止 | hard rejection | force fallback |
| 用来保护底线 | safety constraint | `router_negative_series <= 0` |
| 可能过度保守 | over-constraining | all fallback |

通俗解释：

```text
硬约束像门禁：

  你没有证件，
  就不能进。

它不是说：

  你没证件扣 10 分，
  但总分够高还能进。

在我们的 router 里，
硬约束就是：

  只要某个 series 的历史证据不够好，
  当前就不能用 LoRA adapter 或 zero-shot 去 override fallback。
```

专业解释：

```text
A hard constraint defines the feasible candidate set. Candidates violating the
constraint are removed or altered before scoring. In this run, violation means
the selected family is replaced with the fallback family.
```

项目对应：

```text
fallback_family:
  recent2000

constraint action:
  selected_family -> recent2000
```

## 3. No-Leak Still Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不能偷看当前考卷答案 | no current-cut leakage | prior reports only |
| 当前 cut 只能用过去 cut | chronological causality | `prior_reports=per_cut` |
| 结果出来后才能评分 | offline evaluation | current-cut scoring |
| 这才像真实上线 | deploy-like evaluation | fail-closed router |

通俗解释：

```text
我们不能这样做：

  看当前 cut 哪个 series 亏了，
  然后说未来不要选它。

那是偷看答案。

这一轮的做法是：

  先按时间顺序走。
  到 cut 5000 时，只能看 cut 5000 之前的结果。
  到 cut 5500 时，只能看 cut 5500 之前的结果。

这样才接近真实系统上线时的状态。
```

专业解释：

```text
The constraint is computed sequentially. `per_cut` contains only already
evaluated prior cuts for the same policy. The current cut's labels are not used
to decide the current cut's constraint.
```

项目对应：

```text
policy_history_series_delta_summary(
  prior_reports=per_cut,
  fallback_family="recent2000"
)
```

## 4. What Went Wrong

| Constraint mode | Extra lift | Positive series | Negative series | Meaning |
|---|---:|---:|---:|---|
| Current best | 0.319% | 8 | 2 | useful but still blocked |
| Delayed hard constraint | 0.294% | 7 | 3 | too weak / too late |
| Early hard constraint | 0.000% | 0 | 0 | all fallback |

通俗解释：

```text
我们希望看到的是：

  还有收益，
  但没有负收益 series。

实际看到的是两种坏情况：

  1. 约束晚一点、弱一点：
     还有收益，但 negative series 还是 3 个。

  2. 约束早一点、强一点：
     negative series 清零了，
     但收益也清零了。

第二种看起来安全，
但它只是把 router 全关了。
这不叫模型变强。
这叫退回 baseline。
```

专业解释：

```text
The policy-history constraint has a cliff. With `min_windows=100`, it preserves
some routing behavior but fails the negative-series gate. With `min_windows=50`,
even very small positive thresholds collapse the routed policy to fixed fallback,
yielding zero downside and zero lift.
```

项目对应：

```text
best_no_negative_series:
  relative_lift_vs_fallback = 0.000%
  positive_routed_series_count = 0
  negative_routed_series_count = 0
```

## 5. Why 0 Negative Is Not Automatically Success

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不亏不等于有用 | zero downside is not improvement | `router_extra_lift = 0` |
| 全部退回 fallback 很安全但没价值 | degenerate fallback policy | `selected_family = recent2000` |
| release 需要安全和收益同时过 | conjunctive gates | readiness gate |
| 不能用安全掩盖无提升 | promotion discipline | `continue_research` |

通俗解释：

```text
如果我们把所有选择都退回 fallback，
当然不会再比 fallback 差。

因为它就是 fallback。

但我们的目标不是：

  不犯错。

我们的目标是：

  在不造成局部伤害的前提下，
  比 fallback 更强。

所以 0 negative series 只是必要条件，
不是充分条件。
```

专业解释：

```text
The release gate is conjunctive. A candidate must satisfy router extra lift and
negative-series constraints at the same time. A degenerate all-fallback policy
satisfies the downside constraint but fails the lift constraint.
```

项目对应：

```text
policy-history readiness:
  router_release_candidate = best_no_negative_series
  router_extra_lift = 0.000%
  negative_router_series = 0
  verdict = continue_research
```

## 6. What This Teaches About LoRA Systems

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA adapter 强不强要看系统效果 | adapter value is policy-dependent | adapter + router |
| 太保守的 router 会浪费 adapter | over-gating suppresses model value | all fallback |
| 太激进的 router 会伤害局部 series | under-gating causes downside | negative series |
| 真正难点在中间 | risk-return frontier | promotion boundary |

通俗解释：

```text
LoRA 微调不是只问：

  adapter 训练出来了吗？

更重要的问题是：

  这个 adapter 在什么时候该被使用？
  在什么时候不该被使用？

如果 router 太激进，
它会把某些 series 选坏。

如果 router 太保守，
它就永远退回 fallback，
等于白训练。

这就是我们现在卡住的地方：

  不是没有信号，
  而是还没找到安全使用信号的方法。
```

专业解释：

```text
The adapter family contains useful signal, but the current policy class cannot
separate beneficial overrides from harmful overrides cleanly enough for release.
This is a policy-selection failure, not proof that the LoRA adapters contain no
domain signal.
```

项目对应：

```text
current best:
  useful signal: 0.319% extra lift
  blocker: 2 negative routed series

hard constraint:
  safe but degenerate: 0.000% extra lift
```

## 7. Next Direction

Fact:

```text
The hard per-series constraint did not produce a positive no-negative router.
```

Fact:

```text
The only no-negative policy found in this round is all fallback.
```

Inference:

```text
The current threshold-veto family is not expressive enough to solve the finance
release gate.
```

Recommendation:

```text
Stop tuning global per-series thresholds.

Next useful work should target the two remaining negative series directly:

  BAMLH0A0HYM2:realized_vol_20
  DEXJPUS:realized_vol_20

That means either:

  1. train/evaluate a small new adapter or rank variant aimed at these regimes,
  2. add features that distinguish their good vs bad override windows,
  3. or build a selector that handles these series as explicit constrained cases.
```
