# 045 - Z-Score Recent2000 Candidate

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-zscore-recent2000.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给 zscore 目标加一个新 LoRA 候选 | add adapter family | `recent2000` |
| 只用最近 2000 个训练窗口 | recency-window fine-tuning | `max_windows=2000` |
| 重新导出每个窗口预测 | prediction archive | `recent2000` archives |
| 把候选池从 2 个扩到 3 个 | candidate-pool expansion | zero-shot/full/recent2000 |
| 分别看 MAE 和 SMAPE router | multi-metric check | MAE + SMAPE |

通俗解释：

```text
上一轮 zscore 只有两个选择：

  zero-shot
  full LoRA

这轮我们加了第三个选择：

  recent2000 LoRA

它的意思是：

  不看全部历史训练窗口，
  只拿离当前 cut 最近的 2000 个窗口训练。

我们想测试：

  近期金融状态会不会比全历史更重要？
```

专业解释：

```text
This round expands the zscore adapter candidate pool with recent-window LoRA
adapters, then evaluates whether the larger pool improves chronological
no-leak routing under MAE and SMAPE metrics.
```

项目对应：

```text
new adapters:
  adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train4000
  adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train5000
  adapters/market-macro-realized-vol-20-zscore-h20-r4-step200-recent2000-train5500
```

## 2. What Is A Recent-Window Adapter?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只复习最近的题 | train on recent windows | `recent2000` |
| 少看老历史 | recency bias | skip older windows |
| 适合状态会变的市场 | regime-sensitive fine-tuning | market/macro risk |

通俗解释：

```text
假设你要预测明天市场。

你可以训练模型看：

  过去十几年的全部数据

也可以训练模型只看：

  最近一段时间的数据

金融市场有时候会换状态：

  低利率时代
  加息时代
  高波动时代
  流动性紧张时代

如果状态变了，太旧的数据可能会拖后腿。

recent2000 adapter 就是在测试：

  最近状态是不是更有用？
```

专业解释：

```text
A recent-window adapter is a LoRA adapter fine-tuned on a fixed-size trailing
training window instead of the full historical training span. It injects
recency bias into the adapter weights.
```

项目对应：

```text
cut4000:
  max_windows=2000
  skip_windows=2000

cut5000:
  max_windows=2000
  skip_windows=3000

cut5500:
  max_windows=2000
  skip_windows=3500
```

## 3. Candidate Pool

| 候选 | 通俗解释 | 专业解释 |
|---|---|---|
| `zero-shot` | 原版 TimesFM，不微调 | frozen base model |
| `full` | 用 full-window zscore LoRA | full-history adapter |
| `recent2000` | 用最近 2000 窗口 LoRA | recent-window adapter |

通俗解释：

```text
router 像一个选择器。

上一轮它只能在两个按钮里选：

  原版
  full LoRA

这轮给它第三个按钮：

  recent2000 LoRA

如果第三个按钮真的有用，
我们应该看到：

  oracle 空间变大
  no-leak router 也能吃到一部分收益
```

专业解释：

```text
Expanding the candidate pool increases the possible action space. The key test
is whether added oracle headroom survives chronological, causal routing.
```

项目对应：

```text
router rows:
  reports/router-rows-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json
```

## 4. Router Rows Result

| 指标 | 数值 |
|---|---:|
| rows | 1500 |
| full wins | 495 |
| recent2000 wins | 474 |
| zero-shot wins | 531 |
| fixed zero-shot MAE | 0.4908455409 |
| fixed full MAE | 0.4862193132 |
| fixed recent2000 MAE | 0.4868965619 |
| leaky oracle MAE | 0.4738384752 |
| leaky oracle MAE improvement vs zero-shot | 3.4648507971% |

通俗解释：

```text
加入 recent2000 以后，理论选择空间变大了。

1500 个窗口里：

  zero-shot 赢 531 次
  full 赢 495 次
  recent2000 赢 474 次

这说明三者都有用，
没有一个候选能一直赢。

但是注意：

  oracle 是作弊上限。

它知道每个窗口之后谁错得少。
真实部署时不知道。
```

专业解释：

```text
The expanded candidate pool increases post-hoc oracle headroom, but the label
distribution is fragmented across families. That raises the difficulty of
causal adapter selection.
```

