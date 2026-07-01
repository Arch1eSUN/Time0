# 031 - Loss-Aware Selector

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-loss-aware-selector.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有训练新 LoRA | no new adapter training | same prediction archives |
| 训练一个新的选择器 | supervised selector candidate | `regret_softmax_*` |
| 目标不是猜“谁第一” | loss-aware objective | regret matrix |
| 继续不偷看未来 | chronological no-leak evaluation | `--candidate-set loss-aware` |

通俗解释：

```text
上一轮我们发现：
手调选择规则已经没有太大提升空间。

所以这轮换方向：
不再继续调阈值，
而是让 selector 学一个更细的目标。

以前普通 softmax 学的是：
  这一窗口谁是第一名？

这轮 loss-aware selector 学的是：
  选错每个 adapter 会亏多少？
```

专业解释：

```text
This round adds an opt-in loss-aware candidate set to the no-leak prediction
router. The new regret-softmax selector trains on continuous per-family regret
instead of one-hot best-family labels.
```

项目对应：

```text
changed script:
  experiments/timesfm-lora/scripts/evaluate_prediction_router.py

new candidate set:
  --candidate-set loss-aware

new candidates:
  regret_softmax_raw_no_series
  regret_softmax_relative_no_series
  regret_softmax_raw_series
  regret_softmax_relative_series
```

## 2. What Is A Supervised Selector?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| selector 是调度员 | model-selection policy | router candidate |
| supervised 是有答案训练 | train with labels/errors | prior cut labels |
| no-leak 是只看过去答案 | causal chronological split | train prior cuts only |
| 目标是未来选对 adapter | out-of-sample adapter selection | routed cuts |

通俗解释：

```text
我们有 5 个预测来源：

zero-shot
full
recent1500
recent2000
recent3000

selector 的工作是：
看到当前窗口的 runtime features，
决定用哪个预测来源。

supervised selector 的意思是：
我们用过去窗口中“真实哪个更准”的记录，
训练这个 selector。

但它不能看当前未来窗口的答案。
只能用 prior cuts。
```

专业解释：

```text
A supervised selector is a learned model-selection Module. It maps runtime
features to a selected forecasting family, using historical labeled examples
from prior chronological cuts.
```

项目对应：

```text
training data:
  prior cuts only

evaluation data:
  current future cut

guardrail:
  current cut labels are used only after selection for offline scoring
```

## 3. One-Hot Label vs Regret Objective

| Objective | 通俗解释 | 专业解释 | 风险 |
|---|---|---|---|
| one-hot best family | 只学谁第一 | cross-entropy on argmin label | 不知道错得多严重 |
| raw regret | 学选错会亏多少 MAE | minimize expected raw regret | 大波动 series 可能主导 |
| relative regret | 学相对亏多少 | regret normalized by row mean error | 可能低估大错误 |

通俗解释：

```text
假设一场比赛：

A 分数 99
B 分数 98
C 分数 40

普通分类只知道：
  A 是第一名

但它不知道：
  选 B 其实也很好
  选 C 才是真的灾难

regret objective 想学的是：
  选 B 少亏一点
  选 C 亏很多
```

专业解释：

```text
One-hot classification collapses the full error vector into a single class
label. Regret training preserves the error margin between families and optimizes
expected regret under the selector probability distribution.
```

项目对应：

```text
one-hot:
  softmax
  softmax_series

loss-aware:
  regret_softmax_raw_*
  regret_softmax_relative_*

nearest-neighbor regret baseline:
  knn_regret_* 
```

## 4. What Changed In Code?

| Module | 通俗解释 | 专业解释 |
|---|---|---|
| `CandidateConfig` | 给 selector 增加一种类型 | adds `regret_scale` |
| `regret_matrix` | 算每个选择会亏多少 | per-row family regret tensor |
| `fit_regret_softmax` | 用 regret 训练线性 selector | expected-regret gradient |
| `--candidate-set` | 防止旧实验被污染 | opt-in candidate surface |

通俗解释：

```text
最重要的不是加了新模型。

最重要的是：
旧命令默认还是旧行为。

如果不写：
  --candidate-set loss-aware

那上一轮的结果仍然可复现。
```

专业解释：

```text
The new candidates are opt-in through `--candidate-set loss-aware`. The default
candidate set remains `baseline`, preserving prior report reproducibility.
```

项目对应：

```text
baseline check:
  validation_gated delta = 0.0002674001

loss-aware run:
  validation_gated delta = 0.0002366568
```

## 5. Results

Routed cuts only, MAE:

