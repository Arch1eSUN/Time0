# 042 - Regime-Full Router Breakthrough

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-regime-full-router.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给 router 加市场状态信息 | regime-aware feature surface | `context_regime` |
| 先不改模型代码 | feature ablation experiment | existing router rows |
| 同一参数要两边都赢 | frozen config cross-surface check | late + expanded |
| 找到第一个共同正收益配置 | shared positive router checkpoint | `regime-full` |

通俗解释：

```text
上一轮 two-horizon guard 已经接近成功，
但还是没有同一组参数同时赢 late 和 expanded。

这轮我们没有继续盲目收紧 guard。

我们问一个更本质的问题：

  router 是否缺少“现在市场处于什么状态”的信息？

所以我们测试了 regime feature。
```

专业解释：

```text
This round evaluates whether no-leak regime features improve causal adapter
routing. The router policy stays fixed as `fallback_veto_two_horizon_guarded`;
the experiment changes only the runtime feature surface.
```

项目对应：

```text
policy:
  fallback_veto_two_horizon_guarded

candidate_set:
  knn-regret

fallback:
  recent2000

new evidence surface:
  router-rows-*-regime-full-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is Regime?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 当前市场天气 | market state / regime | `context_regime` |
| 波动大不大 | volatility state | context ratios |
| 趋势稳不稳 | trend state | past trend features |
| adapter 是否适合当下 | conditional adapter usefulness | router feature |

通俗解释：

```text
同一个 adapter 不是永远好或永远坏。

比如：

  VIX 波动很高的时候，
  recent1500 可能更适合。

  利率走势平稳的时候，
  recent2000 可能更稳。

regime 的意思就是：

  当前窗口属于什么状态？

router 如果不知道状态，
它只能看过去平均表现。

但金融时间序列最麻烦的地方就是：

  平均表现会被 regime change 打断。
```

专业解释：

```text
Regime features are no-leak context-derived state descriptors. They do not use
current-window actuals or errors. They help the selector condition adapter
choice on the observed historical context rather than on a global prior.
```

项目对应：

```text
runtime feature group:
  context_regime

source:
  join_prediction_archives.py

guardrail:
  ablate_router_features.py validates no forbidden actual/error keys
```

## 3. Three Surfaces Compared

| Surface | What It Tests | Late Best Delta | Expanded Best Delta | Shared Positive Configs |
|---|---|---:|---:|---:|
| `alignment-normalized` | alignment + normalized disagreement, no regime | 0.0000096078 | 0.0000357210 | 0 |
| `regime-alignment` | regime + alignment, no normalized disagreement | -0.0000084653 | -0.0000046224 | 0 |
| `regime-full` | full no-leak feature set including regime | 0.0000415758 | 0.0000441823 | 40 |

通俗解释：

```text
这个表非常关键。

不是“加 regime 就赢”。

regime-alignment 反而输了。

真正赢的是 regime-full：

  regime
  + normalized disagreement
  + prediction alignment
  + prediction summaries
  + context

也就是说：

  市场状态本身不够。
  它要和预测分歧、预测和历史的关系一起看。
```

专业解释：

```text
The useful evidence is interactional. `context_regime` alone with alignment is
not sufficient. The full surface restores normalized disagreement features and
produces shared positive configurations across both chronological surfaces.
```

项目对应：

```text
regime-alignment rows:
  reports/router-rows-expanded-regime-alignment-market-macro-realized-vol-20-h20-r4.json
  reports/router-rows-late-regime-alignment-market-macro-realized-vol-20-h20-r4.json

regime-full rows:
  reports/router-rows-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json
  reports/router-rows-late-regime-full-market-macro-realized-vol-20-h20-r4.json
