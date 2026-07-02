# 058 - Score-Based Router

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-score-veto.md
```

## 1. What We Tried

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不再只靠一条规则 | score-based policy class | score-vote veto |
| 很多弱信号一起投票 | ensemble of feature thresholds | `ScoreRule.rules` |
| 票数够了才退回 fallback | vote-threshold gate | `min_votes` |
| 仍然用时间顺序验证 | chronological validation | `3750/4000/4250` |

通俗解释：

```text
上一轮 two-feature veto 的问题是：

  A AND B 太严格。

两个条件都满足才行动，
所以很多 validation fold 根本没有触发。

这一轮我们换成：

  不要求某两个条件必须同时满足。
  而是让很多规则一起投票。
  只要票数够多，就说明风险信号足够强，
  然后把 router 的选择退回 fallback。
```

专业解释：

```text
This run tests a score-vote fallback veto. The policy builds an ensemble from
discovery-selected single-feature threshold rules. At inference/evaluation
time, each rule contributes one vote when it matches. The router vetoes the
current selected adapter if the vote count is greater than or equal to the
selected threshold.
```

项目对应：

```text
script:
  experiments/timesfm-lora/scripts/validate_multifold_score_veto.py

report:
  reports/router-score-veto-multifold-validation-alignment-normalized-market-macro-realized-vol-20-h20-r4.json
```

## 2. What Is A Score-Based Router?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| router 不再只问一个问题 | scoring decision rule | score-vote |
| 每个信号给一票 | binary weak learner vote | feature threshold |
| 总票数就是风险分数 | aggregate score | `votes` |
| 阈值决定是否拦截 | decision threshold | `min_votes` |

通俗解释：

```text
你可以把 score-based router 理解成：

  它不是只看一个红灯。
  它看很多个小红灯。

如果只有 1 个红灯亮，
可能只是噪声。

如果 4 个、5 个、10 个红灯一起亮，
就说明这个 adapter override 可能危险，
于是退回更稳的 fallback。
```

专业解释：

```text
A score-based router converts multiple runtime features into a scalar decision
score. In this run the score is intentionally simple: the number of matched
threshold rules. A supervised router would learn the score from data. This run
uses a hand-built score to test whether richer policy capacity helps before we
commit to supervised training.
```

项目对应：

```python
votes = count(rule_matches(rule, feature_values) for rule in rules)

if selected_family != "recent2000" and votes >= min_votes:
    selected_family = "recent2000"
```

## 3. How This Relates To LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| LoRA 训练出多个专长 adapter | adapter specialization | recent1500/recent2000/recent3000 |
| router 决定什么时候用哪个 adapter | adapter selection policy | prediction router |
| adapter 会预测，router 会调度 | model weights vs policy layer | LoRA + router |
| 现在瓶颈在调度，不只在继续训练权重 | selection bottleneck | below fallback |

通俗解释：

```text
LoRA 微调像是训练几个专家：

  专家 A 擅长最近 1500 窗口。
  专家 B 擅长最近 2000 窗口。
  专家 C 擅长最近 3000 窗口。

但有专家不等于系统强。

你还需要一个调度员：

  什么时候叫专家 A？
  什么时候叫专家 B？
  什么时候不要逞强，直接用 fallback？

这个调度员就是 router。

这轮不是重新更新 LoRA 权重，
而是在训练后的 adapter 之上继续验证 router 策略。
```

专业解释：

```text
The LoRA adapters define candidate prediction functions. The router defines a
selection policy over those candidates. Once adapter-level gains exist, the
system can still fail if the selection policy chooses the wrong adapter in
specific regimes. Router validation is therefore part of the specialization
pipeline, even when no gradient update is performed in this particular run.
```

项目对应：

```text
adapter layer:
  TimesFM + LoRA checkpoints

router layer:
  choose one adapter/fallback per forecast window

current blocker:
  adapter signal exists, but no router policy has passed the finance release gate
```

## 4. Why We Keep The Multi-Fold Gate

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不能只看最后一次考试 | avoid holdout chasing | final holdout once |
| 先用旧数据找规则 | discovery split | `cut <= 3500` |
| 再用中间数据筛规则 | validation folds | `3750/4000/4250` |
| 最后数据只做验收 | final holdout | `cut > 4250` |

通俗解释：

```text
如果我们每次都看 final holdout，
然后根据 final holdout 改规则，
final holdout 就不再干净了。

所以流程必须是：

  先在 discovery 找候选。
  再在 validation 选候选。
  最后只在 holdout 上看一次结果。

这和考试很像：

  discovery 是练习题。
  validation 是模拟考。
  final holdout 是正式考试。

