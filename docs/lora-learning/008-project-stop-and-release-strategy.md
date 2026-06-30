# 008 - When Does The Whole LoRA Project Stop?

Date: 2026-07-01

Related repo document:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/PROJECT_STRATEGY.md
```

## 1. The Big Difference

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一次训练停不停，是小问题 | Per-run stop condition | `SUCCESS_CRITERIA.md` |
| 整个项目停不停，是大问题 | Project-level termination criterion | `PROJECT_STRATEGY.md` |
| 训练不是目的 | Training is a means, not the objective | adapter must improve forecasting |
| 发布才是一个完整阶段 | Release is a product/research milestone | GitHub + Hugging Face |

上一篇笔记讲的是：

```text
这一轮 LoRA 训练什么时候停？
这个 adapter 怎么算成功？
```

这一篇讲的是：

```text
整个 Time0 TimesFM LoRA 项目什么时候可以停工？
我们是不是要一直训练下去？
训练出来以后发到哪里？
```

通俗说：

```text
训练一次像做一张卷子。
整个项目像决定这个学生能不能毕业。
```

专业说：

```text
Per-run success is not the same as project-level completion.
```

## 2. Do We Train Forever?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 不应该一直训练 | No endless training loop | stop after evidence target is met |
| 没有新数据新问题就别乱训 | Avoid unmotivated retraining | no data/model/eval change -> no train |
| 有触发条件才复训 | Event-triggered retraining | drift, new target, new base model |
| 训练越多不一定越强 | More optimization can overfit | `level step1000` worse than `step200` |

通俗解释：

```text
训练模型不是健身打卡。
不是每天训就更强。
如果题目、数据、模型、评估方法都没变，重复训练通常只是浪费时间，
甚至会把模型训得更会背旧题。
```

专业解释：

```text
Retraining should be triggered by new evidence: new data distribution,
new target, model drift, new base model, or failed evaluation coverage.
```

项目对应：

```text
现在不要无限训练 level。
level 已经显示 longer training got worse。
下一步应该换更合理的 target: realized_vol_20。
```

## 3. Four Project States

| 状态 | 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|---|
| Research Stop | 研究阶段够了 | enough evidence to stop exploring blindly | target/settings conclusion reached |
| Release Stop | 可以发布了 | release artifact is reproducible and documented | GitHub + HF release ready |
| Negative Stop | 证明这条路不行 | scoped experiments failed | publish negative result or archive |
| Maintenance Mode | 不继续乱做，只维护 | retrain only on triggers | drift/new TimesFM/new data |

### Research Stop

通俗说：

```text
我们已经知道这个方向行不行了，不需要继续乱试。
```

专业说：

```text
The experiment space has enough evidence to accept, reject, or pivot the target.
```

项目对应：

```text
level: 已经可以 Research Stop。
log_change: partial signal，最多做一次复验。
realized_vol_20: 下一轮主要研究方向。
```

### Release Stop

通俗说：

```text
模型不只是自己电脑上能跑，而是别人也能复现、下载、看懂风险。
```

专业说：

```text
The adapter is packaged with reproducible training recipe, evaluation report,
base-model reference, model card, and limitations.
```

项目对应：

```text
adapter + model card + eval table + Time0 repo recipe
```

### Negative Stop

通俗说：

```text
如果认真试过几个合理方向都赢不了原版 TimesFM，就别硬吹。
把失败结果也发出来，这也是开源价值。
```

专业说：

```text
A negative result is publishable when the evaluation harness is reproducible
and the scoped experiment space is clearly defined.
```

项目对应：

```text
如果 level、log_change、realized_vol_20 都失败，
Time0 仍然可以发布 eval harness 和负结果报告。
```

### Maintenance Mode

通俗说：

```text
发布后不是天天重训。
只有环境变了，才复训。
```

专业说：

```text
Released adapters should be maintained through drift monitoring and triggered
retraining rather than continuous unbounded training.
```

项目对应：

```text
新 FRED 数据窗口
新 TimesFM base model
线上评估漂移
新领域 target
```

## 4. What Counts As The Whole Project Succeeding?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 至少有一个方向真赢了 | at least one target passes Candidate Success | from `SUCCESS_CRITERIA.md` |
| 换几个时间段也赢 | rolling validation passes | at least 3 holdout cut-points |
| 不是碰巧赢一点点 | meaningful average improvement | at least 2% primary metric improvement |
| 别人能复现 | reproducible recipe | scripts + pinned deps + public data |
| 能发布说明书 | model card and eval report | HF model card |

通俗说：

```text
项目成功不是“我们训了很多次”。
项目成功是“我们有一个垂直领域 adapter，在没见过的未来窗口上，
稳定比原版 TimesFM 强，而且别人能复现”。
```

专业说：

```text
Project success is reproducible out-of-sample improvement over the frozen base
model, packaged with transparent provenance and limitations.
```

项目对应：

```text
success = Promotion Ready adapter + public release package
```

## 5. What Counts As The Whole Project Stopping Because It Failed?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 合理目标都试过了 | scoped target sweep completed | `level`, `log_change`, `realized_vol_20` |
| 小 LoRA 和稍大 LoRA 都不行 | capacity check failed | `r=4`, then maybe `r=8` |
| 多个 holdout 都赢不了 | rolling validation failed | no generalization |
| 继续训只是在碰运气 | no evidence of adaptation value | stop or publish negative result |

通俗说：

```text
如果它一直赢不了原版 TimesFM，我们不应该为了“有个模型”硬发一个模型。
```

专业说：

```text
If adaptation fails to beat the base model under controlled evaluation, the
correct output is the reproducible benchmark and negative finding.
```

项目对应：

```text
Time0 可以作为 TimesFM LoRA eval harness 发布，
即使最后没有 adapter release。
```

## 6. Publish To Google TimesFM, GitHub, Or Hugging Face?

| 去哪里 | 适合放什么 | 不适合放什么 | 我们的做法 |
|---|---|---|---|
| Google TimesFM repo | 通用 bugfix、脚本、文档、评估改进 | 我们自己的金融垂直 adapter | 有通用价值才 PR |
| Arch1eSUN/Time0 GitHub | 代码、训练脚本、评估脚本、run note、方法论 | 大模型权重和缓存 | 主工程仓库 |
| Hugging Face | LoRA adapter、model card、eval table | 没验证的夸张模型宣传 | 主模型发布地 |

通俗解释：

```text
Google TimesFM 仓库像原厂。
我们不能指望原厂收每个人自己的垂直领域改装件。

