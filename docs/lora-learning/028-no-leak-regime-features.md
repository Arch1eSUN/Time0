# 028 - No-Leak Regime Features

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-regime-router.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不重新训练 adapter | reuse existing LoRA adapters | local archives |
| 给 router 更多考前信息 | add no-leak runtime features | `feature_set=context_prediction_regime_v2` |
| 重新合并 router rows | rebuild prediction archive rows | 5500 rows |
| 重新评估选择器 | rerun no-leak router validation | early-regime reports |

通俗解释：

```text
上一轮告诉我们：
多加 cut 不够。

这轮我们没有继续训练新 LoRA。
因为问题不在 adapter 本身。

问题是 router 在选择 adapter 时，
看见的信息太少。

所以这轮做的是：
让 router 在不偷看未来答案的前提下，
多看一些“当前市场状态”和“各 adapter 预测形状”的特征。
```

专业解释：

```text
We enriched the prediction-archive router rows with no-leak regime and
prediction-context alignment features, then reran the existing chronological
validation-gated router on the early rolling grid.
```

项目对应：

```text
changed:
  scripts/join_prediction_archives.py
  scripts/evaluate_prediction_router.py

new local report:
  reports/router-rows-early-regime-market-macro-realized-vol-20-h20-r4.json

unchanged:
  TimesFM 2.5 base model
  LoRA rank
  LoRA adapters
  prediction archives
```

## 2. What Is A No-Leak Runtime Feature?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 考试前就能看到的信息 | observable before forecast target | `runtime_features` |
| 不能包含答案 | no future actuals/errors | `validate_no_leak()` |
| 可以包含模型预测 | prediction-derived features are allowed | `prediction_summaries` |
| 可以包含过去走势 | context-derived features are allowed | `context_regime` |

通俗解释：

```text
router 就像一个考场里的调度员。

它可以看：
  过去 128 天发生了什么
  每个 adapter 给出的预测长什么样
  adapter 之间分歧大不大

它不能看：
  未来真实值
  哪个 adapter 这次错得少
  当前 window 的 MAE 或 SMAPE

如果看了这些答案，
结果就叫 leaky。
leaky 只能当上限，不能发布。
```

专业解释：

```text
A no-leak runtime feature is any feature available at forecast time. It may use
historical context and model predictions, but it must not use future actuals,
current-window errors, or current-window best-family labels.
```

项目对应：

```text
allowed runtime groups:
  context
  context_regime
  prediction_summaries
  prediction_disagreement
  prediction_disagreement_normalized
  prediction_context_alignment

forbidden runtime keys:
  actual
  mae
  smape
  best_family
  family_errors
  label
```

## 3. What Features Did We Add?

| Feature group | 通俗解释 | 专业解释 |
|---|---|---|
| `context_regime` | 现在这段历史是平稳还是剧烈 | volatility, trend, range, z-score features |
| `prediction_disagreement_normalized` | adapter 分歧相对当前波动有多大 | disagreement scaled by context mean/std |
| `prediction_context_alignment` | 每个 adapter 的预测和当前历史是否贴合 | predicted mean/last/std/range/trend vs context |

通俗解释：

```text
原来 router 只知道：
  过去均值是多少
  过去标准差是多少
  各 adapter 预测均值是多少

现在 router 还能知道：
  当前最后一个点偏离均值多少
  当前波动相对均值大不大
  adapter 预测是不是突然跳离过去
  adapter 之间的分歧相对当前波动是否异常
```

专业解释：

```text
The new features convert raw context and prediction summaries into scale-aware
and regime-aware features. This helps kNN and softmax routers compare windows by
shape instead of only raw magnitude.
```

项目对应：

```text
context: 6 features
context_regime: 8 features
prediction_summaries: 35 features
prediction_disagreement: 7 features
prediction_disagreement_normalized: 14 features
prediction_context_alignment: 40 features
```

## 4. What Changed In The Result?

Routed cuts only, MAE:

| Run | Router | MAE | Delta vs fixed recent2000 | Verdict |
|---|---|---:|---:|---|
| early grid before regime features | validation-gated | 0.0921934286 | -0.0001701487 | failed |
| early grid with regime features | validation-gated | 0.0917723992 | 0.0002508807 | first positive MAE milestone |
| early grid with regime features | best diagnostic | 0.0916329967 | 0.0003902831 | diagnostic only |
| early grid with regime features | fixed recent2000 | 0.0920232799 | 0.0000000000 | fallback |

通俗解释：

