# 032 - Calibrated KNN-Regret Gating

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-calibrated-knn-regret.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有训练新 LoRA | no new adapter training | same archives |
| 只让 KNN-regret 参加选择 | isolated candidate set | `--candidate-set knn-regret` |
| 调它的开关阈值 | calibrated validation gate | `min_validation_lift` sweep |
| 看收益和风险是否更均衡 | aggregate/per-series tradeoff | MAE, SMAPE, series split |

通俗解释：

```text
上一轮我们发现：
线性的 regret-softmax 不如 KNN-regret。

所以这轮不再让 softmax、regret-softmax 混在一起竞争。

我们单独问一个问题：

如果只允许 KNN-regret 这种“找相似历史窗口”的 selector 参与，
然后重新调它的验证阈值，
结果会不会更稳？
```

专业解释：

```text
This round adds an explicit `knn-regret` candidate set and runs a calibrated
validation-gate sweep over the alignment-normalized router rows. The default
baseline candidate set remains unchanged.
```

项目对应：

```text
new candidate set:
  --candidate-set knn-regret

best aggregate:
  min_validation_lift = 0.0

best risk-balanced:
  min_validation_lift = 0.005
```

## 2. What Is KNN-Regret?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 找过去最像现在的窗口 | nearest-neighbor selection | `knn_regret_*` |
| 看那些窗口谁亏得少 | average neighbor family errors | regret scores |
| 不是训练一个大模型 | non-parametric local selector | no learned weights |
| 更像查案例库 | local memory-based routing | prediction archive |

通俗解释：

```text
KNN-regret 的想法很直：

当前窗口长得像过去哪些窗口？
过去那些窗口里，哪个 adapter 最少犯错？
那这次就选那个 adapter。

它不像 softmax 那样学一条线。
它更像：
  翻案例库
  找相似案例
  看当时谁表现好
```

专业解释：

```text
KNN-regret is a non-parametric local selector. It embeds runtime features,
retrieves nearest prior windows, averages each adapter family's realized error
over those neighbors, then selects the lowest-regret family.
```

项目对应：

```text
best diagnostic selector:
  knn_regret_no_series_k25

diagnostic MAE delta vs fallback:
  0.0004631997
```

## 3. What Does Calibration Mean Here?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不是什么时候都相信它 | validation-gated routing | prior validation cut |
| 赢够了才切过去 | thresholded switch rule | `min_validation_lift` |
| 太严格会错过机会 | over-gating | `0.01` failed |
| 太宽松可能冒险 | under-gating | `0.0` best aggregate |

通俗解释：

```text
selector 不是说想用就用。

我们加一个门：

如果 KNN-regret 在最近验证窗口赢了 fallback，
才允许它在下一个窗口接管。

这个门有一个阈值：

0.01:
  要赢很多才允许切换

0.005:
  赢一点点也可以，但还要有一点安全边际

0.0:
  只要不输就可以切换
```

专业解释：

```text
Calibration here means choosing the minimum validation lift required before the
router is allowed to override fixed `recent2000`. The calibrated gate is still
causal because it uses only prior cuts.
```

项目对应：

```text
tested thresholds:
  0.0
  0.005
  0.01
```

## 4. Results

Routed cuts only:

| Candidate set | Min validation | MAE delta | SMAPE delta | Positive / Negative series |
|---|---:|---:|---:|---:|
| `baseline` | 0.010 | 0.0002674001 | 0.0001307865 | 4 / 6 |
| `knn-regret` | 0.010 | -0.0000393438 | -0.0000238320 | not promoted |
| `knn-regret` | 0.000 | 0.0002705342 | 0.0004127764 | 6 / 4 |
| `knn-regret` | 0.005 | 0.0002687244 | 0.0005225268 | 7 / 3 |

通俗解释：

```text
最严格的 0.01 反而失败。

原因：
KNN-regret 是局部选择器。
它的优势可能不总是“大幅领先”，
而是很多地方小幅变好。

所以 0.01 太严，
把一些有用切换挡掉了。

0.0 总分最高。
0.005 总分几乎一样，但 series 更均衡。
```

专业解释：

```text
KNN-regret benefits from a lower validation gate. `min_validation_lift=0.0`
maximizes aggregate MAE delta, while `0.005` preserves almost the same aggregate
MAE delta and improves routed-series coverage to 7 positive vs 3 negative.
```

