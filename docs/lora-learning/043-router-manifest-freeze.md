# 043 - Router Manifest Freeze

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-router-manifest.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把候选规则写死 | frozen router manifest | JSON manifest |
| 不再靠手抄命令 | reproducible config artifact | `manifests/router/...json` |
| 重新跑验证 | manifest-driven evaluation | `evaluate_router_manifest.py` |
| 两张验证面都通过 | required surfaces passed | late + expanded |

通俗解释：

```text
上一轮我们找到一个真正重要的候选：

  regime-full
  two-horizon fallback-veto
  late 和 expanded 都为正

但如果它只停留在笔记里，
就还不是一个工程资产。

这轮我们把它冻结成 manifest。
```

专业解释：

```text
This round converts the shared-positive router checkpoint into a structured
manifest and adds a manifest evaluator that rebuilds attribution reports from
the frozen configuration.
```

项目对应：

```text
manifest:
  experiments/timesfm-lora/manifests/router/market-macro-realized-vol-20-regime-full-two-horizon.json

validator:
  experiments/timesfm-lora/scripts/evaluate_router_manifest.py
```

## 2. What Is A Manifest?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 一张固定配方 | immutable config artifact | router JSON |
| 写清楚用什么材料 | explicit inputs and features | surfaces + feature groups |
| 写清楚怎么做 | router parameters | policy + thresholds |
| 写清楚怎么验收 | promotion gates | expected deltas |

通俗解释：

```text
manifest 可以理解成：

  这套 router 的身份证。

它写清楚：

  用哪个目标
  用哪个特征面
  用哪个 policy
  每个阈值是多少
  必须在哪些验证面通过

这样以后我们不用靠记忆或聊天记录复现。
```

专业解释：

```text
A manifest is a frozen interface between research and release engineering. It
turns a discovered experiment into an explicit, reviewable, reproducible
configuration.
```

项目对应：

```text
schema_version:
  1

status:
  candidate

feature_surface:
  regime-full

required_surfaces:
  late_regime_full
  expanded_regime_full
```

## 3. Frozen Router Config

| Parameter | Value |
|---|---:|
| `policy` | `fallback_veto_two_horizon_guarded` |
| `candidate_set` | `knn-regret` |
| `selection_metric` | `mae` |
| `cold_start_family` | `recent2000` |
| `fallback_family` | `recent2000` |
| `min_validation_lift` | 0 |
| `min_series_validation_lift` | 0.001 |
| `series_risk_decay` | 0.05 |
| `veto_feature_mode` | `global` |
| `veto_k` | 25 |
| `veto_regret_threshold` | 0.00025 |

通俗解释：

```text
这组参数以后就是当前候选 router 的固定规则。

不能在 late 上用一组，
expanded 上又换另一组。

这就是 frozen config 的意义。
```

专业解释：

```text
The manifest stores one frozen router configuration. Validation surfaces are
allowed to differ, but router parameters are not.
```

## 4. Manifest Evaluation Result

Command:

```bash
uv run python scripts/evaluate_router_manifest.py \
  --manifest manifests/router/market-macro-realized-vol-20-regime-full-two-horizon.json \
  --output reports/router-manifest-eval-market-macro-realized-vol-20-regime-full-two-horizon.json \
  --tolerance 1e-12
```

Result:

| Surface | Selected MAE | Fallback MAE | Delta vs fallback | Delta error | Passed |
|---|---:|---:|---:|---:|---|
| `late_regime_full` | 0.0968845010 | 0.0969080555 | 0.0000235545 | 0 | yes |
| `expanded_regime_full` | 0.0958599164 | 0.0958798640 | 0.0000199476 | 0 | yes |

通俗解释：

```text
验证脚本不是读旧结论。

它做的是：

  读取 manifest
  重新跑 attribution builder
  重新算 late 和 expanded 的结果
  对比 manifest 里的 expected delta

这次 delta_error 都是 0。
```

专业解释：

```text
The evaluator rebuilds the attribution report from manifest parameters and
asserts that observed deltas match expected deltas within tolerance. Both
required surfaces passed.
```

项目对应：

```text
evaluation report:
  reports/router-manifest-eval-market-macro-realized-vol-20-regime-full-two-horizon.json

passed:
  true
```

## 5. Why This Matters For LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 训练只是第一半 | adapter weights are not enough | LoRA adapter pool |
| 怎么派 adapter 也要固定 | serving policy must be versioned | router manifest |
| 能复现才像项目 | reproducibility gate | manifest evaluator |
| 能验收才像候选 | promotion gate | required surfaces |

通俗解释：

```text
LoRA 项目不是只训练出 adapter 就结束。

真正发布时还要回答：

  什么时候用哪个 adapter？
  如果 router 不确定，退回哪个 fallback？
  这套规则有没有固定版本？
  能不能一条命令重现结果？

manifest 就是往发布方向迈的一步。
```

专业解释：

```text
For an adapter-based forecasting system, the release artifact is not only LoRA
weights. It also includes the serving policy that selects adapters under
causal constraints.
```

项目对应：

```text
adapter layer:
  full/recent1500/recent2000/recent3000

serving layer:
  fallback_veto_two_horizon_guarded

frozen serving artifact:
  router manifest
```

## 6. Current Verdict

Fact:

```text
The regime-full shared-positive router is now frozen into a manifest.
```

Fact:

```text
The manifest evaluator rebuilt both required surfaces and passed:

  late delta:     0.00002355445156944358
  expanded delta: 0.000019947579099705015
```

Inference:

```text
The router candidate is now reproducible as an engineering artifact, not only
as a notebook-style experiment.
```

Recommendation:

```text
Keep status as candidate.

Next step:
  validate the same manifest pattern on a second financial target before
  calling this a release-ready vertical adapter/router.
```