```text
这是第一次：
一个 no-leak validation-gated router
在 early grid 上真正打过 fixed recent2000。

也就是说：
“让 router 看更好的考前信息”
比“继续加 cut”更有用。
```

专业解释：

```text
The enriched feature set changed validation-gated routing from negative MAE
delta to positive MAE delta over the fixed recent2000 fallback. This validates
runtime feature quality as a higher-leverage seam than adapter retraining for
the current bottleneck.
```

项目对应：

```text
best chronological diagnostic:
  knn_regret_series_k25

validation-gated routed MAE:
  0.0917723992

fixed recent2000 routed MAE:
  0.0920232799

delta vs fallback:
  +0.0002508807

improvement vs zero-shot:
  2.006165%
```

## 5. Why It Is Still Not Promotion Ready

| Check | Result | Meaning |
|---|---:|---|
| MAE validation-gated | +0.0002508807 vs fallback | positive |
| SMAPE validation-gated | -0.0001982436 vs fallback | negative |
| series-guarded MAE | -0.0000320558 vs fallback | negative |
| series-risk MAE | -0.0000320558 vs fallback | negative |
| positive vs negative series | 5 / 5 | not broad enough |

通俗解释：

```text
这轮是一个好信号，
但还不能发布。

原因：
  MAE 赢了
  SMAPE 没赢
  series guard 没赢
  正负 series 是 5 对 5

所以它不是稳定胜利。
它是一个重要突破：
我们知道应该继续增强 router 特征，
而不是盲目继续训练 adapter。
```

专业解释：

```text
The default MAE gate is positive, but cross-metric and per-series robustness are
not yet sufficient. Promotion remains blocked until the router shows stable lift
under series-aware gates or a better risk policy.
```

项目对应：

```text
SMAPE validation-gated delta:
  -0.0001982436

series_guarded routed MAE delta:
  -0.0000320558

series_risk routed MAE delta:
  -0.0000320558

publication:
  blocked
```

## 6. Threshold Sweep

Routed cuts only:

| min_validation_lift | Routed MAE | Delta vs fallback | Positive series | Negative series |
|---:|---:|---:|---:|---:|
| 0.000 | 0.0917256164 | 0.0002976635 | 5 | 5 |
| 0.005 | 0.0917529851 | 0.0002702947 | 6 | 4 |
| 0.010 | 0.0917723992 | 0.0002508807 | 5 | 5 |
| 0.020 | 0.0920283258 | -0.0000050459 | 5 | 5 |
| 0.030 | 0.0920232799 | 0.0000000000 | 0 | 0 |
| 0.050 | 0.0920232799 | 0.0000000000 | 0 | 0 |

通俗解释：

```text
阈值越严格，
router 越不敢接管。

0.0 到 0.01：
  router 还能带来正收益。

0.02：
  太严格，收益消失。

0.03 以上：
  完全退回 recent2000。
```

专业解释：

```text
The lift survives low-to-default validation thresholds but not stricter
thresholds. This suggests the feature signal is real but modest.
```

项目对应：

```text
best tested threshold by MAE:
  min_validation_lift=0.0

best tested threshold by series balance:
  min_validation_lift=0.005

current default:
  min_validation_lift=0.01
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不一定要一直训练 adapter | selection can be the bottleneck | router feature seam |
| 模型输出本身也能当信号 | prediction-derived features can guide routing | prediction summaries |
| 不能只看一个指标 | single-metric wins are insufficient | MAE positive, SMAPE negative |
| 成功要能跨 series | broad per-series stability matters | 5 positive / 5 negative |

通俗解释：

```text
LoRA 微调不是只有一条路：

路线 A：
  继续训练更强 adapter。

路线 B：
  已有多个 adapter，
  学会什么时候用哪个。

这轮证明：
路线 B 开始有效了。

但我们还没把路线 B 做稳。
```

专业解释：

```text
Adapter specialization and adapter selection are separate learning problems.
When multiple LoRA adapters encode different data-window biases, the router
needs forecast-time regime features to exploit that specialization causally.
```

项目对应：

```text
adapter training:
  unchanged

router feature quality:
  improved

MAE no-leak router:
  first positive default-gated result

promotion status:
  not ready
```

## 8. Current Verdict

Fact: enriched no-leak regime features turned the default validation-gated MAE
router from negative to positive against fixed `recent2000`.

Fact: the result is still not robust across SMAPE or series-aware guards.

Inference: router feature quality is now the highest-leverage seam.

Recommendation: next run should ablate feature groups to identify which features
create lift, then design a risk policy that preserves the MAE gain while fixing
series-level regressions.
