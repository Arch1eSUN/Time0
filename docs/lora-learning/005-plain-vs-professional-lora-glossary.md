# 005 - Plain vs Professional LoRA Glossary

Date: 2026-07-01

Purpose: learn LoRA with two layers at the same time.

```text
Plain explanation = understand the idea.
Professional explanation = know the correct technical word.
Project mapping = know what it means in our Time0 / TimesFM run.
```

## 1. The Core Map

| Plain explanation | Professional explanation | In our project |
|---|---|---|
| The original forecaster | Base model / pretrained model | `TimesFM 2.5` |
| A small skill notebook | LoRA adapter | `market-macro-level-h20-r4-step1000-balanced` |
| Use the original forecaster directly | Zero-shot inference | TimesFM 2.5 without adapter |
| Let the forecaster read our notebook | Adapter inference | TimesFM 2.5 + LoRA adapter |
| Homework | Training set / train windows | first 5000 balanced windows |
| Exam | Holdout set / validation or test windows | next 500 balanced windows |
| The notebook memorized homework but failed exam | Overfitting | step1000 adapter lost to zero-shot |
| How wrong the prediction was | Error metric | MAE / SMAPE |
| What we ask the model to predict | Target variable / target field | `level`, later maybe `log_change` |

## 2. Base Model

Plain:

```text
The model we start from.
```

Professional:

```text
A pretrained model whose learned weights are loaded before adaptation.
```

In our project:

```text
google/timesfm-2.5-200m-transformers
```

How to think:

```text
TimesFM already knows general time-series patterns.
We do not want to destroy that.
```

## 3. Adapter

Plain:

```text
A small add-on that changes how the model behaves.
```

Professional:

```text
A parameter-efficient fine-tuning module trained while the base model remains frozen.
```

In our project:

```text
adapters/market-macro-level-h20-r4-step1000-balanced
```

How to think:

```text
The adapter is the thing we train, save, compare, keep, or delete.
```

## 4. LoRA

Plain:

```text
Train a small add-on instead of retraining the whole model.
```

Professional:

```text
Low-Rank Adaptation. It injects trainable low-rank matrices into selected model layers.
```

In our project:

```text
trainable params = 1,382,912
all params = 232,672,192
trainable percent = 0.5944%
```

How to think:

```text
Less than 1% of the model was trained.
The base model stayed mostly unchanged.
```

## 5. Rank `r`

Plain:

```text
How big the adapter's learning space is.
```

Professional:

```text
The low-rank dimension of the LoRA matrices.
```

In our project:

```text
r=4
```

How to think:

```text
r=4 = small adapter
r=8 = bigger adapter
```

Tradeoff:

```text
higher r = more capacity
higher r = more overfit risk
```

Why we did not jump to `r=8`:

```text
r=4 already failed holdout when trained longer.
Increasing capacity now may make memorization worse.
```

## 6. Alpha

Plain:

```text
How strongly the adapter's changes are applied.
```

Professional:

```text
LoRA scaling factor, often used as alpha / r.
```

In our project:

```text
lora_alpha=8
r=4
```

How to think:

```text
alpha controls update strength.
Too strong can distort the base model's behavior.
```

## 7. Dropout

Plain:

```text
Randomly hide part of the adapter during training so it does not memorize too easily.
```

Professional:

```text
Regularization applied to LoRA paths during training.
```

In our project:

```text
lora_dropout=0.05
```

How to think:

```text
dropout is anti-memorization pressure.
```

## 8. Zero-Shot

Plain:

```text
Use the original model without our adapter.
```

Professional:

```text
Inference without task-specific fine-tuning.
```

In our project:

```text
TimesFM 2.5 zero-shot holdout MAE = 5.4776
```

How to think:

```text
This is the model we must beat.
```

## 9. Training Set

Plain:

```text
The homework data the adapter sees.
```

Professional:

```text
The data used for gradient updates.
```

In our project:

```text
skip_windows=0
max_windows=5000
```

How to think:

```text
The adapter learns from these windows.
```

## 10. Holdout Set

Plain:

```text
The exam data the adapter did not see.
```

Professional:

```text
Data withheld from training to estimate generalization.
```

In our project:

```text
skip_windows=5000
max_windows=500
```

How to think:

```text
If the adapter fails here, it is not good enough.
```

## 11. Overfitting

Plain:

```text
Good at homework, bad at the exam.
```

Professional:

```text
The model fits training-specific patterns that do not generalize.
```

In our project:

```text
LoRA step1000 trained successfully but lost to zero-shot on holdout.
```

How to think:

```text
More training made the adapter worse outside its training window.
```

## 12. Context Length

Plain:

```text
How much history the model looks at.
```

Professional:

```text
Input sequence length used as the conditioning context.
```

In our project:

```text
context_len=128
```

How to think:

```text
The model looks back 128 time steps before forecasting.
```

## 13. Horizon Length

Plain:

```text
How far into the future the model predicts.
```

Professional:

```text
Forecast length / prediction horizon.
```

In our project:

```text
horizon_len=20
```

How to think:

```text
The model predicts the next 20 time steps.
```

## 14. Target Field

Plain:

```text
The thing we ask the model to predict.
```

Professional:

```text
The supervised target variable.
```

In our project:

```text
field=level
```

Problem:

```text
raw level mixes different scales: SP500, VIX, rates, FX.
```

Better next targets:

```text
log_change
realized_vol_20
```

## 15. MAE

Plain:

```text
Average size of the mistake.
```

Professional:

```text
Mean Absolute Error.
```

In our project:

```text
zero-shot MAE = 5.4776
LoRA step1000 MAE = 6.4789
```

How to think:

```text
lower MAE is better
zero-shot was better
```

## 16. SMAPE

Plain:

```text
Mistake size compared to the scale of the true value.
```

Professional:

```text
Symmetric Mean Absolute Percentage Error.
```

In our project:

```text
zero-shot SMAPE = 0.04519
LoRA step1000 SMAPE = 0.04788
```

How to think:

```text
lower SMAPE is better
zero-shot was better
```

## 17. The Correct Reading Of Our Latest Run

Plain:

```text
We made a notebook.
The notebook trained.
But the original forecaster did better on the exam.
So the notebook is not useful yet.
```

Professional:

```text
The r=4 LoRA adapter completed training, but under a skip-window holdout split
it underperformed TimesFM 2.5 zero-shot on both MAE and SMAPE.
```

Project decision:

```text
Do not promote this adapter.
Do not increase r yet.
Change target or validation strategy next.
```

## 18. Future Explanation Template

For every future run, explain results in this order:

| Plain question | Professional question |
|---|---|
| Did the script finish? | Did training complete without runtime failure? |
| Did we get a notebook? | Was an adapter artifact saved? |
| Did it beat simple guessing? | Did it beat naive baselines? |
| Did it beat the original model? | Did it beat zero-shot? |
| Did it pass the exam? | Did it improve holdout / rolling backtest? |
| Did it improve for real? | Did MAE and SMAPE both improve across series? |

## 19. One-Sentence Summary

The professional terms are just precise names for simple ideas: base model is
the original forecaster, LoRA adapter is the small notebook, zero-shot is the
original forecaster alone, holdout is the exam, and overfitting means the
adapter learned the homework but failed the exam.
