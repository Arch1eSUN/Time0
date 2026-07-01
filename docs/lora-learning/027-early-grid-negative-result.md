# 027 - Early Grid Negative Result

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-early-grid.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 在更早的位置加两次考试 | earlier chronological cut grid | `--grid early` |
| 重新训练缺失 adapter | train new LoRA adapters | cut3000/cut3250 |
| 重新导出预测档案 | prediction archive export | 10 new archives |
| 重新做 no-leak router 评估 | causal router validation | 5500 joined rows |

通俗解释：

```text
上一轮的问题是：
cut4000 之前只有很少的历史 validation 证据。

所以这轮我们往更早的位置加了两个 cut：

3000
3250

这样 router 在到 cut4000 之前，
可以多看到几次历史小考。
```

专业解释：

```text
We extended the chronological grid from the previous expanded grid by adding
earlier cut points 3000 and 3250. This created additional no-leak training and
validation windows before cut4000.
```

项目对应：

```text
new grid:
  --grid early

new cuts:
  3000
  3250

new LoRA adapters:
  2 cuts * 4 LoRA families = 8 adapters

new prediction archives:
  2 cuts * 5 families = 10 archives
```

## 2. What Is A Rolling Cut Grid?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把时间线切成多次考试 | chronological cut points | `cuts` |
| 每个 cut 前面训练，后面考试 | train-before, evaluate-after | no leakage |
| cut 越多，router 学到的历史越多 | more validation supervision | 5500 rows |
| 但 cut 多不代表一定更好 | more data can expose instability | negative result |

通俗解释：

```text
我们不是随机切数据。

时序模型必须按时间切：

过去训练
未来测试

如果反过来，
就等于偷看答案。

rolling cut grid 就是把这个“过去 -> 未来”的考试重复很多次。
```

专业解释：

```text
A rolling cut grid is a chronological evaluation scaffold. Each cut defines a
training region before the cut and a holdout region after the cut. Router
decisions for a target cut may only use earlier cuts.
```

项目对应：

```text
expanded grid:
  3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500

early grid:
  3000, 3250, 3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500
```

## 3. What Did We Train?

| Cut | Family | Training window |
|---:|---|---|
| 3000 | full | first 3000 windows |
| 3000 | recent1500 | windows 1500-3000 |
| 3000 | recent2000 | windows 1000-3000 |
| 3000 | recent3000 | first 3000 windows |
| 3250 | full | first 3250 windows |
| 3250 | recent1500 | windows 1750-3250 |
| 3250 | recent2000 | windows 1250-3250 |
| 3250 | recent3000 | windows 250-3250 |

通俗解释：

```text
full:
  从最早开始一直学到 cut。

recent1500:
  只学 cut 前最近 1500 个窗口。

recent2000:
  只学 cut 前最近 2000 个窗口。

recent3000:
  只学 cut 前最近 3000 个窗口。
```

专业解释：

```text
Each adapter family is a different data-window policy over the same TimesFM 2.5
base model and LoRA hyperparameters. This isolates the effect of chronological
training-window selection rather than changing rank, alpha, or target field.
```

项目对应：

```text
LoRA rank: r=4
LoRA alpha: 8
steps: 200
target: realized_vol_20
fallback: recent2000
```

## 4. What Did The New Early Cuts Show?

Fixed-family MAE by cut:

| Cut | Best fixed family | zero-shot | recent1500 | recent2000 | recent3000 |
|---:|---|---:|---:|---:|---:|
| 3000 | recent1500 | 0.1137512872 | 0.1117234973 | 0.1124094573 | 0.1130174788 |
| 3250 | recent3000 | 0.0852291421 | 0.0863861013 | 0.0849447790 | 0.0848719414 |

通俗解释：

```text
3000 这个位置：
recent1500 最好。

3250 这个位置：
recent3000 最好。

这说明：
“哪个 adapter 最好”确实会随时间变化。

但这还不等于 router 能安全学会怎么选。
```

专业解释：

```text
The early cuts increase adapter-selection diversity: different fixed families
win at different cut points. This confirms routing headroom exists, but it does
not prove a no-leak router can exploit that headroom.
```

项目对应：

```text
joined early rows:
  5500

fixed recent2000 mean MAE:
  0.0938765687

leaky oracle MAE:
  0.0888025342

leaky oracle improvement vs zero-shot:
  6.992092%
```

## 5. What Did The Router Do?

Routed cuts only:

| Policy | MAE | Improvement vs zero-shot | Delta vs fixed recent2000 | Verdict |
|---|---:|---:|---:|---|
| fixed recent2000 fallback | 0.0920232799 | 1.738276% | 0.0000000000 | safe baseline |
| best chronological diagnostic | 0.0919644635 | 1.801080% | 0.0000588164 | not fail-closed |
| validation-gated | 0.0921934286 | 1.556593% | -0.0001701487 | failed |
| series-guarded | 0.0921456132 | 1.607650% | -0.0001223333 | failed |
| series-risk-penalized | 0.0921345873 | 1.619423% | -0.0001113074 | failed |

通俗解释：

```text
最安全的方案还是 recent2000。

有一个“诊断用”的 router 看起来略好，
但它不是我们能直接发布的策略。

为什么？

因为我们需要一个 fail-closed gate：
只有当历史验证明确证明 learned router 更好，
才允许它接管。

这轮的 gate 没做到。
它一接管，整体反而低于 recent2000。
```

专业解释：

```text
The best chronological diagnostic policy (`knn_regret_no_series_k25`) slightly
beats the fixed fallback on routed cuts, but the deployable validation-gated
policies regress. This means selection headroom remains, while the causal
promotion rule is still unreliable.
```

项目对应：

```text
best diagnostic:
  knn_regret_no_series_k25

best deployable/fail-closed result:
  fixed recent2000 fallback

publication:
  blocked
```

## 6. Why More Cuts Did Not Fix It

| Problem | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| 多了证据，但证据不稳定 | 小考变多，但规律还是会变 | non-stationary regime evidence | financial time series |
| learned router 有时赢很多，有时输很多 | 不是稳定优势 | high variance routing policy | cut4250/cut5250 |
| gate 会放行坏切换 | 护栏判断错 | validation transfer failure | negative delta |
| DFF 变成主要负贡献 | 原来的正贡献反转 | regime-specific concentration risk | early grid DFF |

Important cut behavior:

| Cut | validation-gated delta vs fallback | Selected config |
|---:|---:|---|
| 3750 | 0.0013651981 | softmax |
| 4000 | 0.0024793740 | softmax |
| 4250 | -0.0033224244 | softmax |
| 4750 | -0.0001914564 | knn_regret_series_k100 |
| 5250 | -0.0020321786 | knn_regret_series_k25 |

通俗解释：

```text
router 不是一直错。

它在 3750 和 4000 是有明显正收益的。

真正的问题是：
它在 4250 和 5250 输得太大。

这就像一个策略：
平时小赚，
偶尔大亏。

这种策略不能发布。
```

专业解释：

```text
The router's expected gain is dominated by tail failures. More early cuts
increase supervision, but they also reveal that the current validation gate does
not transfer reliably across regimes.
```

项目对应：

```text
largest negative routed series:
  DFF
  SP500
  DCOILWTICO

series-risk policy reduced damage:
  validation-gated delta: -0.0001701487
  series-risk delta:      -0.0001113074

but still below fallback:
  yes
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 多训练不等于更强 | more adapters are not automatic improvement | early grid negative result |
| 多验证不等于可发布 | validation quantity is not validation quality | gate failed |
| 最重要是不能偷看答案 | causal selection is stricter than oracle | no-leak router |
| 负结果能避免错发模型 | negative evidence prevents overclaiming | publication blocked |

通俗解释：

```text
我们这轮真的训练了新 adapter。
也真的扩展了数据。

但结果不是：
“训练更多，所以模型更强。”

结果是：
“训练更多后，我们更清楚地看到当前 router 不稳定。”

这很重要。

如果我们只看 leaky oracle，
会以为有接近 7% 的提升空间。

但可发布模型必须 no-leak。
no-leak gate 失败，就不能发布。
```

专业解释：

```text
LoRA experiments require separation between adapter capacity, evaluation
coverage, oracle headroom, and deployable selection policy. This run improves
coverage, but the deployable policy still fails the fallback comparison.
```

项目对应：

```text
adapter training:
  succeeded

prediction archive:
  succeeded

router evidence:
  negative for deployable policies

project status:
  continue research
  no release
```

## 8. Current Verdict

Fact: the early grid created 5500 aligned router rows across 11 chronological
cuts.

Fact: fixed `recent2000` remains the best deployable policy in this run.

Fact: the best chronological diagnostic slightly beats fallback, but the
fail-closed validation-gated policies underperform fallback.

Inference: the next bottleneck is not more hard gates. The bottleneck is router
feature quality and regime detection.

Recommendation: stop expanding cut density for now. The next controlled step
should add richer no-leak runtime features for regime/risk detection, then rerun
the same early grid.