项目对应：

```text
best aggregate:
  knn-regret, min_validation_lift=0.0
  MAE delta = 0.0002705342

best risk-balanced:
  knn-regret, min_validation_lift=0.005
  MAE delta = 0.0002687244
  SMAPE delta = 0.0005225268
  series split = 7/3
```

## 5. Why This Is Better Than The Previous Round

| Previous issue | This round | Meaning |
|---|---|---|
| baseline had 4 / 6 series split | KNN mvl0.005 has 7 / 3 | broader positive coverage |
| loss-aware softmax lowered gated delta | KNN-only mvl0.005 slightly improves it | local selector is stronger |
| SMAPE lift was small | KNN mvl0.005 SMAPE delta is larger | secondary metric improved |

通俗解释：

```text
这轮不是大突破。

但它比上一轮有价值：

上一轮：
  新 selector 没有推进 frontier

这一轮：
  KNN-only + 合适阈值
  同时让 MAE、SMAPE、series 分布都稍微变好
```

专业解释：

```text
This is a small positive frontier update. The improvement is numerically tiny,
but it moves three surfaces in the right direction: aggregate MAE, SMAPE, and
per-series coverage.
```

项目对应：

```text
baseline MAE delta:
  0.0002674001

knn-regret mvl0.005 MAE delta:
  0.0002687244

extra MAE delta over baseline:
  0.0000013244
```

## 6. Why This Still Cannot Be Published

| Blocker | 通俗解释 | 专业解释 |
|---|---|---|
| delta 太小 | 多赢了一点点 | marginal frontier gain |
| 仍有 3 条 series 负收益 | 还会伤到部分市场序列 | heterogeneous downside |
| 仍靠 router 选择 | 发布前要更多 cut 稳定性 | future-cut reproducibility |

通俗解释：

```text
这轮可以说：
方向变好了。

但不能说：
模型已经可以发布。

因为多出来的收益非常小。
如果换一批未来数据，
这点差距可能消失。
```

专业解释：

```text
The KNN-regret calibrated policy is the current best risk-balanced router
candidate, but the extra lift over baseline is too small to satisfy promotion.
It should be treated as a research checkpoint, not a release artifact.
```

项目对应：

```text
promotion:
  blocked

current best risk-balanced candidate:
  knn-regret, min_validation_lift=0.005

next useful direction:
  per-series downside control on top of KNN-regret
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 多个 LoRA adapter 像多个专家 | adapter portfolio | full/recent windows |
| KNN-regret 像找相似病历 | local non-parametric selector | prior prediction archives |
| 阈值太严会错过好选择 | calibration matters | `min_validation_lift` |
| 小提升也要严谨记录 | frontier movement must be measured | run notes |

通俗解释：

```text
LoRA 微调后，
我们不是只拿一个 adapter 用到底。

我们有多个 adapter：
  长期历史型
  近期历史型
  原始 zero-shot

KNN-regret 做的是：
  看现在像过去哪种情况
  再选当时更靠谱的 adapter

这说明：
LoRA 项目的后半段，
很多价值来自“怎么选择 adapter”，
不是无限训练新 adapter。
```

专业解释：

```text
LoRA adapter specialization creates a model portfolio. KNN-regret routing is a
local model-selection layer over that portfolio. Calibration controls when the
selector is allowed to override the fixed fallback.
```

项目对应：

```text
current best feature surface:
  alignment-normalized

current best risk-balanced selector:
  knn-regret, min_validation_lift=0.005

still needed:
  stronger per-series downside control
```

## 8. Current Verdict

Fact: `knn-regret` candidate set with `min_validation_lift=0.0` gives the best
aggregate MAE delta: `0.0002705342`.

Fact: `knn-regret` with `min_validation_lift=0.005` gives the best risk-balanced
result: MAE delta `0.0002687244`, SMAPE delta `0.0005225268`, and `7/3`
positive/negative routed series.

Fact: `min_validation_lift=0.01` is too strict for KNN-regret and regresses MAE.

Inference: KNN-regret needs lighter validation gating than the mixed baseline
candidate set.

Recommendation: treat `knn-regret mvl0.005` as the current best risk-balanced
router checkpoint, but keep promotion blocked. The next useful step is adding
per-series downside control on top of this KNN-regret surface.