| Selector | MAE | Delta vs fallback | Selected counts |
|---|---:|---:|---|
| `knn_regret_no_series_k25` | 0.0915600802 | 0.0004631997 | full 551, recent1500 969, recent2000 1231, recent3000 906, zero-shot 1343 |
| `knn_regret_series_k25` | 0.0916377215 | 0.0003855584 | full 572, recent1500 1092, recent2000 1067, recent3000 907, zero-shot 1362 |
| `knn_regret_no_series_k100` | 0.0917805651 | 0.0002427147 | full 583, recent1500 881, recent2000 1318, recent3000 849, zero-shot 1369 |
| `knn_regret_series_k50` | 0.0917974896 | 0.0002257903 | full 654, recent1500 1063, recent2000 1122, recent3000 802, zero-shot 1359 |
| `regret_softmax_raw_no_series` | 0.0918167750 | 0.0002065049 | full 1617, recent1500 799, recent2000 937, recent3000 423, zero-shot 1224 |
| `regret_softmax_raw_series` | 0.0918311609 | 0.0001921190 | full 1774, recent1500 806, recent2000 872, recent3000 443, zero-shot 1105 |
| `regret_softmax_relative_series` | 0.0918442535 | 0.0001790263 | full 1431, recent1500 688, recent2000 978, recent3000 606, zero-shot 1297 |
| `softmax` | 0.0919876795 | 0.0000356004 | full 110, recent1500 1809, recent2000 709, recent3000 763, zero-shot 1609 |

Gated policy comparison:

| Candidate set | Validation-gated MAE | Delta vs fallback |
|---|---:|---:|
| `baseline` | 0.0917558798 | 0.0002674001 |
| `loss-aware` | 0.0917866231 | 0.0002366568 |

通俗解释：

```text
regret-softmax 比普通 softmax 强。

但它没有超过 KNN-regret。

而且当我们把它加入 gated policy 的候选池后，
整体 gated 结果还比 baseline 略低。

所以这轮不能算成功推进。
```

专业解释：

```text
Regret-softmax improves over one-hot softmax, but it does not improve the
diagnostic frontier or the validation-gated policy frontier. The best diagnostic
remains `knn_regret_no_series_k25`.
```

项目对应：

```text
best old diagnostic:
  knn_regret_no_series_k25

best new regret-softmax:
  regret_softmax_raw_no_series

promotion:
  still blocked
```

## 6. Why This Did Not Promote

| 观察 | 通俗解释 | 专业解释 |
|---|---|---|
| regret-softmax 正收益 | 新目标有信号 | loss-aware objective is not useless |
| 但低于 KNN-regret | 线性模型表达力不够 | linear boundary underfits local regimes |
| gated policy 下降 | 多一个候选反而误导 gate | validation winner may not transfer |
| series 仍是 4 / 6 | 稳定性没解决 | heterogeneous downside remains |

通俗解释：

```text
这轮不是完全失败。

它证明：
  “看错得多严重”比“只猜第一名”更合理。

但它也证明：
  一个线性 softmax selector 不够强。

它会在某些 validation cut 上看起来不错，
但到未来 cut 不一定延续。
```

专业解释：

```text
The regret objective improved the linear selector relative to one-hot softmax,
but the learned linear decision surface did not generalize better than local
nearest-neighbor regret. This suggests the bottleneck is not just the training
target; it is also selector capacity and validation transfer.
```

项目对应：

```text
loss-aware attribution:
  positive routed series = 4
  negative routed series = 6

top positive:
  DFF
  DGS2
  DEXUSEU

top negative:
  VIXCLS
  SP500
  DCOILWTICO
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 微调后还要会选择 | adapter portfolio needs selection | router layer |
| 训练目标很重要 | objective design changes behavior | best-label vs regret |
| 指标好看不等于能发布 | validation transfer matters | no-leak future cuts |
| 负结果也有价值 | eliminates weak branch | no more linear regret-softmax |

通俗解释：

```text
LoRA 让 TimesFM 产生多个“偏向”：

长期历史偏向
近期窗口偏向
zero-shot 原始偏向

selector 决定什么时候用哪个偏向。

这轮告诉我们：
selector 不能只学“谁第一”，
但也不能只靠一个简单线性模型。
```

专业解释：

```text
Adapter specialization turns forecasting into a two-level system: base
forecast generation and causal adapter selection. The selector objective must
capture loss severity, but the selector class also needs enough locality to
handle regime-specific behavior.
```

项目对应：

```text
keep:
  opt-in candidate-set infrastructure
  regret objective as a diagnostic

do not promote:
  regret_softmax

next direction:
  local/ensemble selector or calibrated gating over KNN-regret
```

## 8. Current Verdict

Fact: baseline candidate set remains reproducible with `validation_gated` delta
`0.0002674001`.

Fact: `loss-aware` candidate set reaches `validation_gated` delta
`0.0002366568`, which is lower than baseline.

Fact: the best regret-softmax diagnostic is `regret_softmax_raw_no_series` with
delta `0.0002065049`, below `knn_regret_no_series_k25` at `0.0004631997`.

Fact: loss-aware attribution still has only `4/10` positive routed series.

Inference: loss-aware objective design is directionally useful, but linear
regret-softmax is not the selector class that unlocks this router.

Recommendation: keep the opt-in infrastructure, record this as a negative
selector result, and move next toward calibrated KNN-regret gating or a
nonlinear/local selector with explicit per-series downside control.
