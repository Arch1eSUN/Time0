# 035 - Formal Router Policy

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-formal-fallback-veto-policy.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 没有训练新 LoRA | no new adapter training | same prediction archive |
| 把实验脚本升级成正式策略 | diagnostic to policy surface | `--policy fallback_veto` |
| 让 sweep 也能比较它 | reusable evaluation seam | `sweep_router_policies.py` |
| 验证数字是否一致 | semantic preservation check | same MAE delta |

通俗解释：

```text
上一轮 fallback-veto 是一个独立诊断脚本。

它证明：
  这个想法有信号。

但独立脚本还不够。

因为真正的项目需要统一入口：
  所有 router policy 都能用同一套 attribution。
  所有 policy 都能放进同一张 sweep 表比较。

所以这轮做的是：
  把 fallback-veto 从“实验小脚本”
  升级成正式 router policy。
```

专业解释：

```text
This round promotes fallback-veto from a standalone diagnostic into the shared
router policy interface. The policy can now be evaluated through
`summarize_router_attribution.py` and swept through `sweep_router_policies.py`.
```

项目对应：

```text
new formal policy:
  --policy fallback_veto

new shared module:
  scripts/router_fallback_veto.py
```

## 2. What Is A Formal Policy?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不是临时脚本 | reusable policy interface | `selection_for_cut` |
| 能被统一评估 | shared attribution surface | `summarize_router_attribution.py` |
| 能被批量比较 | sweep-compatible | `sweep_router_policies.py` |
| 才能进入后续系统 | serving-policy candidate | future router seam |

通俗解释：

```text
临时脚本像一次手工实验。

正式 policy 像项目里的一个标准选项。

区别是：

  临时脚本：
    只能证明“这次我跑出来有效”

  正式 policy：
    可以反复跑
    可以和其他 policy 放在一起比较
    可以进入后续系统设计
```

专业解释：

```text
A formal policy is a named adapter-selection behaviour behind the shared
`selection_for_cut` interface. It exposes parameters, writes decisions into the
standard attribution report, and can be swept against other policies.
```

项目对应：

```text
formal interface:
  selection_for_cut(...)

existing policies:
  validation_gated
  series_guarded
  series_risk_penalized

new policy:
  fallback_veto
```

## 3. Why We Extracted A Shared Module

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不想两处复制同一套逻辑 | avoid duplicate algorithm drift | shared Module |
| 诊断和正式策略用同一算法 | single implementation | `router_fallback_veto.py` |
| 以后改一次就够 | locality | one owner |
| 这次抽象是值得的 | two real callers | diagnostic + formal policy |

通俗解释：

```text
如果我们把 fallback-veto 逻辑复制两份：

  一份在 diagnostic script
  一份在 formal policy

短期能跑。
长期会出问题。

因为以后改一个地方，另一个地方可能忘了改。

所以这次把共同逻辑抽出来：
  两边都调用同一个 Module。
```

专业解释：

```text
The shared Module is justified because there are now two real adapters to the
same algorithmic seam: the diagnostic evaluator and the formal router policy.
This improves locality and prevents policy drift.
```

项目对应：

```text
shared module:
  scripts/router_fallback_veto.py

callers:
  scripts/evaluate_router_fallback_veto.py
  scripts/summarize_router_attribution.py
```

## 4. New CLI Surface

| 参数 | 通俗解释 | 专业解释 |
|---|---|---|
| `--policy fallback_veto` | 使用 fallback-veto 策略 | named router policy |
| `--veto-k 50` | 找 50 个历史相似失败/成功案例 | neighbor count |
| `--veto-regret-threshold 0.0002` | 超过这个预计后悔值就拦 | expected-regret cutoff |
| `--veto-feature-mode global` | 不直接用序列 ID | no series one-hot |

通俗解释：

```text
现在我们可以这样跑：

  --policy fallback_veto

这代表：
  先让 KNN-regret 选 adapter。
  再让 fallback-veto 判断是否要退回 recent2000。

这已经不是单独脚本里的隐藏逻辑。
它是 router policy 的正式选项。
```

专业解释：

```text
The policy surface exposes fallback-veto as a named selection policy with
explicit parameters. This makes the veto behaviour reproducible and comparable
inside the existing attribution and sweep reports.
```

项目对应：

```bash
uv run python scripts/summarize_router_attribution.py \
  --candidate-set knn-regret \
  --policy fallback_veto \
  --min-validation-lift 0.005 \
  --veto-feature-mode global \
  --veto-k 50 \
  --veto-regret-threshold 0.0002
```

## 5. Results

Formal attribution result:

| Policy | Min validation | Feature mode | k | Threshold | MAE delta | Positive / Negative series |
|---|---:|---|---:|---:|---:|---:|
| `fallback_veto` | 0.005 | `global` | 50 | 0.0002 | 0.0003088776 | 9 / 1 |

Sweep ranking:

| Rank | Policy | Min validation | k | Threshold | MAE delta | Positive / Negative series |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `fallback_veto` | 0.005 | 50 | 0.00020 | 0.0003088776 | 9 / 1 |
| 2 | `fallback_veto` | 0.005 | 50 | 0.00015 | 0.0003043504 | 9 / 1 |
| 3 | `fallback_veto` | 0.000 | 50 | 0.00020 | 0.0003038838 | 6 / 4 |
| 4 | `fallback_veto` | 0.005 | 50 | 0.00025 | 0.0003037471 | 7 / 3 |
| 7 | `validation_gated` | 0.000 | - | - | 0.0002705342 | 6 / 4 |
| 8 | `validation_gated` | 0.005 | - | - | 0.0002687244 | 7 / 3 |

通俗解释：

```text
好消息：

  正式 policy 跑出来的数字，
  和上一轮 diagnostic script 的数字一致。

这说明我们没有在“升级成正式接口”的过程中改坏逻辑。

而且 sweep 表现在也能看到：
  fallback_veto 明确排在 validation_gated 前面。
```

专业解释：

```text
The formal policy reproduced the diagnostic best result and ranked above
validation-gated baselines in the shared sweep table. This confirms semantic
preservation across the diagnostic-to-policy refactor.
```

项目对应：

```text
formal best:
  fallback_veto mvl=0.005 global k=50 threshold=0.0002

MAE delta:
  0.0003088776

series split:
  9/1
```

## 6. What Changed In The Architecture?

| 之前 | 现在 | 意义 |
|---|---|---|
| veto 只在诊断脚本里 | veto 是正式 policy | reusable |
| 逻辑只服务一个实验 | 逻辑被共享 Module 管 | locality |
| sweep 看不到 veto | sweep 可以比较 veto | policy comparison |
| 后续难接入系统 | 后续可接 router seam | serving candidate |

通俗解释：

```text
之前 fallback-veto 像一个单独实验。

现在它变成：
  Time0 router 系统里的一个正式策略选项。

这一步很重要。
因为模型项目不是只看一次实验结果。
我们需要一套可以反复比较、反复验证、反复扩展的评估表面。
```

专业解释：

```text
The implementation now separates algorithm ownership from evaluation entry
points. `router_fallback_veto.py` owns the veto algorithm. Attribution and sweep
scripts call it through the formal `fallback_veto` policy.
```

项目对应：

```text
algorithm Module:
  router_fallback_veto.py

policy seam:
  selection_for_cut(... policy="fallback_veto")

reporting surfaces:
  summarize_router_attribution.py
  sweep_router_policies.py
```

## 7. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 训练只是第一层 | adapter training is not the full system | LoRA portfolio |
| 策略接口很重要 | serving policy matters | router policy |
| 好实验要产品化成接口 | diagnostic to reusable seam | formal policy |
| 才能继续验证 | reproducible evaluation | shared sweep |

通俗解释：

```text
LoRA 项目不是：

  训练一个 adapter
  看一次分数
  结束

更真实的流程是：

  训练多个 adapter
  建立 router
  加风控层
  把有效策略变成正式 policy
  用统一评估反复测试

这轮我们做的是第四步：
  把有效策略变成正式 policy。
```

专业解释：

```text
Adapter fine-tuning creates specialized model behaviours. A production-grade
LoRA system also needs serving-time policy interfaces that decide when to use
each adapter and when to fall back. Formalizing fallback-veto is a step toward
that serving policy layer.
```

项目对应：

```text
adapter portfolio:
  full
  recent1500
  recent2000
  recent3000
  zero-shot

router:
  KNN-regret

risk policy:
  fallback_veto
```

## 8. Current Verdict

Fact: The formal `fallback_veto` policy reproduced the previous diagnostic
result: MAE delta `0.0003088776`, split `9/1`.

Fact: `sweep_router_policies.py` now ranks `fallback_veto` against
`validation_gated`.

Fact: The best formal row remains `mvl=0.005`, `global`, `k=50`,
`threshold=0.0002`.

Inference: The fallback-veto signal is now part of the reusable Time0 router
evaluation surface, not just a one-off experiment.

Recommendation: Stop tuning this same archive for now. The next useful test is
a different target or later archive.

## 9. Next Useful Step

```text
Run formal fallback_veto on a second target or later prediction archive.
```

Why:

```text
same archive:
  tells us the policy is internally consistent

new archive / target:
  tells us whether it generalizes
```
