# 039 - Later Archive Retest

Date: 2026-07-02

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-02-market-macro-realized-vol-20-late-archive-guarded-retest.md
```

## 1. What We Ran

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 把上一轮最好候选冻结 | frozen policy retest | balanced guarded fallback-veto |
| 只考后半段时间 | later archive subset | cuts 4500..5500 |
| 不重新调正式参数 | no post-hoc promotion tuning | fixed config |
| 结果失败 | negative later generalization | delta below fallback |

通俗解释：

```text
上一轮我们找到一个比较好的候选：

  guarded fallback-veto
  平均赢
  split 到 5/5

这轮不能继续在同一张卷子上调。

我们要问：

  把这套规则固定下来，
  放到更后面的时间段，
  它还赢吗？

答案是：

  没赢。
```

专业解释：

```text
This round freezes the balanced guarded fallback-veto configuration and retests
it on a later alignment-normalized archive containing cuts 4500, 4750, 5000,
5250, and 5500.
```

项目对应：

```text
late rows:
  reports/router-rows-late-alignment-normalized-market-macro-realized-vol-20-h20-r4.json

frozen policy:
  fallback_veto_series_guarded
```

## 2. What Is A Later Archive Retest?

| 通俗版 | 专业版 | Time0 版本 |
|---|---|---|
| 不换题型，只换后面的时间 | chronological subset retest | later cuts |
| 看策略是否只是吃到早期规律 | temporal robustness check | late regime |
| 失败也是证据 | negative evidence | promotion blocker |

通俗解释：

```text
如果一个策略在全部 expanded cuts 上赢，
它可能只是因为前面的时间段帮了它。

later archive retest 的意思是：

  我们把早一点的 cut 拿掉，
  只看后面的 cut。

如果还赢，
说明它更稳。

如果不赢，
说明它可能对时间段敏感。
```

专业解释：

```text
A later archive retest keeps the target and feature surface fixed, but narrows
the evaluation to later chronological cuts. It tests whether router lift is
stable across time, not just across rows in the original aggregate surface.
```

项目对应：

```text
expanded comparable surface:
  3500, 3750, 4000, 4250, 4500, 4750, 5000, 5250, 5500

late comparable surface:
  4500, 4750, 5000, 5250, 5500
```

## 3. The Frozen Policy

| Parameter | Value |
|---|---:|
| `policy` | `fallback_veto_series_guarded` |
| `candidate_set` | `knn-regret` |
| `min_validation_lift` | 0 |
| `min_series_validation_lift` | -0.001 |
| `series_risk_decay` | 0.25 |
| `veto_feature_mode` | `global` |
| `veto_k` | 25 |
| `veto_regret_threshold` | 0.00015 |

通俗解释：

```text
这组参数就是上一轮的 balanced candidate。

本轮正式验证时没有改它。

这样做是为了避免：

  看了 late 结果以后，
  再挑一个 late 上最好看的参数，
  然后假装它一开始就是我们的策略。
```

专业解释：

```text
The frozen policy preserves the previous checkpoint's balanced configuration.
Any late-specific sweep is diagnostic only and does not count as promotion
evidence.
```

## 4. Late Surface

| Item | Value |
|---|---:|
| Rows | 2500 |
| Cuts | 4500, 4750, 5000, 5250, 5500 |
| Families | zero-shot, full, recent1500, recent2000, recent3000 |
| Best fixed family by MAE | recent2000 |
| Fixed recent2000 MAE | 0.0946496832 |
| Leaky oracle MAE | 0.0905343794 |

通俗解释：

```text
这个 late surface 还是同一个金融 realized_vol_20 任务。

不同点是：

  它只保留更后面的时间切片。

固定 recent2000 还是最强固定 baseline。
所以 router 要赢，还是必须打赢 recent2000。
```

专业解释：

```text
The late surface is still a comparable alignment-normalized router-row surface.
The fallback baseline remains `recent2000`, so the same promotion condition
applies: selected MAE must be below recent2000 MAE.
```

## 5. Frozen Retest Result

Routed cuts only:

| Policy | Selected MAE | Fallback MAE | Delta vs fallback | Relative lift | Split |
|---|---:|---:|---:|---:|---:|
| Unguarded fallback-veto | 0.0969867480 | 0.0969080555 | -0.0000786925 | -0.0008120327 | 7 / 3 |
| Frozen balanced guarded | 0.0969406774 | 0.0969080555 | -0.0000326219 | -0.0003366277 | 7 / 3 |

通俗解释：

```text
guard 还是有用：

  unguarded 亏 -0.00007869
  guarded 亏 -0.00003262

亏损减少了。

但没有翻正。

所以正式结论是：

  frozen balanced guarded policy
  在 late archive 上没有泛化成功。
