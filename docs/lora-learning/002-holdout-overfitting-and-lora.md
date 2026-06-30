# 002 - Holdout, Overfitting, and Why More LoRA Training Can Be Worse

Date: 2026-07-01

Experiment repo:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora
```

Run note:

```text
experiments/timesfm-lora/runs/2026-07-01-market-macro-level-h20-r4-holdout.md
```

## 1. What We Tried

In the previous round, a small LoRA adapter trained for 200 steps looked slightly
better than TimesFM zero-shot on a quick evaluation.

This round asked a stricter question:

```text
If we train longer, does the adapter get better on windows it did not train on?
```

We kept the LoRA configuration the same:

```text
lora_r=4
lora_alpha=8
lora_dropout=0.05
context_len=128
horizon_len=20
field=level
```

We changed one main thing:

```text
max_steps: 200 -> 1000
```

That means this round tested training duration, not adapter capacity.

## 2. New Concept: Holdout

A holdout set is data kept away from training.

Training data answers:

```text
Can the adapter fit what it was shown?
```

Holdout data answers:

```text
Can the adapter generalize to windows it did not train on?
```

For time series, holdout must respect time order. We should not randomly mix
future windows into training.

This round added:

```text
--skip-windows
```

Training used:

```text
skip_windows=0
max_windows=5000
```

Holdout evaluation used:

```text
skip_windows=5000
max_windows=500
```

Meaning:

```text
Train on the first 5000 balanced windows.
Evaluate on the next 500 balanced windows.
```

## 3. New Concept: Overfitting

Overfitting means a model learns patterns that help on training data but do not
help on unseen data.

The dangerous pattern is:

```text
training loss looks okay
holdout error gets worse
```

That happened in this round.

The 1000-step adapter ended with a low training loss:

```text
step=1000 loss=0.15799338
```

But its holdout score was worse than zero-shot.

Lesson:

```text
Lower training loss does not prove better forecasting.
```

## 4. Holdout Results

500 balanced holdout windows, 50 per series.

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 6.8866578500000015 | 0.04814407659052045 |
| Seasonal naive | 12.616396260000002 | 0.0690725444758241 |
| TimesFM 2.5 zero-shot | 5.477592374297006 | 0.04519216076482665 |
| LoRA r4 step200 | 5.778416210730518 | 0.04560542206655007 |
| LoRA r4 step1000 | 6.478898421882549 | 0.04788307865447745 |

Best model in this evaluation:

```text
TimesFM 2.5 zero-shot
```

## 5. What This Means

Fact:

```text
The 1000-step LoRA adapter trained successfully.
```

Fact:

```text
It did not beat zero-shot on the holdout windows.
```

Fact:

```text
The 1000-step adapter was worse than the 200-step adapter on holdout.
```

Inference:

```text
More training made the adapter fit early-window behavior too much.
```

Recommendation:

```text
Do not increase r yet.
Do not train longer blindly.
Add validation checkpoints or change the target.
```

## 6. Why We Should Not Try r=8 Yet

`r` controls adapter capacity.

Higher `r` means:

```text
more trainable parameters
more ability to adapt
more overfit risk
```

Because `r=4` already overfit when trained longer, going to `r=8` now would
likely make overfitting worse.

The next better move is not more capacity.

The next better move is better evaluation and better target selection.

## 7. Better Next Targets

Raw `level` mixes very different scales:

```text
SP500 around thousands
VIX around tens
rates around single digits
exchange rates around 1 or 100+
```

That can make adaptation harder.

Better next targets:

```text
log_change
realized_vol_20
```

Why:

```text
log_change focuses on relative movement.
realized_vol_20 focuses on risk and volatility.
```

These targets may align better with the market-macro-risk domain.

## 8. Lesson From This Round

LoRA is not automatically better because it trained.

A LoRA adapter is useful only if:

```text
it beats zero-shot
it beats naive baselines
it wins on holdout or rolling windows
it does not only lower training loss
```

This round taught the first real LoRA discipline:

```text
Always separate training success from forecasting success.
```

## 9. One-Sentence Summary

The 1000-step LoRA adapter trained correctly but generalized worse than
zero-shot, teaching that longer LoRA training can overfit and that holdout
evaluation is mandatory.