```

## 4. Shared Best Frozen Config

Best shared config by minimum delta across late and expanded:

| Parameter | Value |
|---|---:|
| `policy` | `fallback_veto_two_horizon_guarded` |
| `candidate_set` | `knn-regret` |
| `min_validation_lift` | 0 |
| `min_series_validation_lift` | 0.001 |
| `series_risk_decay` | 0.05 |
| `veto_feature_mode` | `global` |
| `veto_k` | 25 |
| `veto_regret_threshold` | 0.00025 |

Routed cuts only:

| Surface | Selected MAE | Fallback MAE | Delta vs fallback | Split |
|---|---:|---:|---:|---:|
| Late regime-full | 0.0968845010 | 0.0969080555 | 0.0000235545 | 3 / 4 |
| Expanded regime-full | 0.0958599164 | 0.0958798640 | 0.0000199476 | 3 / 3 |

通俗解释：

```text
这是目前最重要的一轮结果。

以前我们经常遇到：

  late 上赢，
  expanded 上输。

或者：

  expanded 上赢，
  late 上输。

这轮第一次找到：

  同一组参数，
  late 正收益，
  expanded 也正收益。
```

专业解释：

```text
This is the first checkpoint in this router sequence where a frozen
configuration is positive on both the later chronological archive and the
expanded archive within the tested parameter box.
```

项目对应：

```text
late attribution:
  reports/router-attribution-two-horizon-fallback-veto-shared-best-late-regime-full-market-macro-realized-vol-20-h20-r4.json

expanded attribution:
  reports/router-attribution-two-horizon-fallback-veto-shared-best-expanded-regime-full-market-macro-realized-vol-20-h20-r4.json
```

## 5. What This Means For LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| adapter 已经有不同专长 | adapter specialization exists | recent/full families differ |
| 关键是看场景派人 | conditional selection | regime-aware router |
| guard 负责刹车 | downside control | two-horizon fallback-veto |
| regime 负责识别天气 | state conditioning | `context_regime` in full surface |

通俗解释：

```text
LoRA 本身像是训练出几种不同打法：

  full
  recent1500
  recent2000
  recent3000

之前的问题是：

  我们不知道什么时候该用哪种打法。

这轮说明：

  只看 adapter 过去表现不够。
  要看当前窗口的市场状态。

这就是 regime-aware routing 的价值。
```

专业解释：

```text
The improvement comes from selection, not new LoRA weight training. The adapter
pool remains unchanged. The gain appears when the router can condition on the
full no-leak regime-aware feature surface and is constrained by two-horizon
downside control.
```

项目对应：

```text
weights changed:
  no

router evidence changed:
  yes

promotion status:
  candidate, not final release
```

## 6. Why Not Final Yet?

通俗解释：

```text
这轮是突破，但还不能直接说项目完成。

原因：

  1. 还是同一个 realized_vol_20 目标。
  2. 还没测第二个金融目标。
  3. split 不是全线胜利，late 是 3/4。
  4. 还没冻结成一个发布版 adapter/router package。

所以现在是：

  可以进入候选池，
  不能直接发布最终模型。
```

专业解释：

```text
The shared positive config clears the current late/expanded gate, but it is not
yet a release-grade result. It still needs second-target validation, a frozen
router config file, and a packaged inference path.
```

项目对应：

```text
current status:
  promotion candidate

next required checks:
  second target
  frozen router manifest
  packaged inference run
```

## 7. Current Verdict

Fact:

```text
Regime-alignment failed on both late and expanded.
```

Fact:

```text
Regime-full found 40 configurations with positive delta on both late and
expanded.
```

Fact:

```text
Best shared frozen config:

  late delta:     0.00002355445156944358
  expanded delta: 0.000019947579099705015
```

Inference:

```text
Regime information is useful only as part of the full no-leak feature surface.
The router needs state-conditioned selection, but not a regime-only feature
surface.
```

Recommendation:

```text
Promote this to the next candidate checkpoint, not to final release.

Next step:
  freeze the regime-full shared config into a router manifest and validate it
  on a second financial target.
```