项目对应：

```text
leaky_oracle_per_window.mae:
  0.4738384752

fixed_full.mae:
  0.4862193132
```

## 5. MAE Router Result

| 指标 | 数值 |
|---|---:|
| best chronological diagnostic | `knn_regret_no_series_k25` |
| best diagnostic routed MAE | 0.4838786046 |
| fixed full fallback routed MAE | 0.4836954085 |
| validation-gated routed MAE | 0.4836954085 |
| delta vs fallback | 0 |

通俗解释：

```text
用 MAE 看，router 还是没有过关。

它尝试学习：

  什么窗口该用 full？
  什么窗口该用 recent2000？
  什么窗口该回到 zero-shot？

但在时间顺序验证里，
它没有比固定用 full 更好。

所以系统继续 fail-closed：

  不切换
  固定 full
```

专业解释：

```text
Under MAE selection, the best learned chronological diagnostic still
underperformed the fixed full fallback. The validation gate correctly retained
the fallback policy.
```

项目对应：

```text
MAE output:
  reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-recent2000-h20-r4.json
```

## 6. SMAPE Router Result

| 指标 | 数值 |
|---|---:|
| best chronological diagnostic | `knn_regret_no_series_k100` |
| best diagnostic routed SMAPE | 0.9679270536 |
| fixed zero-shot fallback routed SMAPE | 0.9734419740 |
| validation-gated routed SMAPE | 0.9728359861 |
| delta vs fallback | 0.0006059880 |

通俗解释：

```text
SMAPE 是另一种误差看法。

MAE 问：

  平均差多少？

SMAPE 更像问：

  相对真实大小，错得多严重？

这轮在 SMAPE 上有一点小正信号。
router 比固定 zero-shot fallback 好一点点。

但这个收益太小，
而且只在 base-grid 上看到。

所以它是研究信号，
不是发布信号。
```

专业解释：

```text
The SMAPE-gated policy produced a small positive delta against zero-shot
fallback. This is directional evidence that the recent-window candidate adds
some relative-error diversity, but not enough for promotion.
```

项目对应：

```text
SMAPE output:
  reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-recent2000-smape-h20-r4.json
```

## 7. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 多训练一个 adapter 不等于系统更强 | more candidates can add noise | MAE still blocked |
| 候选多了，oracle 可能更好 | larger action space increases upper bound | oracle MAE improved |
| 真正难的是提前选对 | causal routing is the hard part | no-leak gate |
| 不同指标可能给不同答案 | metric-dependent utility | MAE vs SMAPE |

通俗解释：

```text
这轮最重要的理解：

  多一个 LoRA adapter，
  不等于模型马上更强。

它可能带来两件事：

  好处：多一种选择
  坏处：更难选对

如果 router 选不对，
多出来的 adapter 反而会制造噪音。

所以 LoRA 项目不是越训越好。
它是：

  训一个候选
  证明它在哪些窗口有用
  再证明系统能提前选中它
```

专业解释：

```text
Adapter diversity only becomes system quality when the serving policy can
select the right adapter causally. Otherwise, extra adapters remain diagnostic
oracles rather than production improvements.
```

项目对应：

```text
current MAE policy:
  not promotable

current SMAPE signal:
  small positive, needs more cuts
```

## 8. Current Verdict

Fact:

```text
Three zscore recent2000 LoRA adapters were trained for cuts 4000, 5000, and
5500.
```

Fact:

```text
Adding recent2000 increased leaky oracle MAE headroom:

  prior two-family oracle improvement: 2.1852417499%
  expanded three-family oracle improvement: 3.4648507971%
```

Fact:

```text
MAE no-leak routing still failed closed:

  validation-gated delta vs fixed full fallback: 0
```

Fact:

```text
SMAPE no-leak routing produced a small positive delta:

  validation-gated delta vs zero-shot fallback: 0.0006059880
```

Inference:

```text
recent2000 adds useful zscore candidate diversity, but not enough to promote a
MAE router. It may become useful if more cuts confirm the SMAPE signal.
```

Recommendation:

```text
Keep the new adapters as local experiment artifacts. Next, test whether
recent1500/recent3000 or expanded zscore cuts make the SMAPE signal stable
without weakening MAE.
```
