# 050 - Series Risk Objective

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-series-risk-objective.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不只看赚多少，也看亏得疼不疼 | risk-adjusted objective | `risk_adjusted_score` |
| 把坏处变成扣分项 | downside penalty | `series_risk_penalty` |
| 看极端保守会不会更适合发布 | high-risk-penalty sweep | penalties `50`, `100` |
| 继续用过去 cut 做判断 | no-leak evaluation | prior cuts only |

通俗解释：

```text
上一轮我们做了一个硬规则：

  如果某个 series 历史上经常被 router 选坏，
  就直接挡住，退回 fallback。

这一轮换一个角度：

  不只是问哪一个 policy 的 MAE 最低，
  还问哪一个 policy 在扣掉负面伤害以后最划算。

就像投资里不只看收益率，
还要看回撤和亏损集中在哪些资产上。
```

专业解释：

```text
This round adds a risk-adjusted ranking objective over no-leak router policies.
Each policy is still generated without using current-cut labels. Current-cut
labels are used only after the fact to score the offline report.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/evaluate_router_fallback_veto.py

report:
  experiments/timesfm-lora/reports/router-fallback-veto-series-risk-objective-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is An Objective Function?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 告诉模型或选择器什么叫好 | objective function | score to maximize |
| 分数越高越应该选 | optimization criterion | `max(..., key=score)` |
| 不同目标会选出不同策略 | objective-dependent optimum | delta vs risk-adjusted |

通俗解释：

```text
objective function 可以理解成：

  裁判打分规则。

如果裁判只看进球数，
球队会疯狂进攻。

如果裁判同时扣失球分，
球队会更重视防守。

模型训练和 router 选择也是一样：

  你怎么定义好，
  系统就会往哪个方向找。
```

专业解释：

```text
An objective function maps a candidate policy to a scalar score. Optimization
then selects the candidate with the highest score or lowest loss. Changing the
objective changes the preferred policy even when the candidate set is unchanged.
```

项目对应：

```text
old objective:
  maximize delta_vs_fallback

new diagnostic objective:
  maximize risk_adjusted_score
```

## 3. The Formula

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 总收益 | aggregate improvement | `delta_vs_fallback` |
| 总伤害摊到每个窗口 | downside mass per window | `downside_mass_per_window` |
| 你有多怕伤害 | risk aversion coefficient | `series_risk_penalty` |
| 最终分数 | penalized utility | `risk_adjusted_score` |

通俗解释：

```text
这轮的分数公式是：

  最终分数 = 总体收益 - 风险惩罚 * 负面伤害

如果风险惩罚很小，
系统更像是在说：

  只要总体赚得多，局部亏一点可以忍。

如果风险惩罚很大，
系统更像是在说：

  我宁愿少赚，也不要伤害某些 series。
```

专业解释：

```text
risk_adjusted_score = delta_vs_fallback
                    - series_risk_penalty * downside_mass_per_window

where downside_mass_per_window is the absolute sum of negative per-series deltas
divided by routed window count.
```

项目对应：

```text
delta_vs_fallback:
  fallback MAE - routed MAE

downside_mass_per_window:
  abs(sum(negative per-series delta)) / routed_windows
```

## 4. Hard Gate vs Soft Penalty

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 硬门槛：不满足就不能过 | hard constraint | `router_negative_series <= 0` |
| 软惩罚：不好会扣分，但还能赢 | soft penalty | `risk_adjusted_score` |
| 发布标准必须是硬门槛 | release gate | finance readiness |
| 研究排序可以用软惩罚 | diagnostic ranking | risk objective |

通俗解释：

```text
硬门槛像考试及格线：

  低于 60 分，其他优点再多也不算过。

软惩罚像综合评分：

  你某项弱，会扣分，
  但如果其他项很强，可能总分仍然第一。

我们现在不能把发布标准改成软惩罚。
因为金融预测里，一个总体好但稳定伤害某些 series 的模型，
不能说它已经安全可发布。
```

专业解释：

```text
A hard constraint defines feasibility. A soft penalty defines ranking among
candidates. For release decisions, the Time0 finance line uses hard gates:
average lift, positive cut count, router extra lift, negative routed series,
and fallback sensitivity.
```

项目对应：

```text
release gate:
  router_negative_series required: 0
  current actual: 2

diagnostic objective:
  risk penalty 1, 2, 5, 10, 50, 100
```

## 5. What The Result Means

| Policy | Extra lift | Positive series | Negative series | Downside mass / window |
|---|---:|---:|---:|---:|
| Baseline validation-gated | 0.292% | 7 | 3 | 0.0000251505 |
| Best by delta | 0.319% | 8 | 2 | 0.0000080650 |
| Penalty 1 to 10 | 0.319% | 8 | 2 | 0.0000080650 |
| Penalty 50 to 100 | 0.264% | 7 | 3 | 0.0000058045 |

通俗解释：

```text
普通风险惩罚下，系统还是选同一个最优 policy：

  收益最高，
  负 series 从 3 降到 2，
  downside 也明显下降。

但如果我们把风险惩罚调到非常大，
系统会选一个更保守的 policy：

  负面伤害总量更低，
  但负收益 series 反而从 2 变 3，
  总收益也下降。

这说明：

  当前候选 policy 里面，还没有真正干净的解。
```

专业解释：

```text
The risk objective exposes a frontier. The best aggregate policy and normal
risk-adjusted policies coincide. Extremely high penalties prefer lower negative
mass, but not lower negative series count.
```

项目对应：

```text
best_no_negative_series:
  null

finance readiness:
  continue_research
```

## 6. Why This Is Still Useful For LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 不是只训练一个 adapter | adapter family search | full / recent windows / zscore |
| 还要学会什么时候用哪个 adapter | routing problem | prediction router |
| router 的目标会决定模型系统行为 | policy optimization | objective selection |
| 发布前要证明局部不伤人 | per-series safety | negative series gate |

通俗解释：

```text
你可以把 Time0 现在的系统想成两层：

  第一层：LoRA adapter 负责产生不同风格的预测。
  第二层：router 负责选择这一窗口该信谁。

只训练 LoRA adapter 不够。

如果 router 乱选，
多个 adapter 组合起来也可能变差。

所以 LoRA 实战不是：

  跑完训练就结束。

而是：

  训练 adapter，
  导出预测，
  做 no-leak 回测，
  设计选择目标，
  用 release gate 判断能不能发布。
```

专业解释：

```text
LoRA fine-tuning creates adapter candidates. A deployment-grade forecasting
system also needs policy selection, evaluation archives, leakage controls, and
promotion gates. The adapter is one Module; the router is another Module.
```

项目对应：

```text
adapter candidates:
  full
  recent1500
  recent2000
  recent3000
  zero-shot

router candidate:
  no-leak fallback-veto KNN-regret with series downside control
```

## 7. What We Learned This Round

Fact:

```text
The best ordinary risk-adjusted policy still has 2 negative routed series.
```

Fact:

```text
Extreme risk penalties reduce downside mass but increase negative series count
to 3 and reduce extra lift to 0.264%.
```

Inference:

```text
The current router policy family has reached a local limit. More threshold
tuning is unlikely to satisfy the release gate by itself.
```

Recommendation:

```text
Next useful work should target the remaining failure directly:

  BAMLH0A0HYM2:realized_vol_20
  DEXJPUS:realized_vol_20

That can mean a new adapter/rank experiment for those regimes, or a selector
with a hard per-series constraint instead of only aggregate downside penalty.
```
