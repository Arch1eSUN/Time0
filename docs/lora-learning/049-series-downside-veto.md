# 049 - Series Downside Veto

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-series-downside-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 针对赔钱的 series 加刹车 | series-level downside veto | `--series-downside-threshold` |
| 针对某个 series + adapter 组合加刹车 | series-family downside veto | `--series-family-downside-threshold` |
| 只用过去 cut 判断 | no-leak historical guard | prior cuts only |
| 看能不能把负收益 series 降到 0 | downside release gate | `router_negative_series` |

通俗解释：

```text
上一轮 readiness gate 告诉我们：

  router 总体有收益，
  但还有 3 个 series 被 router 选坏了。

所以这轮不是继续训练 LoRA，
而是给 router 加一个刹车：

  如果一个 series 过去被 router override 后经常比 fallback 差，
  那未来遇到这个 series 时就更保守，退回 fallback。
```

专业解释：

```text
This round adds no-leak historical downside vetoes to the fallback-veto router.
The policy uses prior cuts to estimate whether overrides have historically
helped or harmed a series, then blocks risky overrides on future cuts.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/evaluate_router_fallback_veto.py

helper:
  experiments/timesfm-lora/scripts/router_fallback_veto.py
```

## 2. What Is Downside?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 做错以后亏多少 | negative delta vs fallback | `delta_vs_fallback < 0` |
| 总体赢但局部输 | aggregate lift with series regression | 8 positive / 2 negative |
| 发布前必须控制的伤害 | per-series downside risk | readiness gate |

通俗解释：

```text
如果一个策略总体赚钱，
但总在某几个品种上亏，
它还不能直接上线。

因为真实系统里，用户可能刚好用到那个亏的品种。

所以我们现在不只问：

  总体有没有变好？

还要问：

  有没有某些 series 被我们稳定伤害？
```

专业解释：

```text
Downside means the routed policy has worse error than the fallback for a
specific series. A positive aggregate metric can still hide negative
per-series behavior.
```

项目对应：

```text
release gate:
  router_negative_series must be 0
```

## 3. Series-Level Veto

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 看这个 series 过去整体表现 | historical mean delta by series | `historical_series_delta_summary` |
| 如果历史不够好就退回 fallback | thresholded override veto | `apply_series_downside_veto` |
| 对所有 adapter 选择一起判断 | series-level aggregate | `series_downside_threshold` |

通俗解释：

```text
series-level veto 的逻辑很简单：

  对某个 series 来说，
  过去 router 离开 fallback 后，
  平均到底有没有更好？

如果没有明显更好，
未来就不要乱切，
回到 fallback。
```

专业解释：

```text
The series-level veto aggregates historical override deltas for each series.
When the mean delta is below the configured threshold, current overrides for
that series are replaced with the fallback family.
```

项目对应：

```text
best config:
  series_downside_threshold = 0.0005
```

## 4. Series-Family Veto

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 看某个 series 配某个 adapter 是否危险 | historical mean delta by series-family pair | `historical_series_family_delta_summary` |
| 更细，但可能过度刹车 | finer guard can over-block | DFF turned negative |
| 这轮结果不如 series-level | lower aggregate lift | pair-only / combined sweeps |

通俗解释：

```text
我们还试了更细的规则：

  不是只看这个 series，
  而是看这个 series 选择某个 adapter 时，
  过去到底有没有更好。

听起来更精确，
但结果更差。

原因是它太容易把有用的路线也挡掉。
这叫 over-blocking。
```

专业解释：

```text
The series-family veto estimates downside for each series and selected adapter
pair. It is more granular, but in this run it over-blocked useful routes and
reduced aggregate lift.
```

项目对应：

```text
pair-only result:
  extra lift: 0.231%
  negative series: 3

series + pair combined:
  extra lift: 0.210%
  negative series: 3
```

## 5. What Improved

| Policy | Extra lift | Positive series | Negative series |
|---|---:|---:|---:|
| Previous best | 0.316% | 7 | 3 |
| Strict series-downside | 0.319% | 8 | 2 |
| Pair-only | 0.231% | 7 | 3 |
| Combined | 0.210% | 7 | 3 |

通俗解释：

```text
最好的新结果是：

  总体收益稍微变高
  正收益 series 从 7 个变 8 个
  负收益 series 从 3 个降到 2 个

这是进步。

但 release gate 要求负收益 series 是 0。
所以还没过门。
```

专业解释：

```text
The strict series-level veto improved the risk frontier but did not satisfy the
release constraint. It remains a useful intermediate policy, not a promotable
router.
```

项目对应：

```text
current readiness:
  continue_research

router_negative_series:
  required 0
  actual 2
```

## 6. What This Teaches

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不是越保守越好 | hard gates can over-block useful decisions | pair veto hurt DFF |
| 总体指标和局部风险要一起看 | aggregate/series frontier | readiness gate |
| LoRA 训练后还需要路由系统 | adapter quality != serving policy quality | router layer |
| 下一步需要目标函数，不是继续调阈值 | need explicit risk objective | constrained selector |

通俗解释：

```text
这轮最重要的知识是：

  风险控制不是简单地“多加几个 if”。

太松：
  会留下负收益 series。

太严：
  会把本来赚钱的 DFF 也挡掉。

所以下一步不应该继续手调阈值。
应该让 selector 的目标函数本身知道：

  总收益要高，
  但每个 series 的伤害要被惩罚。
```

专业解释：

```text
The manual threshold frontier is near exhaustion. The next router should encode
series downside in the optimization objective, not only in post-hoc hard vetoes.
```

项目对应：

```text
next useful experiment:
  constrained selector with series-risk penalty
```
