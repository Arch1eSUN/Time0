# 030 - Policy Sweep And Risk Tradeoff

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-policy-sweep.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有重新训练 LoRA | no new adapter training | existing prediction archives |
| 只调“选择规则” | router policy sweep | `sweep_router_policies.py` |
| 看哪种选择方式更稳 | policy evaluation | attribution summaries |
| 继续防止偷看答案 | no-leak evaluation | pre-holdout validation only |

通俗解释：

```text
我们手里已经有多个 TimesFM/LoRA 预测版本：

zero-shot
full
recent1500
recent2000
recent3000

现在问题不是：
  继续训练哪个 adapter？

而是：
  到了一个新窗口，router 应该选谁？

这轮就是拿同一批预测结果，
反复换“选择规则”，
看哪条规则最靠谱。
```

专业解释：

```text
This round performs a router policy sweep over the existing
alignment-normalized router rows. The adapter predictions, labels, runtime
features, and chronological split stay fixed. Only the selection policy
thresholds change.
```

项目对应：

```text
new script:
  experiments/timesfm-lora/scripts/sweep_router_policies.py

input rows:
  reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

output report:
  reports/router-policy-sweep-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

configs tested:
  27
```

## 2. What Is A Policy Sweep?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 同一辆车试不同驾驶规则 | evaluate multiple decision policies | same router rows |
| 不换发动机 | model/adapters unchanged | no new LoRA weights |
| 只换什么时候转弯 | threshold/policy changes | validation gates |
| 看哪条规则少出事 | risk/return tradeoff | MAE delta and series count |

通俗解释：

```text
你可以把 LoRA adapter 当作几个司机：

司机 A：比较保守
司机 B：最近路况熟
司机 C：长期经验多

router 是调度员。

policy 是调度员的规则：

  如果司机 B 过去表现好，就派司机 B
  如果某条路上司机 B 经常翻车，就别派司机 B
  如果证据不够，就用默认司机 recent2000

policy sweep 就是：
  不训练新司机
  只测试不同调度规则
```

专业解释：

```text
A policy sweep evaluates multiple deterministic selection policies over the
same prediction-level archive. It is useful when the model portfolio already
exists and the open question is how to choose among models without leaking
future labels.
```

项目对应：

```text
model portfolio:
  zero-shot, full, recent1500, recent2000, recent3000

fallback:
  recent2000

selection metric:
  MAE
```

## 3. The Three Policy Knobs

| Knob | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| `min_validation_lift` | 整体至少要赢多少才允许换 | aggregate validation threshold | 0, 0.005, 0.01 |
| `min_series_validation_lift` | 这条 series 自己至少要赢多少 | per-series validation threshold | 0, 0.001 |
| `series_risk_decay` | 旧证据打几折 | recency weighting decay | 0.05, 0.1, 0.25 |

### 3.1 `min_validation_lift`

通俗解释：

```text
这像一个总开关：

如果 router 在过去验证集上没有明显赢，
那它就不能乱选，
继续用 fallback recent2000。
```

专业解释：

```text
`min_validation_lift` is the minimum aggregate validation improvement required
before the router is allowed to override the fallback family.
```

项目对应：

```text
best aggregate:
  validation_gated
  min_validation_lift = 0.01
```

### 3.2 `min_series_validation_lift`

通俗解释：

```text
总成绩好，不代表每个 series 都好。

比如：
  DFF 大赚
  SP500 小亏
  DGS10 小亏

总分可能还是赢。

但如果我们要发布模型，
不能只靠一个 series 拉高总成绩。
所以要看每条 series 自己有没有赢。
```

专业解释：

```text
`min_series_validation_lift` requires the router to have non-negative or
positive validation evidence for the same series before it can override the
fallback on that series.
```

项目对应：

```text
series-aware policies:
  series_guarded
  series_risk_penalized
```

### 3.3 `series_risk_decay`

通俗解释：

```text
金融市场会变。

很久以前的验证结果不能和最近的验证结果一样重要。

decay 越小：
  越相信最近结果

decay 越大：
  越把旧结果也算进去
```

专业解释：

```text
`series_risk_decay` controls how quickly older validation cuts lose influence
inside the recency-weighted series-risk policy.
```

项目对应：

```text
tested decay:
  0.05
  0.10
  0.25
```

## 4. Policy Sweep Results

Top rows, routed cuts only, MAE:

| Rank | Policy | Min validation | Min series | Decay | MAE | Delta vs fallback | Positive / Negative series |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `validation_gated` | 0.010 | 0.000 | 0.10 | 0.0917558798 | 0.0002674001 | 4 / 6 |
| 2 | `validation_gated` | 0.000 | 0.000 | 0.10 | 0.0917603146 | 0.0002629653 | 6 / 4 |
| 3 | `validation_gated` | 0.005 | 0.000 | 0.10 | 0.0917621244 | 0.0002611555 | 7 / 3 |
| 4 | `series_guarded` | 0.000 | 0.000 | 0.10 | 0.0919869385 | 0.0000363414 | 6 / 4 |
| 5 | `series_risk_penalized` | 0.000 | 0.000 | 0.05 | 0.0919869385 | 0.0000363414 | 6 / 4 |
| 6 | `series_guarded` | 0.000 | 0.001 | 0.10 | 0.0919982524 | 0.0000250275 | 6 / 4 |
| 7 | `series_guarded` | 0.005 | 0.000 | 0.10 | 0.0920020171 | 0.0000212628 | 8 / 2 |
| 8 | `series_risk_penalized` | 0.005 | 0.000 | 0.05 | 0.0920020171 | 0.0000212628 | 8 / 2 |

