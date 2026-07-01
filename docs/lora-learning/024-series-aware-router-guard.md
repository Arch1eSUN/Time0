# 024 - Series-Aware Router Guard

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-series-guard.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 给小裁判加第二道保险 | series-aware validation gate | `--policy series_guarded` |
| 不只看全班平均，也看每个学生 | subgroup validation | `series_id` gate |
| 某条序列历史上被伤害，就挡回安全方案 | per-series fallback | fixed `recent2000` |
| 比较不同严格程度 | threshold sweep | `min_series_validation_lift` |

通俗解释：

```text
上一轮我们发现：
router 平均看起来更好，
但 DGS10 和 SP500 被伤害。

所以这轮我们给 router 加了一道保险：

第一道保险：
先看 learned router 在整体 validation cut 上有没有赢。

第二道保险：
再看它在当前这个 series 上有没有赢。

如果这个 series 上没赢，
就别让 learned router 接管，
继续用 recent2000。
```

专业解释：

```text
We extended the validation-gated router with a series-level guard. A learned
router can serve a future row only when the global validation gate passes and
the same candidate also beats the fallback on that series in the latest prior
validation cut.
```

项目对应：

```text
script: summarize_router_attribution.py
new option: --policy series_guarded
fallback: fixed recent2000
default series threshold: 0.0
```

## 2. What Is A Guardrail?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 模型不确定时别乱来 | conservative serving constraint | fallback |
| 新策略必须先证明自己 | validation gate | prior cut |
| 分组也不能被伤害 | subgroup guardrail | series gate |
| 宁可少赢，也不要隐藏性伤害 | regression prevention | promotion safety |

通俗解释：

```text
guardrail 就是护栏。

它不是让模型更聪明。
它是防止模型在没把握时乱开。

在这个项目里：
recent2000 是目前最稳的安全方案。
learned router 想替换它，必须先证明自己。
```

专业解释：

```text
A guardrail constrains model serving behavior. It does not change the adapter
weights. It changes when a learned policy is allowed to override the fallback.
```

项目对应：

```text
no guard:
  learned router can harm DGS10/SP500

series guard:
  learned router is blocked for a series when prior series validation is worse
```

## 3. What Did We Compare?

Routed cuts only:

| Policy | Series lift | MAE delta vs fallback | Relative lift vs fallback | Negative series |
|---|---:|---:|---:|---:|
| validation-gated | n/a | 0.0001260041 | 0.131419% | 5 |
| series-guarded | 0.0% | 0.0002025053 | 0.211207% | 5 |
| series-guarded | 0.5% | 0.0000418135 | 0.043610% | 5 |
| series-guarded | 1.0% | 0.0000580597 | 0.060555% | 4 |
| series-guarded | 2.0% | 0.0000445261 | 0.046439% | 1 |

通俗解释：

```text
最好的平均结果是：
series guard 但不要太严格。

0.0% 的意思是：
只要这个 series 上 learned router 没比 recent2000 差，
就允许它接管。

0.5%、1%、2% 更严格，
但它们挡掉了太多本来有用的切换，
所以整体 MAE 反而变差。
```

专业解释：

```text
The best MAE policy is `series_guarded` with `min_series_validation_lift=0.0`.
Stricter thresholds reduce some subgroup regressions, but over-constrain the
router and remove positive signal.
```

项目对应：

```text
best current policy:
  --policy series_guarded
  --min-series-validation-lift 0.0
```

## 4. What Improved?

| Metric | validation-gated | series-guarded 0.0% |
|---|---:|---:|
| selected MAE | 0.0957538599 | 0.0956773586 |
| MAE delta vs fallback | 0.0001260041 | 0.0002025053 |
| relative lift vs fallback | 0.131419% | 0.211207% |
| improvement vs zero-shot | 2.116398% | 2.194601% |
| positive changed windows | 412 | 379 |
| negative changed windows | 424 | 357 |

通俗解释：