如果模拟考全挂，
正式考试偶然考好，
我们不能说这个方法已经可靠。
```

专业解释：

```text
The multi-fold gate protects against temporal overfitting and holdout leakage.
The router rule may only be selected using discovery and validation evidence.
The final holdout is not allowed to guide policy search.
```

项目对应：

```text
initial_discovery_max_cut: 3500
validation_cuts: 3750, 4000, 4250
final_holdout_min_cut: 4250
```

## 5. What The Result Says

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 最后结果看起来变好一点 | final metric delta positive | `+0.0001099906` |
| 负收益 series 没增加 | downside neutral on final | `2 -> 2` |
| 但验证阶段全失败 | validation set rejects policy | `validation_positive_count=0` |
| 所以不能发布 | not promotion-ready | below fallback |

通俗解释：

```text
这轮最容易误解的地方是：

  final holdout 是正的。

但我们不能只看这句话。

因为 validation 里：

  robust_pass_count = 0
  validation_positive_count = 0

意思是：

  没有一个候选在验证阶段真正过关。

所以 final 正收益只能说明：

  这个方向有信号。

但不能说明：

  这个规则已经稳定。
```

专业解释：

```text
The selected score-vote rule improves the final holdout but fails validation.
No candidate achieves positive combined validation metric delta while also
preserving downside constraints. This makes the final result diagnostic rather
than promotable.
```

项目对应：

```text
validation:
  validation_robust_pass_count: 0
  validation_positive_count: 0
  selected combined_metric_delta: -0.0004421860

final:
  changed_windows: 72
  metric_delta: +0.0001099906
  negative_series: 2 -> 2
  relative_lift_vs_fallback: -0.027951%
```

## 6. Why Final Positive Is Not Enough

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 正式考试偶然考好不等于会了 | holdout luck risk | final-only win |
| 模拟考全挂说明不稳定 | validation failure | no positive candidate |
| 金融预测尤其不能赌偶然 | downside-sensitive domain | negative series gate |
| 发布要看稳定证据 | promotion requires robustness | release gate |

通俗解释：

```text
金融方向最危险的错误是：

  看到一次赚钱，
  就以为策略有效。

在模型训练里也一样：

  看到 final holdout 好一点，
  不代表模型已经可靠。

如果 validation 不支持它，
那更合理的理解是：

  这个规则可能刚好碰到了最后那段数据的形状。

所以我们把它记为信号，
但不把它当成版本。
```

专业解释：

```text
Promotion requires evidence that the policy generalizes across intermediate
chronological folds before the final holdout. A final-only improvement after
validation failure is a high-overfitting-risk result.
```

项目对应：

```text
verdict:
  incremental_positive_but_below_fallback

release status:
  blocked
```

## 7. What We Learned About Policy Classes

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 单规则太浅 | low-capacity threshold | single-feature veto |
| AND 规则太窄 | sparse conjunction | two-feature veto |
| 投票规则更宽但不稳 | higher-capacity ensemble | score-vote veto |
| 下一步要让数据学边界 | supervised policy | learned router |

通俗解释：

```text
现在我们已经试了三种手写 router：

  1. 单特征规则：
     太简单。

  2. 双特征 AND：
     更精确，但触发太少。

  3. score-vote：
     触发更多，但 validation 不稳定。

所以问题不再是：

  再手写一个更复杂的 if 规则。

更像是：

  需要让一个监督式 router 学出边界。
```

专业解释：

```text
The manual policy-class ladder has reached diminishing returns. Score-vote
adds capacity, but the validation gate rejects it. The next policy class should
estimate adapter regret or fallback-veto probability directly from no-leak
runtime features.
```

项目对应：

```text
manual policy ladder:
  single-feature threshold -> too shallow
  two-feature AND -> too sparse
  score-vote ensemble -> validation unstable

next candidate:
  supervised no-leak router
```

## 8. Next Round

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不继续堆手写规则 | stop threshold ensemble tuning | no more manual veto ladder |
| 用已有 rows 训练小 router | supervised router | no-leak runtime features |
| 预测哪个 adapter 会后悔 | regret prediction | fallback-veto probability |
| 仍然用同一个 gate 验证 | same validation contract | multi-fold gate |

通俗解释：

```text
下一轮最值得做的是：

  不再靠人写规则。

而是把已有数据变成训练样本：

  输入：当时能看到的 no-leak 特征。
  标签：router override 事后看是好还是坏。
  输出：要不要退回 fallback。

这才是真正把 router 从规则系统推进到学习系统。
```

专业解释：

```text
The next experiment should train a small supervised classifier or ranker on
no-leak router rows. The target should represent adapter regret, fallback-veto
benefit, or probability of downside regression. The evaluation gate should stay
unchanged: discovery/train, chronological validation folds, final holdout.
```

项目对应：

```text
candidate next script:
  train_supervised_fallback_veto.py

must keep:
  no target leakage
  same validation folds
  same final holdout rule
  same negative-series release gate
```