```

专业解释：

```text
The per-series guard reduces downside versus unguarded fallback-veto on the late
surface, but the frozen policy remains below the fixed recent2000 fallback.
```

项目对应：

```text
frozen guarded late:
  delta = -0.000032621940338081745
  split = 7/3

required:
  delta > 0
```

## 6. Diagnostic Sweep Result

Best late diagnostic row:

| Parameter | Value |
|---|---:|
| `min_series_validation_lift` | 0.001 |
| `series_risk_decay` | 0.05 |
| Selected MAE | 0.0969113527 |
| Fallback MAE | 0.0969080555 |
| Delta vs fallback | -0.0000032972 |
| Split | 3 / 3 |

通俗解释：

```text
我们也做了一个小范围诊断 sweep。

结果说明：

  late surface 上确实能接近打平，
  但最好也还是负数。

这很重要。

它说明问题不只是上一轮参数不完美。
在后段时间里，这个 router family 还没有稳定打赢 fallback。
```

专业解释：

```text
The late diagnostic sweep reached near break-even but did not clear the
fallback baseline. Because this sweep uses late data for parameter selection,
even a positive result would be hypothesis-generating rather than promotion
evidence.
```

项目对应：

```text
best late diagnostic:
  delta = -0.0000032972286630600367
  split = 3/3
```

## 7. Where Did Late Fail?

Frozen guarded positives:

| Series | Delta vs fallback |
|---|---:|
| `VIXCLS:realized_vol_20` | 0.0005613355 |
| `DGS10:realized_vol_20` | 0.0001616912 |
| `BAMLH0A0HYM2:realized_vol_20` | 0.0001265247 |

Frozen guarded negatives:

| Series | Delta vs fallback |
|---|---:|
| `DFF:realized_vol_20` | -0.0012531175 |
| `DGS2:realized_vol_20` | -0.0000738041 |
| `DTWEXBGS:realized_vol_20` | -0.0000415819 |

通俗解释：

```text
有趣的是：

  上一轮的问题 series 和这轮不完全一样。

late frozen guard 里：

  VIXCLS
  DGS10
  BAMLH0A0HYM2

反而是正的。

但 DFF 变成最大负贡献，
而且它一个 series 的亏损就足够拖垮整体。
```

专业解释：

```text
The late failure is not the same downside pattern as the expanded-surface
failure. DFF becomes the dominant negative contributor, suggesting regime
sensitivity rather than a fixed bad-series list.
```

项目对应：

```text
new late downside:
  DFF:realized_vol_20

previous recurring downside reduced or reversed:
  DGS10
  BAMLH0A0HYM2
```

## 8. What This Teaches About LoRA

| 通俗解释 | 专业解释 | 项目对应 |
|---|---|---|
| 一个好 router 也可能过期 | router policy can be regime-sensitive | late cuts fail |
| guard 能减亏但不一定能赚钱 | risk control is not alpha | negative delta remains |
| 不能只看全样本平均 | aggregate surface can hide temporal fragility | expanded vs late |
| 下一步要处理 regime | temporal robustness problem | DFF late failure |

通俗解释：

```text
LoRA adapter 和 router 都会遇到一个问题：

  过去有效的规律，
  到后面的市场环境可能变弱。

这轮不是说 guard 没用。

它确实减少了亏损。

但它还不能保证：

  后面的时间段也赚钱。

所以我们现在看到的是：

  风险控制层有效，
  但缺少时间 regime 判断。
```

专业解释：

```text
The portfolio-router architecture needs a temporal robustness layer. Per-series
guarding controls known downside, but late-regime failure shows that the router
also needs regime-aware fallback or a stronger validation objective.
```

项目对应：

```text
current model stack:
  LoRA adapter portfolio
  fallback-veto
  per-series downside guard

missing layer:
  temporal regime robustness
```

## 9. Fact / Inference / Recommendation

Fact: The late alignment-normalized surface was built from existing prediction
archives with 2500 rows across cuts 4500 to 5500.

Fact: Frozen balanced guarded fallback-veto failed the late retest:
`-0.0000326219` MAE delta versus fallback.

Fact: The guard still improved over unguarded fallback-veto on the same late
surface, reducing loss from `-0.0000786925` to `-0.0000326219`.

Fact: A late-specific diagnostic sweep reached `-0.0000032972`, close to
break-even but still negative.

Inference: The balanced guarded policy is useful but not temporally robust
enough. The failure pattern moved to DFF, so a static per-series blocklist is
not sufficient.

Recommendation: Do not promote the balanced guarded policy. The next research
step should add a temporal-regime guard or test a stricter validation objective
that blocks overrides when the latest prior cut shows concentrated downside.

## 10. Next Round

```text
Next useful experiment:

  add or test a latest-cut downside guard:
    if latest prior cut has concentrated negative contribution for a series,
    block current overrides for that series.

success criteria:
  late surface delta > 0
  DFF downside reduced
  expanded surface remains positive
```