GitHub 像我们的工厂说明书。
放代码、流程、实验记录。

Hugging Face 像模型货架。
放 adapter、模型卡、评估表，让别人能下载和试用。
```

专业解释：

```text
Upstream is for generalizable contributions.
GitHub is for reproducibility and engineering provenance.
Hugging Face is for model artifact distribution.
```

项目对应：

```text
GitHub:
git@github.com:Arch1eSUN/Time0.git

Hugging Face:
Arch1eSUN/timesfm-2.5-market-macro-risk-lora
```

## 7. Why Publish Adapter Instead Of Full Model?

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| adapter 小很多 | LoRA stores delta weights | easier to upload/download |
| 尊重 base model 来源 | base model remains referenced | TimesFM stays base |
| 用户更清楚发生了什么 | transparent adaptation layer | model card can state exact base |
| 更适合垂直领域 | specialized patch over general model | market/macro risk adapter |

通俗说：

```text
完整模型像整台车。
LoRA adapter 像我们换上的专业零件。
发布零件更轻，也更诚实。
```

专业说：

```text
Publishing the adapter preserves base-model provenance and exposes the
fine-tuned delta as the actual contribution.
```

项目对应：

```text
HF release should contain adapter_config.json + adapter weights + model card.
```

## 8. Minimum Release Checklist

| 检查项 | 通俗解释 | 专业解释 |
|---|---|---|
| Base model | 说明原模型是谁 | base model reference |
| Data source | 说明用什么数据训 | dataset provenance |
| Target | 说明预测什么 | target field |
| Metrics | 说明怎么赢 | eval protocol |
| Limitations | 说明不能干什么 | intended use and misuse |
| Recipe | 说明怎么复现 | reproducibility |
| License | 说明别人怎么用 | license compatibility |

必须写清楚：

```text
这不是金融建议。
这不是交易信号。
这是 TimesFM 2.5 的市场/宏观风险领域 LoRA adapter。
```

专业表达：

```text
The model card must constrain intended use and disclose evaluation limitations.
```

## 9. Current Project Position

| 领域 | 当前状态 | 下一步 |
|---|---|---|
| GitHub repo | remote exists, no commits yet | first commit + push |
| `level` target | failed | stop increasing steps |
| `log_change` target | partial signal | optional repeat only |
| `realized_vol_20` target | not run yet | next controlled experiment |
| public release | not ready | needs Promotion Ready adapter |

当前最准确的判断：

```text
Time0 现在还不是模型发布项目。
它现在是一个正在形成的 LoRA 实验和评估项目。
```

专业说：

```text
The project is in target-selection and evaluation-harness phase, not release phase.
```

下一步：

```text
1. 把当前 Time0 repo 真正 commit/push 到 GitHub。
2. 跑 realized_vol_20。
3. 如果它赢 zero-shot，再做 rolling holdout。
4. rolling holdout 过了，才准备 Hugging Face adapter release。
```
