# 044 - Z-Score Second Target Archive

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-zscore-second-target.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 换了第二个训练目标看效果 | second target validation | `realized_vol_20_zscore` |
| 没有重新训练权重 | reused existing adapters | zscore `train4000/5000/5500` |
| 补每个窗口的预测记录 | prediction archive export | `predictions-timesfm-...zscore...json` |
| 拼成 router 可以学习的数据 | router-row join | 1500 rows |
| 看 router 能不能真选对 | no-leak router evaluation | validation-gated KNN-regret |

通俗解释：

```text
上一轮我们把主目标 realized_vol_20 的 router 固定成 manifest。

这轮不是继续只盯着同一个目标。
我们拿第二个目标 zscore 来验一下：

  LoRA 在另一个金融目标上有没有用？
  旧脚本能不能支持第二目标？
  router 是不是只对主目标有效？

结果是：

  zscore full LoRA 有一点 MAE 价值；
  但 learned router 没有超过固定 full adapter。
```

专业解释：

```text
This round validates a second financial target by exporting aligned
prediction-level archives for existing zscore LoRA adapters and evaluating a
chronological no-leak router over zero-shot vs full adapter choices.
```

项目对应：

```text
target:
  realized_vol_20_zscore_train{cut}

cuts:
  4000, 5000, 5500

families:
  zero-shot, full

router rows:
  reports/router-rows-market-macro-realized-vol-20-zscore-h20-r4.json
```

## 2. What Is Z-Score?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把不同单位变成同一种尺子 | standardization | z = `(value - mean) / std` |
| 不看原始大小，看离正常值多远 | normalized deviation | train-window future stats |
| 不同金融序列更容易比较 | scale alignment | VIX/SP500/rates/FX/credit/oil |

通俗解释：

```text
假设两个人考试：

  A 考了 80 分
  B 考了 8 分

如果 A 满分是 100，B 满分是 10，
那 80 和 8 其实都可能是同一种水平。

金融时间序列也一样：

  VIX 的波动范围
  美债收益率的波动范围
  汇率的波动范围
  原油的波动范围

数值大小天然不一样。

z-score 就是把它们换成：

  现在比自己的正常水平高多少？
  现在比自己的正常水平低多少？
```

专业解释：

```text
Z-score normalization converts each value into a standardized distance from a
training-window mean measured in units of training-window standard deviation.
It reduces scale mismatch across heterogeneous market series.
```

项目对应：

```text
data/market/normalized-realized-vol-20-zscore-train4000.csv
data/market/normalized-realized-vol-20-zscore-train5000.csv
data/market/normalized-realized-vol-20-zscore-train5500.csv
```

## 3. Why Each Cut Has Its Own Field

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练到哪里，只能用哪里以前的均值方差 | cut-specific normalization | train4000/5000/5500 |
| 不能偷看未来再标准化 | avoid normalization leakage | one CSV per cut |
| 所以字段名也不同 | per-cut target field | `realized_vol_20_zscore_train{cut}` |

通俗解释：

```text
如果我们在 4000 这个切点做测试，
就只能用 4000 之前的数据算“正常水平”。

如果拿 5500 之后的数据也算进去，
那等于考试前偷看了答案分布。

所以 zscore 不是一个固定字段，
而是：

  train4000 有自己的 zscore
  train5000 有自己的 zscore
  train5500 有自己的 zscore
```

专业解释：

```text
The target field is cut-specific because normalization statistics must be
estimated only from the training window available before that evaluation cut.
This prevents future distribution information from leaking into test windows.
```

项目对应：

```text
--csv-template 'data/market/normalized-realized-vol-20-zscore-train{cut}.csv'
--field-template 'realized_vol_20_zscore_train{cut}'
```

## 4. What Is A Prediction Archive?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 每一道题都留下答案纸 | per-window prediction record | `records[]` |
| 不是只看总分 | not only aggregate metrics | 500 windows per cut |
| 后面 router 才能学 | supervision surface | `actual`, `predicted`, runtime features |

通俗解释：

```text
只有总分不够。

比如：

  zero-shot 平均分 80
  LoRA 平均分 81

这只能说明 LoRA 平均更好一点。

但 router 想学的是：

  哪些题 zero-shot 更好？
  哪些题 LoRA 更好？
  看题目前面的信息，能不能提前猜出来？

所以必须保存每个窗口的预测和真实值。
这就是 prediction archive。
```

专业解释：

```text
A prediction archive stores aligned per-window forecasts, actuals, metrics,
and runtime features. It is the interface between model evaluation and adapter
selection policy training.
```

项目对应：

