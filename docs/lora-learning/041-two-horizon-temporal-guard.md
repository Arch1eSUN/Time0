# 041 - Two-Horizon Temporal Guard

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-two-horizon-guard.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 同时看近况和长期表现 | two-horizon validation | latest cut + recency-weighted history |
| 两边都安全才放行 | conjunctive per-series gate | `recency_allowed and latest_allowed` |
| 还是让 fallback-veto 先选 | post-selector guard | `fallback_veto_two_horizon_guarded` |
| 最后仍没过 promotion | no shared positive config | late/expanded join failed |

通俗解释：

```text
上一轮 latest-cut guard 太短视：

  只看最近一次验证，
  late 上能小赢，
  expanded 上会输。

所以这轮我们加一个更合理的安全阀：

  最近一次不能坏，
  过去一段时间的加权历史也不能坏。

两个条件都满足，
才允许 router 选 LoRA adapter。

只要其中一个不满足，
就退回 recent2000 fallback。
```

专业解释：

```text
This round adds `fallback_veto_two_horizon_guarded`, a post-selector guard that
combines the existing latest-cut gate and recency-weighted gate. A series is
allowed only when both horizons pass the same minimum per-series validation
lift condition.
```

项目对应：

```text
new policy:
  fallback_veto_two_horizon_guarded

new gate:
  two_horizon_selection_risk_gate

fallback:
  recent2000

candidate set:
  knn-regret
```

## 2. What Is A Two-Horizon Guard?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 最近别出事 | latest-cut safety | latest prior cut |
| 长期别太差 | recency-weighted safety | weighted prior cuts |
| 两个都过才上 | intersection gate | logical AND |
| 宁可少选也别乱选 | conservative routing | fallback on failure |

通俗解释：

```text
你可以把 router 想成一个派人上场的教练。

latest-cut guard 只问：

  这个选手上一场打得行不行？

recency-weighted guard 问：

  这个选手最近一段时间整体行不行？

two-horizon guard 同时问两个问题：

  上一场不能差。
  最近整体也不能差。

如果有一个答案是否定的，
就不上这个选手，改用稳定的 fallback。
```

专业解释：

```text
The two-horizon guard is a conjunctive risk gate. It does not average latest
and historical evidence into one score. It requires both independently computed
gates to pass, which makes the policy conservative and easier to interpret.
```

项目对应：

```text
latest horizon:
  latest_cut_selection_risk_gate

history horizon:
  recency_weighted_selection_risk_gate

combined horizon:
  two_horizon_selection_risk_gate
```

## 3. Result Summary

Routed cuts only:

| Check | Config | Delta vs fallback | Split | Verdict |
|---|---|---:|---:|---|
| Frozen balanced expanded | `global/k25/thr0.00015/msvl-0.001/decay0.25` | 0.0000998175 | 5 / 5 | positive |
| Frozen balanced late | same config | -0.0000326219 | 7 / 3 | failed |
| Late sweep best | `series/k50/thr0.00025/msvl0.001/decay0.05` | 0.0000096078 | 3 / 3 | late positive |
| Same late-best on expanded | same config | -0.0000150012 | 4 / 4 | failed |
| Expanded sweep best | `series/k25/thr0.00015/msvl0.001/decay0.05` | 0.0000357210 | 4 / 4 | expanded positive |
| Best shared near-miss | `global/k25/thr0.0001/msvl0.001/decay0.05` | late -0.000001997 / expanded 0.000014219 | 3 / 3 and 2 / 6 | failed |

通俗解释：

```text
这轮比上一轮更接近了。

我们找到了一个 almost pass：

  expanded 是正的
  late 只差大约 0.000002

但规则不能因为“差一点”就算成功。

同一组 frozen 参数必须两边都正。
这轮没有任何一组参数做到。
```

专业解释：

```text
The two-horizon policy reduced the worst mismatch, but the joined late and
expanded sweeps still produced zero configurations with positive delta on both
surfaces. The best min-delta row remained slightly negative on the late archive.
```

项目对应：

```text
both_positive_count:
  0

best near-miss:
  late delta = -0.0000019969607878561613
  expanded delta = 0.000014219138773169382
```

## 4. Why This Is Not A Promotion

通俗解释：

```text
如果我们只看 expanded：

  会觉得 two-horizon guard 可以。

如果我们只看 late：

  也能找到一个 late 上小赢的参数。

但两个参数不是同一个。

模型项目里最危险的事就是：

  在 A 卷子上挑 A 的答案，
  在 B 卷子上挑 B 的答案，
  然后说模型整体变强了。

我们不能这样做。
```

专业解释：

```text
Promotion requires a frozen adapter-selection policy that generalizes across
chronological evaluation surfaces. Surface-specific best rows are diagnostic
evidence only. They do not prove deployable or publishable improvement.
```

项目对应：

```text
late sweep:
  reports/router-policy-sweep-two-horizon-fallback-veto-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

expanded sweep:
  reports/router-policy-sweep-two-horizon-fallback-veto-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

near-miss attribution:
  reports/router-attribution-two-horizon-fallback-veto-near-miss-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
  reports/router-attribution-two-horizon-fallback-veto-near-miss-expanded-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 5. What We Learned About LoRA Routing

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA adapter 不是越多越好 | adapter pool needs selection discipline | five families |
| 路由器不是能随便调 | router must be causal and frozen | no current-cut leakage |
| guard 能减少风险 | downside gating reduces overrides | fallback to `recent2000` |
| 但 guard 不等于能力增长 | guard is selection control, not representation learning | no new weights |

通俗解释：

```text
LoRA 微调给了我们几个“专长不同”的 adapter。

但真正难的是：

  当前窗口该用哪个？

这不是训练更多 adapter 就自动解决。

如果 router 判断错，
强 adapter 也会变成负收益。

guard 的作用是少犯错。
它不是让 adapter 本身变聪明。
```

专业解释：

```text
This checkpoint reinforces that the current bottleneck is no-leak adapter
selection, not adapter weight training. The LoRA adapters already encode
different temporal specializations, but causal selection remains unstable
across chronological regimes.
```

项目对应：

```text
adapter families:
  zero-shot
  full
  recent1500
  recent2000
  recent3000

current fallback:
  recent2000

current blocker:
  causal selection under regime shift
```

## 6. Current Verdict

Fact:

```text
Two-horizon guard was implemented and evaluated on both late and expanded
alignment-normalized surfaces.
```

Fact:

```text
The 48-row joined sweep found no configuration with positive delta on both
late and expanded.
```

Fact:

```text
The best shared near-miss was very close:

  late delta:     -0.0000019969607878561613
  expanded delta:  0.000014219138773169382
```

Inference:

```text
Two-horizon gating is directionally better as a diagnostic structure, but it
still does not solve the routing problem.
```

Recommendation:

```text
Do not promote `fallback_veto_two_horizon_guarded`.

Next step:
  stop only tightening guards.

Instead, add a regime-state feature or regime classifier that can explain why
the same series behaves differently across late and expanded surfaces.
```
