# 004 - LoRA Like I Know Nothing

Date: 2026-07-01

## 1. One Picture In Your Head

Think of TimesFM 2.5 as a very experienced forecaster.

It already knows general time-series patterns.

LoRA is not replacing that forecaster.

LoRA is giving that forecaster a small notebook about one domain.

```text
TimesFM 2.5 = experienced general forecaster
LoRA adapter = small domain notebook
TimesFM + LoRA = general forecaster reading our notebook
```

If the notebook helps, we keep it.

If the notebook hurts, we throw it away.

The original forecaster is not damaged.

## 2. What We Are Actually Training

We are not training all of TimesFM.

TimesFM has about:

```text
232,672,192 parameters
```

In our LoRA run, we trained only:

```text
1,382,912 parameters
```

That is about:

```text
0.5944%
```

Plain meaning:

```text
More than 99% of the model did not move.
Less than 1% was trained.
```

That small trainable part is the LoRA adapter.

## 3. Why This Is Useful

Full training says:

```text
Change the whole brain.
```

LoRA says:

```text
Keep the brain.
Add a small skill patch.
```

For our project:

```text
base TimesFM = general forecasting
adapter A = market/macro risk
adapter B later = maybe crypto volatility
adapter C later = maybe operational time series
```

Each adapter can be tested separately.

## 4. What Zero-Shot Means

Zero-shot means:

```text
Use TimesFM without our LoRA notebook.
```

It is the original model.

We compare LoRA against zero-shot because LoRA must answer this question:

```text
Did our notebook make the forecaster better?
```

If the answer is no, the adapter is not useful yet.

## 5. What Holdout Means

Holdout means:

```text
Data the adapter did not see during training.
```

Think of it as an exam.

Training data is homework.

Holdout data is the exam.

```text
homework score = training loss
exam score = holdout result
```

The exam matters more.

## 6. What Happened In Our Last Run

We trained a LoRA adapter longer:

```text
step200 -> step1000
```

We expected:

```text
more training -> better adapter
```

But the exam said no.

Holdout result:

```text
TimesFM zero-shot MAE = 5.4776
LoRA step1000 MAE    = 6.4789
```

Lower is better.

So:

```text
5.4776 is better than 6.4789
zero-shot beat LoRA
```

That means:

```text
The LoRA adapter trained successfully.
But it did not become a better forecaster.
```

## 7. The Most Important Distinction

Do not confuse these two:

```text
Training completed.
Model improved.
```

They are different.

Training completed means:

```text
The script ran.
The adapter file was saved.
The loss had numbers.
```

Model improved means:

```text
The adapter beat zero-shot on holdout.
```

Last run:

```text
training completed = yes
model improved = no
```

## 8. What Is Overfitting?

Overfitting means:

```text
The adapter got good at homework but bad at the exam.
```

In model terms:

```text
It learned training-window quirks.
It did not learn a general forecasting improvement.
```

This is why training longer can hurt.

More training is not always better.

## 9. Why We Should Not Jump To r=8

`r` means adapter capacity.

Higher `r` means a bigger notebook.

```text
r=4 = small notebook
r=8 = bigger notebook
```

If the small notebook already made the exam worse when trained longer, a bigger
notebook might memorize even more wrong details.

So the next move is not:

```text
make r bigger
```

The next move is:

```text
choose a better prediction target
use better validation
stop training before overfit
```

## 10. Why Raw Level May Be A Bad Target

We trained on `level`.

That means raw values:

```text
SP500: thousands
VIX: tens
interest rates: single digits
exchange rates: around 1 or 100+
```

These scales are very different.

The model may struggle to adapt one adapter across all of them.

Better next targets:

```text
log_change
realized_vol_20
```

Why:

```text
log_change = relative movement
realized_vol_20 = risk/volatility
```

These are more aligned with the market-macro-risk goal.

## 11. How To Judge A LoRA Run

Use this checklist:

```text
1. Did training finish?
2. Did it save an adapter?
3. Did it beat naive baseline?
4. Did it beat zero-shot?
5. Did it beat zero-shot on holdout?
6. Did it improve both MAE and SMAPE?
```

If it fails step 5, it is not good enough.

Our last run failed step 5.

## 12. The Correct Lesson

The correct lesson is not:

```text
LoRA does not work.
```

The correct lesson is:

```text
This LoRA setup did not work yet.
```

Specifically:

```text
raw level target + r=4 + 1000 steps did not beat zero-shot holdout
```

That is useful information.

Now we know what to change next.

## 13. What To Do Next

Next experiment should change one thing:

```text
field=level -> field=log_change
```

or:

```text
field=level -> field=realized_vol_20
```

Keep LoRA simple:

```text
r=4
alpha=8
same holdout method
```

Then compare again.

## 14. Simplest Summary

```text
TimesFM zero-shot = original model
LoRA adapter = small patch
training loss = homework score
holdout score = exam score
our adapter did homework, but failed the exam
next we change the target, not blindly train harder
```