```text
zero-shot archives:
  predictions-timesfm-market-macro-realized-vol-20-zscore-h20-r4-zero-shot-holdout500-skip{cut}.json

full adapter archives:
  predictions-timesfm-market-macro-realized-vol-20-zscore-h20-r4-full-holdout500-skip{cut}.json
```

## 5. What The Router Rows Showed

| 指标 | 数值 |
|---|---:|
| rows | 1500 |
| cuts | 4000, 5000, 5500 |
| full wins | 814 |
| zero-shot wins | 686 |
| fixed full MAE | 0.4862193132 |
| fixed zero-shot MAE | 0.4908455409 |
| leaky oracle MAE | 0.4801193792 |
| leaky oracle MAE improvement vs zero-shot | 2.1852417499% |

通俗解释：

```text
1500 道题里：

  LoRA full 赢了 814 道
  zero-shot 赢了 686 道

所以 LoRA 不是碾压。
它只是略多时候赢。

如果有一个神仙提前知道每道题谁会赢，
MAE 可以到 0.480119。

但这个神仙是 leaky oracle。
它用了未来真实误差，所以不能上线。
它只能告诉我们：理论上有选择空间。
```

专业解释：

```text
The joined router rows show measurable but modest adapter-selection headroom.
The oracle improvement is an upper bound because it uses post-hoc labels.
No production policy may use this information at inference time.
```

项目对应：

```text
report:
  reports/router-rows-market-macro-realized-vol-20-zscore-h20-r4.json

guardrail:
  runtime_features exclude actuals, errors, and best-family labels
```

## 6. What The No-Leak Router Showed

| 指标 | 数值 |
|---|---:|
| best chronological diagnostic | `knn_regret_no_series_k100` |
| best diagnostic routed MAE | 0.4849968548 |
| fixed full fallback routed MAE | 0.4836954085 |
| validation-gated routed MAE | 0.4836954085 |
| delta vs fallback | 0 |

通俗解释：

```text
我们让 router 只看过去的 cut。

它不能看当前测试答案。
它只能根据以前经验决定：

  这次用 zero-shot？
  还是用 full LoRA？

结果：

  router 没有比一直用 full 更好。

所以系统选择 fail-closed：

  不切换
  不冒险
  继续用固定 full
```

专业解释：

```text
Under chronological validation, learned KNN-regret policies did not clear the
fixed full fallback. The validation-gated policy therefore selected the
fallback, yielding zero delta against fallback and preventing promotion.
```

项目对应：

```text
command:
  evaluate_prediction_router.py

fallback:
  full

candidate_set:
  knn-regret

promotion:
  blocked
```

## 7. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 训练出 adapter 不等于项目成功 | adapter weights are not enough | zscore full exists |
| 平均更好一点也不等于可以上线 | aggregate gain is insufficient | small MAE lift |
| router 想上线必须不用未来答案也赢 | causal policy validation | no-leak router |
| 如果 router 不赢，就固定用更稳的 adapter | fail-closed serving | fixed full fallback |

通俗解释：

```text
LoRA 的完整流程不是：

  训练完 -> 好了

而是：

  训练 adapter
  跑 zero-shot 对比
  跑 naive 对比
  导出每个窗口预测
  拼 router rows
  检查有没有未来泄漏
  训练/验证 router
  如果 router 不赢，就不要上线 router

这轮 zscore 教的是：

  LoRA adapter 有价值，
  但 router 还没有价值。
```

专业解释：

```text
LoRA specialization must be evaluated at both the weight level and the serving
policy level. A positive adapter does not imply a promotable dynamic router.
The router needs causal, chronological gains over a fixed fallback.
```

项目对应：

```text
adapter-level result:
  full LoRA has small MAE advantage over zero-shot

serving-policy result:
  learned router blocked

current safe behavior:
  fixed full fallback for zscore
```

## 8. Current Verdict

Fact:

```text
The zscore target now has aligned prediction archives and 1500 no-leak-checked
router rows across cuts 4000, 5000, and 5500.
```

Fact:

```text
Fixed full LoRA beats zero-shot on base-grid MAE:

  full:      0.4862193132
  zero-shot: 0.4908455409
```

Fact:

```text
The no-leak learned router did not beat fixed full fallback:

  validation-gated delta vs fallback: 0
```

Inference:

```text
realized_vol_20_zscore is useful as a second financial target validation
surface, but not yet as a promoted dynamic-router surface.
```

Recommendation:

```text
Keep zscore as a secondary adapter target. Next, either add more zscore cuts or
train recent-window zscore adapters before trying router promotion again.
```
