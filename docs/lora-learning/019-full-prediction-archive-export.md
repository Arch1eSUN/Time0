# 019 - Full Prediction Archive Export

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-realized-vol-20-full-archives.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把所有考卷都保存成错题本 | full prediction archive export | 15 archives |
| 每个 cut 都跑 5 个 family | candidate matrix | 3 cuts x 5 families |
| 每个 family 都答同一套题 | aligned forecast windows | same `window_id` |
| 后面才能训练 selector | router training data | future joiner |

通俗解释：

```text
上一轮我们只验证：
能不能保存逐窗口预测？

这轮我们正式把所有候选 adapter 都跑了一遍：

cut4000: 5 个 family
cut5000: 5 个 family
cut5500: 5 个 family

每个 family 都答 500 道题。
```

专业解释：

```text
We exported a complete prediction archive matrix for the current router
candidate set. Each cut/family pair has one aggregate report and one per-window
prediction archive.
```

项目对应：

```text
3 cuts * 5 families * 500 windows = 7500 prediction records
```

## 2. Why We Added An Export Script

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不要手敲 15 条命令 | reproducible orchestration | `export_prediction_archives.py` |
| 跑过的可以跳过 | idempotent export | skip existing outputs |
| 路径不能靠记忆 | fixed family/cut mapping | adapter matrix |
| 以后别人也能复现 | research reproducibility | committed script |

通俗解释：

```text
如果我手动复制 15 条命令，
很容易某个 adapter 路径写错。

所以我们把“该跑哪些 family、哪些 cut、输出到哪里”
写进脚本。
```

专业解释：

```text
The export script turns a repeated evaluation workflow into a reproducible
Module. It records the adapter-family matrix and delegates inference to
evaluate_timesfm.py.
```

项目对应：

```text
script:
experiments/timesfm-lora/scripts/export_prediction_archives.py
```

## 3. What Was Exported

| Cut | Families | Windows per family | Records per cut |
|---:|---|---:|---:|
| 4000 | zero-shot/full/r1500/r2000/r3000 | 500 | 2500 |
| 5000 | zero-shot/full/r1500/r2000/r3000 | 500 | 2500 |
| 5500 | zero-shot/full/r1500/r2000/r3000 | 500 | 2500 |

通俗解释：

```text
同一个 cut 里，
5 个 family 必须答完全相同的 500 道题。

否则后面没法比较：
同一道题到底谁答得更好。
```

专业解释：

```text
Archive alignment is required before computing adapter-disagreement features or
best-family labels. The join key is `window_id`.
```

项目对应：

```text
window_id = series_id:start_index
```

## 4. What We Verified

| 检查 | 结果 |
|---|---|
| archive-export reports | 15 |
| prediction records | 7500 |
| `cut4000` alignment | passed |
| `cut5000` alignment | passed |
| `cut5500` alignment | passed |
| old report metrics match new export reports | passed |
| feature contract | passed |

Observed:

```text
validated_reports 15
validated_prediction_records 7500
cut_aligned 4000 families 5 windows_per_family 500
cut_aligned 5000 families 5 windows_per_family 500
cut_aligned 5500 families 5 windows_per_family 500
feature_keys past_last,past_max,past_mean,past_min,past_std,past_trend
```

通俗解释：

```text
这说明我们现在不是只有“平均分”。

我们有每一道题上：
zero-shot 怎么答，
full adapter 怎么答，
recent1500 怎么答，
recent2000 怎么答，
recent3000 怎么答。
```

专业解释：

```text
The archive matrix is aligned and metric-preserving. It can now serve as the
source dataset for router-row construction.
```

## 5. What This Teaches About LoRA

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 多个 adapter 需要共同考卷 | comparable evaluation set | aligned archives |
| 训练 selector 要有标签 | supervised routing labels | best future MAE family |
| 不能只看最终平均分 | per-window evidence | prediction records |
| 复现实验要脚本化 | reproducible experiment pipeline | export script |

通俗解释：

```text
LoRA 微调项目到这一步，
已经不是单纯训练一个 adapter。

我们在构建一个小系统：

基础模型
多个 LoRA adapter
评估档案
router 训练数据
router 选择规则
```

专业解释：

```text
Once multiple adapters exist, the system needs a routing dataset. Fine-tuning
creates candidate behaviors; archive export creates the evidence needed to
select among those behaviors.
```

项目对应：

```text
new Module:
export_prediction_archives.py

next Module:
join_prediction_archives.py

future Adapter:
no-leak router
```

## 6. What Is The Next Label?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 同一道题谁错最少 | best-family label | min future MAE |
| 这是训练 selector 的答案 | supervised target | label column |
| 预测前不能用这个答案 | not runtime feature | no leakage |
| 只在训练/评估时算 | offline label construction | joiner |

通俗解释：

```text
下一步 joiner 会做一件事：

把同一道题的 5 个答案摆在一起，
算出谁错最少。

这个“谁错最少”就是 router 的训练标签。
```

专业解释：

```text
The best-family label is derived from future error, so it is allowed only as a
training/evaluation target. Runtime router inputs must be restricted to
pre-forecast features and model outputs available before actuals are known.
```

项目对应：

```text
features:
past statistics
adapter predictions
adapter disagreement
series identity

label:
best family by future MAE
```

## 7. Current Verdict

| 问题 | 答案 |
|---|---|
| 这轮训练了新 adapter 吗？ | 没有 |
| 这轮有新模型胜利吗？ | 没有直接证明 |
| 这轮完成了什么？ | 完整 router 数据源 |
| 可以训练 router 了吗？ | 可以开始做 joiner |
| 可以发布 adapter 吗？ | 还不可以 |

一句话：

```text
我们已经把“多个 LoRA adapter 的答题记录”完整导出。
下一轮要把这些 records 合并成 router 训练表。
```