通俗解释：

```text
最能提高总分的是：
  validation_gated 0.01

但它有个问题：
  4 条 series 赢
  6 条 series 输

比较均衡的是：
  validation_gated 0.005

它几乎不损失总分：
  delta 0.0002674 -> 0.0002612

但 series 分布更好：
  7 条赢
  3 条输
```

专业解释：

```text
The best aggregate policy remains validation-gated with a 0.01 aggregate lift
threshold. The risk-balanced aggregate candidate is validation-gated with a
0.005 threshold because it preserves nearly the same MAE delta while improving
the positive/negative routed-series split from 4/6 to 7/3.
```

项目对应：

```text
best aggregate delta:
  0.0002674001

best risk-balanced aggregate delta:
  0.0002611555

series-aware hard/risk policies:
  positive, but too small
```

## 5. Why The Series-Risk Policy Did Not Win

| 观察 | 通俗解释 | 专业解释 |
|---|---|---|
| `series_risk_penalized` ties `series_guarded` | 新规则没创造额外收益 | risk penalty did not improve frontier |
| 8 / 2 series split is possible | 更稳可以做到 | stronger guard reduces negative series |
| But delta falls to `0.0000212628` | 稳了很多，但赚太少 | risk reduction crushes aggregate lift |

通俗解释：

```text
你可以把它理解成：

方案 A：
  总收益高
  但有些 series 会亏

方案 B：
  大部分 series 不亏
  但总收益很小

如果只是研究：
  方案 A 有价值

如果要发布：
  方案 A 风险太集中
  方案 B 收益太小

所以现在还不能发布。
```

专业解释：

```text
The tested series-risk policies move along the risk frontier but do not improve
the frontier. They trade aggregate MAE lift for fewer negative series, but the
remaining lift is below the promotion threshold.
```

项目对应：

```text
best series-aware delta:
  0.0000363414

best 8/2 positive/negative split delta:
  0.0000212628

promotion status:
  blocked
```

## 6. Aggregate Lift vs Per-Series Risk

| 概念 | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| Aggregate lift | 总成绩提高 | average metric improvement | overall MAE delta |
| Per-series risk | 单个 series 被伤害 | heterogeneous series regression | positive/negative count |
| Promotion | 能不能发布 | release gate | Moirai/HF blocked |

通俗解释：

```text
一个模型不能只看总分。

假设 10 个学生考试：

  1 个学生提高 100 分
  9 个学生各退步 5 分

班级平均分可能还是提高。

但你不能说：
  这个教学方法对所有人都好。

我们的 router 现在类似这样：
  总分有提升
  但 series 之间不够均匀
```

专业解释：

```text
Aggregate MAE improvement can hide heterogeneous failure modes. Promotion needs
both aggregate lift and acceptable per-series downside because a deployed
forecasting Module will be judged on reliability, not only average score.
```

项目对应：

```text
best aggregate:
  strong enough to keep researching

per-series stability:
  not strong enough to publish
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| LoRA 不是只训练一次就完事 | adapter training is only one layer | adapter portfolio |
| 多个 adapter 各有偏向 | each adapter encodes a specialization bias | full/recent windows |
| router 决定用哪个偏向 | selection policy controls deployment behavior | no-leak router |
| 成功要看“训练 + 选择” | end-to-end evaluation matters | policy sweep |

通俗解释：

```text
LoRA 微调之后，
我们得到的不是一个绝对正确的模型。

我们得到的是一个“更偏向某种数据经验”的 adapter。

比如：
  recent1500 更偏近期
  recent2000 更均衡
  full 更偏长期历史

所以后面真正重要的问题变成：
  当前市场状态下，该用哪一个偏向？

这就是 router 的价值。
```

专业解释：

```text
LoRA creates lightweight specialized adapters. Once multiple adapters exist,
the core system problem becomes model selection under distribution shift. The
router policy is therefore part of the effective forecasting model.
```

项目对应：

```text
current LoRA stage:
  adapter portfolio exists

current bottleneck:
  selection reliability

current best feature seam:
  alignment-normalized
```

## 8. Current Verdict

Fact: 27 policy configurations were tested on the same alignment-normalized
router rows.

Fact: the best aggregate policy is `validation_gated` with
`min_validation_lift=0.01`, reaching `0.0002674001` MAE delta over fixed
`recent2000`.

Fact: the best risk-balanced aggregate candidate is `validation_gated` with
`min_validation_lift=0.005`, reaching `0.0002611555` MAE delta with a `7/3`
positive/negative series split.

Fact: `series_risk_penalized` did not beat `series_guarded`.

Inference: more hard-gate and series-risk threshold tuning is now low leverage.
The current router can show signal, but it cannot yet produce publishable
series-stable gains.

Recommendation: keep `alignment-normalized` as the current feature surface,
do not promote the adapter/router yet, and move next toward a supervised
selector objective or richer loss-aware router training rather than more manual
threshold sweeps.
