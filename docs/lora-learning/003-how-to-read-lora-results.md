# 003 - How To Read LoRA Training Results

Date: 2026-07-01

Related run:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora/runs/2026-07-01-market-macro-level-h20-r4-holdout.md
```

## 1. What You Asked

You asked how to understand the result from the last LoRA run.

The short version:

```text
The training worked technically.
The adapter was produced successfully.
But the adapter did not beat TimesFM zero-shot on holdout data.
So the adapter is not good enough yet.
```

This is not a failed engineering run.

It is a useful experimental result.

## 2. The Four Things We Compared

We compared four kinds of predictors.

| Predictor | Meaning | Why it matters |
|---|---|---|
| Last-value naive | Predict future values as the last observed value | Simple baseline that is hard to beat in slow-moving series |
| Seasonal naive | Repeat values from a prior lag | Checks whether simple repetition is enough |
| TimesFM zero-shot | Use TimesFM 2.5 without LoRA | The base model benchmark |
| TimesFM + LoRA | Use TimesFM 2.5 with our trained adapter | The thing we are testing |

The rule:

```text
LoRA is useful only if it beats zero-shot on unseen data.
```

If LoRA only beats naive but loses to zero-shot, then the base model was already
better than our adaptation.

## 3. What Zero-Shot Means

Zero-shot means:

```text
Use the model directly without training it on our data.
```

For this project:

```text
TimesFM 2.5 zero-shot = original TimesFM 2.5 forecasting ability
```

Why this matters:

```text
TimesFM is already trained on lots of time-series data.
Our LoRA adapter must improve it, not merely reproduce it.
```

So zero-shot is the real benchmark.

## 4. What Holdout Means

Holdout means:

```text
Data kept away from training.
```

This round used:

```text
training windows: first 5000 balanced windows
holdout windows: next 500 balanced windows
```

The important detail is `next`.

For time series, we care about time order.

We should not train on future windows and evaluate on earlier windows.

That would leak information.

The correct mental model:

```text
past data -> train
later data -> evaluate
```

## 5. What The Metrics Mean

We used MAE and SMAPE.

### MAE

MAE means Mean Absolute Error.

It answers:

```text
On average, how far was the prediction from the true value?
```

Lower is better.

Example:

```text
MAE 5 means average error is about 5 raw units.
```

### SMAPE

SMAPE means Symmetric Mean Absolute Percentage Error.

It answers:

```text
How large is the error relative to the scale of the value?
```

Lower is better.

SMAPE is useful because our series have different scales:

```text
SP500 is in thousands.
VIX is in tens.
Interest rates are single digits.
```

Raw MAE alone can be misleading across mixed-scale series.

## 6. The Actual Result

Holdout results:

| Model | MAE | SMAPE |
|---|---:|---:|
| Last-value naive | 6.8867 | 0.04814 |
| Seasonal naive | 12.6164 | 0.06907 |
| TimesFM 2.5 zero-shot | 5.4776 | 0.04519 |
| LoRA r4 step200 | 5.7784 | 0.04561 |
| LoRA r4 step1000 | 6.4789 | 0.04788 |

Read it from best to worst:

```text
TimesFM zero-shot was best.
LoRA step200 was second.
LoRA step1000 was worse.
Naive baselines were weaker than zero-shot.
```

Important:

```text
The 1000-step adapter trained longer but performed worse.
```

## 7. Why Training Longer Became Worse

Training longer can make the adapter memorize patterns in the training windows.

That is called overfitting.

The pattern looks like this:

```text
training loss looks okay
holdout error gets worse
```

This round showed that pattern.

At step 1000, the training loss was low:

```text
step=1000 loss=0.15799338
```

But holdout performance was worse than zero-shot:

```text
zero-shot MAE = 5.4776
LoRA step1000 MAE = 6.4789
```

Lesson:

```text
Training loss is not the final judge.
Holdout performance is the judge.
```

## 8. What This Says About LoRA

LoRA is not magic.

LoRA gives us a small trainable adapter.

But the adapter can learn the wrong thing if:

```text
the target is poorly chosen
the data scale is mixed
the training runs too long
the validation setup is weak
the adapter capacity is too high
```

In this round, adapter capacity was not high:

```text
r=4
trainable params=1,382,912
trainable percent=0.5944%
```

So the likely issue is not "adapter too large".

More likely issues:

```text
raw level is a difficult mixed-scale target
later holdout windows differ from early training windows
1000 steps over-adapted to early windows
```

## 9. How You Should Read Future Results

Use this order every time:

1. Did the script finish without errors?
2. Did it save an adapter?
3. Did the adapter beat naive baselines?
4. Did the adapter beat TimesFM zero-shot?
5. Did it win on holdout, not just training-adjacent windows?
6. Did both MAE and SMAPE improve?
7. Did the improvement happen across many series, not just one?

Only if the answer is yes to 4-7 should we call the adapter better.

## 10. How To Interpret A Negative Result

A negative result does not mean LoRA failed.

It means one hypothesis failed.

This round tested:

```text
Hypothesis: r=4 trained for 1000 steps on raw level will improve holdout.
```

Result:

```text
Rejected.
```

That is useful because it tells us what not to do next.

Do not do:

```text
blindly train longer
increase r to 8 immediately
claim the adapter is better because training finished
```

Better next move:

```text
change the target to log_change or realized_vol_20
add validation checkpoints
compare adapters by holdout and rolling backtest
```

## 11. What To Remember

The most important lesson:

```text
LoRA training success and model improvement are different things.
```

Training success means:

```text
the adapter trained and saved
```

Model improvement means:

```text
the adapter beats zero-shot on unseen future windows
```

This round had training success, but not model improvement.

## 12. One-Sentence Summary

The latest LoRA run proved the pipeline can train longer, but the holdout result
showed overfitting: TimesFM zero-shot stayed better than the trained adapter, so
the next improvement should come from better targets and validation, not simply
more steps or larger rank.
