# 046 - Z-Score Candidate Pool Risk

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-zscore-all-recent.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把 zscore 候选池补完整 | complete recent-window family sweep | `recent1500/recent2000/recent3000` |
| 新训练 6 个 adapters | train additional LoRA adapters | 3 cuts x 2 families |
| 导出逐窗口预测 | prediction archives | 6 new archives |
| 拼五候选 router rows | expanded action space | 1500 rows |
| 同时看 MAE 和 SMAPE | multi-metric router check | no-leak evaluation |

通俗解释：

```text
上一轮 zscore 已经有：

  zero-shot
  full
  recent2000

这轮我们补上：

  recent1500
  recent3000

这样 zscore 的 base-grid 候选池就变成：

  zero-shot
  full
  recent1500
  recent2000
  recent3000

问题是：

  候选更多以后，系统会不会更强？
```

专业解释：

```text
This round completes the base zscore recent-window adapter family and evaluates
whether the larger candidate pool improves chronological no-leak routing.
```

项目对应：

```text
new families:
  recent1500
  recent3000

router rows:
  reports/router-rows-market-macro-realized-vol-20-zscore-all-recent-h20-r4.json
```

## 2. More Adapters Are Not Free

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 多几个按钮，不等于更会选 | larger action space can increase error | 5 families |
| 神仙选择会更强 | oracle headroom increases | leaky oracle |
| 真实 router 可能更难 | causal selection becomes harder | no-leak gate |

通俗解释：

```text
想象你去考试。

原来每道题只有两个选项：

  A
  B

现在变成五个选项：

  A
  B
  C
  D
  E

如果你知道答案，五个选项当然更好。
因为正确答案更可能在里面。

但如果你不知道答案，
五个选项反而更难选。

LoRA adapter pool 也是这样：

  候选越多，理论上限越高；
  但 router 更容易选错。
```

专业解释：

```text
Adding adapters increases the policy action space. This usually raises the
post-hoc oracle upper bound, but it also increases the sample complexity and
mis-selection risk for causal routing.
```

项目对应：

```text
candidate pool:
  2 families -> 3 families -> 5 families

core question:
  does no-leak routing capture the new oracle headroom?
```

## 3. Router Rows Result

| 指标 | 数值 |
|---|---:|
| rows | 1500 |
| zero-shot wins | 379 |
| full wins | 328 |
| recent1500 wins | 419 |
| recent2000 wins | 197 |
| recent3000 wins | 177 |
| fixed zero-shot MAE | 0.4908455409 |
| fixed full MAE | 0.4862193132 |
| fixed recent1500 MAE | 0.4929371551 |
| fixed recent2000 MAE | 0.4868965619 |
| fixed recent3000 MAE | 0.4872102193 |
| leaky oracle MAE improvement vs zero-shot | 4.9413373547% |
| leaky oracle SMAPE improvement vs zero-shot | 3.5249489648% |

通俗解释：

```text
五个候选里，没有一个总是赢。

1500 个窗口里：

  recent1500 赢最多
  zero-shot 也赢很多
  full 仍然是最好的固定 MAE

这说明：

  有选择空间，
  但选择问题变难了。
```

专业解释：

```text
The expanded pool increases oracle headroom and spreads labels across all
families. Fixed-family MAE still favors full, while post-hoc labels favor a
heterogeneous per-window selection.
```

项目对应：

```text
best fixed MAE:
  full

best fixed SMAPE:
  recent1500

best possible oracle:
  leaky, not deployable
```

## 4. MAE Result

| 指标 | 数值 |
|---|---:|
| best chronological diagnostic | `knn_regret_no_series_k100` |
| best diagnostic routed MAE | 0.4848657808 |
| fixed full fallback routed MAE | 0.4836954085 |
| validation-gated routed MAE | 0.4836954085 |
| delta vs fallback | 0 |

通俗解释：

```text
用 MAE 看，五候选没有让 router 过关。

虽然神仙 oracle 更强，
但真实 router 不能偷看答案。

它用过去 cut 学到的选择规则，
在验证时没有超过固定 full。

所以系统继续保持：

  固定 full
  不动态切换
```

专业解释：

```text
The expanded candidate pool did not improve MAE routing. The validation gate
retained the fixed full fallback because learned policies failed prior-cut
validation.
```

项目对应：

```text
MAE output:
  reports/no-leak-prediction-router-market-macro-realized-vol-20-zscore-all-recent-mae-h20-r4.json
```

## 5. SMAPE Result

| 对比 | Fallback SMAPE | Routed SMAPE | Delta vs fallback |
|---|---:|---:|---:|
| fallback = recent1500 | 0.9715985846 | 0.9713667758 | 0.0002318088 |
| fallback = zero-shot | 0.9734419740 | 0.9751426728 | -0.0017006988 |

通俗解释：

```text
SMAPE 的结果更微妙。

如果拿 recent1500 当保底：

  router 好一点点。

但如果拿 zero-shot 当保底：

  router 反而更差。

这说明这个 SMAPE 信号不稳。
它不是一个干净的发布信号。
```

专业解释：

```text
The SMAPE result is fallback-sensitive. A small positive delta against
recent1500 does not survive the zero-shot fallback comparison, so it should not
be promoted.
```

项目对应：

```text
SMAPE recent1500 fallback:
  positive but tiny

SMAPE zero-shot fallback:
  negative
```

## 6. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不要因为候选多就兴奋 | upper bound is not deployable quality | oracle vs router |
| 真正难点是选择器 | serving policy is the bottleneck | no-leak router |
| 指标不同，答案不同 | metric-dependent promotion | MAE vs SMAPE |
| fallback 选错会误导判断 | baseline sensitivity | recent1500 vs zero-shot |

通俗解释：

```text
这轮最重要的教训：

  候选池变大，
  不是免费的升级。

它会让“理论最优”变强，
但也会让真实 router 更难。

所以我们不能说：

  多训几个 LoRA，模型就更强了。

只能说：

  多训几个 LoRA，给了系统更多可能性；
  但必须证明 router 能提前选对。
```

专业解释：

```text
Adapter-pool expansion creates optionality. Optionality becomes model quality
only if a causal serving policy can exploit it under stable validation
surfaces.
```

项目对应：

```text
current zscore status:
  useful research surface
  not a promotable router
```

## 7. Current Verdict

Fact:

```text
Six zscore adapters were trained for recent1500/recent3000 across cuts 4000,
5000, and 5500.
```

Fact:

```text
The five-family candidate pool increased oracle headroom:

  MAE oracle improvement vs zero-shot:   4.9413373547%
  SMAPE oracle improvement vs zero-shot: 3.5249489648%
```

Fact:

```text
MAE no-leak routing still failed closed:

  validation-gated delta vs fixed full fallback: 0
```

Fact:

```text
SMAPE no-leak routing is fallback-sensitive:

  vs recent1500 fallback: +0.0002318088
  vs zero-shot fallback:  -0.0017006988
```

Inference:

```text
The wider zscore adapter pool adds theoretical upside but not stable deployable
quality yet.
```

Recommendation:

```text
Stop widening the zscore base-grid pool for now. Next, either add more cuts for
stability testing or design a stricter router guard that blocks fallback-
sensitive SMAPE wins.
```
