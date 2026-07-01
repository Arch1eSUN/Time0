# 047 - Fallback Sensitivity Guard

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-zscore-fallback-sensitivity.md
```

## 1. What We Built

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 加了一个防误判检查 | fallback sensitivity evaluator | `evaluate_router_fallback_sensitivity.py` |
| 不只和一个保底方案比 | multi-fallback validation | all families as fallbacks |
| 看 router 是否换个保底就变差 | baseline sensitivity check | positive/negative fallback split |
| 把手工判断变成脚本 | reproducible promotion guard | JSON report |

通俗解释：

```text
上一轮我们发现：

  zscore router 对某个 fallback 小赢，
  但换成另一个 fallback 就变差。

这很危险。

如果只挑一个对它有利的 fallback，
我们可能会误以为 router 变强了。

所以这轮我们加一个检查：

  同一个 router，
  换不同 fallback，
  看结果是不是仍然站得住。
```

专业解释：

```text
This round adds a fallback-sensitivity evaluator that reruns the same no-leak
router policy across multiple fallback families and classifies whether the
observed gain is robust, partial, fallback-sensitive, or not promotable.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/evaluate_router_fallback_sensitivity.py
```

## 2. What Is A Fallback?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| router 不确定时回到谁 | default serving policy | `fallback_family` |
| 保底方案 | fail-closed baseline | full / zero-shot / recent2000 |
| 比较标准 | baseline comparator | delta vs fallback |

通俗解释：

```text
fallback 就是保底方案。

比如 router 想动态选择：

  zero-shot
  full
  recent1500
  recent2000
  recent3000

但如果它没有足够证据，
它要退回一个默认选择。

这个默认选择就是 fallback。
```

专业解释：

```text
A fallback is the fixed policy used when a learned router does not clear its
validation gate. It is also the baseline used to compute router lift.
```

项目对应：

```text
MAE fallback:
  full

SMAPE fallback examples:
  zero-shot
  recent1500
  recent2000
```

## 3. Why Fallback Sensitivity Matters

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 只赢一个弱对手不算强 | baseline-dependent lift is weak evidence | fallback-sensitive |
| 换个对手就输，不能上线 | non-robust promotion signal | blocked |
| 稳定赢才有意义 | robust positive delta | promotable candidate |

通俗解释：

```text
如果一个学生只和比较弱的人比能赢，
换一个强一点的对手就输，
那不能说这个学生很强。

router 也是一样。

如果它只比某个 fallback 好，
但比另一个合理 fallback 差，
那它不是稳定进步。

这叫 fallback-sensitive。
```

专业解释：

```text
Fallback sensitivity means the apparent router improvement depends on the
chosen baseline. A deployment policy should not be promoted when its sign
flips across reasonable fallback families.
```

项目对应：

```text
previous problem:
  SMAPE looked slightly positive against recent1500
  but negative against zero-shot
```

## 4. Verdict Classes

| Verdict | 通俗解释 | 专业解释 |
|---|---|---|
| `robust_positive` | 每个 fallback 都赢 | positive against all checked fallbacks |
| `partial_positive` | 有赢，没有输，但不是全赢 | positive for some, zero for others, no negatives |
| `fallback_sensitive` | 有的赢，有的输 | sign flips across fallbacks |
| `fail_closed_all` | 全部不切换 | zero delta across all fallbacks |
| `not_promotable` | 没赢，而且有输 | no positives and at least one negative |

通俗解释：

```text
我们现在不只看一个数字。

我们把结果分成几类：

  全赢：最强
  有赢没输：有研究价值
  有赢有输：不稳定
  全部不动：保守没伤害
  没赢还输：不该继续吹
```

专业解释：

```text
The sensitivity verdict classifies router promotion evidence by sign stability
across fallback families.
```

项目对应：

```text
guardrail:
  fallback-sensitive results stay blocked
```

## 5. What We Observed

| Surface | Metric | Verdict | Positive | Negative | Zero | Min delta | Max delta |
|---|---|---|---:|---:|---:|---:|---:|
| all-recent | SMAPE | `fallback_sensitive` | 2 | 3 | 0 | -0.0017006988 | 0.0029060640 |
| all-recent | MAE | `fallback_sensitive` | 1 | 1 | 3 | -0.0004458839 | 0.0014738528 |
| recent2000 | SMAPE | `partial_positive` | 2 | 0 | 1 | 0 | 0.0017566489 |
| two-family | SMAPE | `not_promotable` | 0 | 1 | 1 | -0.0004501663 | 0 |

通俗解释：

```text
结果非常清楚：

  两候选：不值得发布
  三候选：有一点正信号，但还不是全赢
  五候选：理论上限更高，但变得不稳定

所以继续盲目加 adapter，
不是正确方向。
```

专业解释：

```text
The three-family zscore pool produced a partial-positive SMAPE result. The
five-family all-recent pool became fallback-sensitive on both MAE and SMAPE,
which blocks promotion.
```

项目对应：

```text
best current zscore research surface:
  recent2000 SMAPE partial_positive

blocked surface:
  all-recent fallback_sensitive
```

## 6. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 候选越多，选择越难 | adapter diversity increases policy complexity | all-recent pool |
| 上限变高不等于系统变强 | oracle headroom is not deployable lift | leaky oracle |
| 发布需要稳定正收益 | promotion requires robust validation | sensitivity guard |
| 保底线本身也是设计选择 | fallback is part of serving policy | fallback family |

通俗解释：

```text
LoRA 训练到这里，你要开始把它看成系统工程。

不是：

  我训练了更多 adapter，所以更强。

而是：

  我训练了更多 adapter，
  但系统能不能在不知道答案的时候选对？

如果不能选对，
adapter 越多，反而越容易选错。
```

专业解释：

```text
Adapter quality and serving-policy quality are separate. A larger adapter pool
must be paired with a robust causal router; otherwise the extra adapters remain
oracle-only optionality.
```

项目对应：

```text
new promotion guard:
  fallback sensitivity check
```

## 7. Current Verdict

Fact:

```text
A reusable fallback-sensitivity evaluator now exists.
```

Fact:

```text
The five-family zscore pool is fallback-sensitive:

  SMAPE positives: 2/5
  SMAPE negatives: 3/5
  MAE positives:   1/5
  MAE negatives:   1/5
```

Fact:

```text
The three-family zscore pool has partial-positive SMAPE evidence:

  positive: 2
  negative: 0
  zero: 1
```

Inference:

```text
The best current zscore direction is not to widen the adapter pool further,
but to stabilize the recent2000 SMAPE signal.
```

Recommendation:

```text
Next, test a stricter SMAPE guard on the three-family recent2000 pool before
training more zscore adapters.
```