```text
series guard 后：
平均 MAE 更低。
相对 fallback 的收益更高。
变差窗口更少。

这说明 guardrail 是有用的。
```

专业解释：

```text
The series-aware guard improves the aggregate routed MAE delta over fallback by
0.0000765012, a 60.713273% increase over the previous fallback delta.
```

项目对应：

```text
validation-gated delta: 0.0001260041
series-guarded delta: 0.0002025053
delta increase: 0.0000765012
```

## 5. What Did The Guard Block?

| Cut | Before guard | After guard | Effect |
|---:|---|---|---|
| 4000 | `softmax_series` for all allowed series | unchanged | positive cut stayed positive |
| 4250 | `knn_regret_no_series_k50` | block DGS10/SP500 | negative cut became positive |

通俗解释：

```text
cut4250 原来是坏的：
learned router 一接管，整体比 fallback 差。

series guard 发现：
DGS10 和 SP500 在 validation 里不该交给 learned router。

于是它让这两个 series 回到 recent2000。

结果 cut4250 从负变正。
```

专业解释：

```text
At cut4250, the global gate selected `knn_regret_no_series_k50`, but the
series-level gate blocked `DGS10` and `SP500`. This converted the cut-level
delta from -0.0003475770 to +0.0002644327.
```

项目对应：

```text
blocked at cut4250:
  DGS10:realized_vol_20
  SP500:realized_vol_20
```

## 6. Why Are We Still Not Publishing?

| Remaining issue | Meaning | Project impact |
|---|---|---|
| 5 series still negative at 0.0% threshold | subgroup regressions remain | promotion blocked |
| DFF still dominates positive signal | concentration risk | not broad enough |
| stricter thresholds reduce total gain | guard/signal tradeoff | needs better policy |
| cut4000 still allows risky series | one-cut validation is thin | need multi-cut guard |

通俗解释：

```text
这轮是进步，不是终点。

series guard 确实让结果更好，
但它没有彻底解决问题。

特别是 cut4000：
上一轮 validation 没看出 DGS10/SP500 风险，
所以 guard 没挡住。

这说明：
只看最近一个 validation cut 还是太薄。
```

专业解释：

```text
The series-aware guard improves causal routing but still relies on a single
latest validation cut. Some series-level failure modes are not detected early
enough, so promotion remains blocked.
```

项目对应：

```text
next guard idea:
  multi-cut series validation
  or series-risk penalty
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 微调不只是训练权重 | serving policy matters | router gate |
| 保护规则也能提升模型系统 | guardrails improve effective performance | series-aware gate |
| 太保守会挡掉好信号 | over-constrained policy loses recall | threshold sweep |
| 发布前要看分组风险 | subgroup reliability | per-series guard |

通俗解释：

```text
很多人以为 LoRA 的重点只有：
训练 adapter。

但真正做成一个可用模型系统，还要解决：
什么时候用这个 adapter？
什么时候不用？
哪些序列不能交给它？
出错时回到哪里？

这轮学到的是：
router 的 guardrail 也是模型能力的一部分。
```

专业解释：

```text
LoRA deployment is a policy problem, not only a weight-adaptation problem.
Serving-time gates can improve effective out-of-sample performance by deciding
when learned adaptation is safe to use.
```

项目对应：

```text
adapter:
  recent2000

router:
  learned selector

guardrail:
  global validation + series validation
```

## 8. How To Understand This Round

Fact:

```text
Series-aware gating improved routed MAE over validation-gated routing.
```

Fact:

```text
The best tested series threshold is 0.0%, not 0.5%, 1%, or 2%.
```

Fact:

```text
The guard blocked DGS10 and SP500 at cut4250.
```

Inference:

```text
The router now has a stronger valid policy, but the evidence is still too thin
for release.
```

Recommendation:

```text
Continue with multi-cut series validation or a series-risk penalty. Do not move
to Moirai integration, Hugging Face release, or larger LoRA rank yet.
```
