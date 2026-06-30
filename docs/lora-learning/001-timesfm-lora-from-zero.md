# 001 - TimesFM LoRA from Zero

Date: 2026-07-01

Experiment repo:

```text
/Users/archiesun/Documents/Time0/experiments/timesfm-lora
```

## 1. What We Are Trying To Do

Goal: make TimesFM 2.5 more specialized for one useful time-series domain.

This round's domain:

```text
market-macro-risk
```

That means we are not training the model to directly say "buy" or "sell".
We are first training it to forecast market and macro risk series better:

```text
VIX
SP500
10Y treasury yield
2Y treasury yield
Fed funds rate
high-yield credit spread
WTI oil
trade-weighted dollar
EUR/USD
JPY/USD
```

Reason: risk and macro state forecasting is a deeper, cleaner first target than
direct trading actions. Trading actions mix forecasting, position sizing, risk
management, transaction cost, and execution into one noisy label.

## 2. What Is LoRA?

LoRA means Low-Rank Adaptation.

The simplest mental model:

```text
base model = original knowledge
LoRA adapter = small learned patch
final behavior = base model + adapter
```

Normal full fine-tuning updates the whole model:

```text
TimesFM 2.5 has about 232M parameters
full fine-tuning tries to update all of them
```

LoRA freezes the original model and trains only small extra matrices:

```text
base TimesFM weights: frozen
LoRA adapter weights: trainable
```

So the model becomes:

```text
original layer output + adapter correction
```

In formula form:

```text
original: y = W x
LoRA:     y = W x + B A x
```

`W` is the original model weight. It does not change.

`A` and `B` are small LoRA matrices. They are the only parts we train.

## 3. Why LoRA Is Useful

LoRA is useful when we want domain adaptation without retraining the whole
foundation model.

For Time0 and Moirai, that means:

```text
Keep TimesFM 2.5 as the general forecasting base.
Train small adapters for specific domains.
Compare adapters with evidence.
Keep or reject adapters based on rolling backtests.
```

This is valuable because adapters are:

```text
small
cheap to train
easy to version
easy to disable
easy to compare
```

If an adapter is bad, we throw away the adapter. We do not damage the base model.

## 4. Important LoRA Knobs

| Knob | Meaning | This round |
|---|---|---:|
| `r` | Adapter capacity. Higher means more trainable capacity and more overfit risk. | `4` |
| `alpha` | Scale of the LoRA update. Often paired with `r`. | `8` |
| `dropout` | Randomly disables part of adapter training to reduce overfit. | `0.05` |
| `learning_rate` | How big each optimizer update is. | `5e-5` |
| `max_steps` | Number of optimizer updates. | `200` |
| `batch_size` | Number of windows per update. | `2` |

This round used `r=4`, which is intentionally small.

The lesson: start with a small adapter so we can see whether the domain has a
signal before increasing capacity.

## 5. Time-Series Terms

TimesFM does not train on a single row. It trains on windows.

This round used:

```text
context_len = 128
horizon_len = 20
```

Meaning:

```text
Look at the past 128 time steps.
Predict the next 20 time steps.
```

Example:

```text
past:   t-127 ... t
future: t+1   ... t+20
```

The past is the input. The future is the training target.

## 6. What Data We Used

Data source:

```text
FRED public CSV endpoint
```

Generated local training file:

```text
data/market/daily_market_series.csv
```

The CSV format is long format:

```csv
series_id,timestamp,field,value,source_symbol,source
VIXCLS:level,2025-01-02,level,17.93,VIXCLS,fred
```

Important columns:

```text
series_id = which time series this point belongs to
timestamp = time order
field = what target we are training
value = numeric value
```

This round trained on:

```text
field = level
```

That means we trained the model to forecast raw levels such as VIX level,
interest-rate level, SP500 index level, and so on.

## 7. Why Balanced Windows Matter

At first, the window builder filled the dataset from the first series before
moving to later series. That would make the adapter mostly learn VIX.

We fixed it by round-robin sampling windows across all series.

This round's final training windows:

```text
10 series
500 windows per series
5000 total windows
```

Lesson: data balance is part of model training. A LoRA adapter can only learn
the distribution we actually show it.

## 8. What We Ran

The real training command was equivalent to:

```bash
uv run python scripts/finetune_lora.py \
  --csv data/market/daily_market_series.csv \
  --field level \
  --model-id .hf-cache/timesfm-2.5-200m-transformers \
  --context-len 128 \
  --horizon-len 20 \
  --batch-size 2 \
  --max-steps 200 \
  --log-every 20 \
  --lora-r 4 \
  --lora-alpha 8 \
  --output-dir adapters/market-macro-level-h20-r4-step200-balanced
```

The adapter created by this run:

```text
adapters/market-macro-level-h20-r4-step200-balanced
```

## 9. What Actually Trained

Observed parameter count:

```text
all params: 232,672,192
trainable params: 1,382,912
trainable percent: 0.5944%
```

Meaning:

```text
99.4056% of TimesFM did not change.
0.5944% was trained as the LoRA adapter.
```

This is the central LoRA idea.

We are not creating a new TimesFM from scratch.

We are creating a small specialized adapter on top of TimesFM.

## 10. What The Metrics Mean

We used two error metrics:

```text
MAE = mean absolute error
SMAPE = symmetric mean absolute percentage error
```

Lower is better for both.

MAE answers:

```text
How far away are predictions in raw units?
```

SMAPE answers:

```text
How large is the error relative to the scale of the value?
```

## 11. Why We Need Baselines

A model is only useful if it beats simple alternatives.

This round compared against:

```text
last-value naive
seasonal naive
TimesFM 2.5 zero-shot
TimesFM 2.5 + LoRA adapter
```

`last-value naive` means:

```text
Predict every future point as the last observed point.
```

`zero-shot` means:

```text
Use TimesFM 2.5 without any LoRA adapter.
```

If LoRA cannot beat zero-shot, the adapter is not useful yet.

## 12. Results From This Round

Naive baseline over 5000 balanced windows:

```text
last_value MAE   = 5.370801646
last_value SMAPE = 0.05623413994392316
```

TimesFM 2.5 zero-shot over 200 balanced windows:

```text
MAE   = 3.352549499458163
SMAPE = 0.043185524621834885
```

TimesFM 2.5 + LoRA r4 step200 over the same 200 windows:

```text
MAE   = 3.2645185147089473
SMAPE = 0.0415481501766979
```

Interpretation:

```text
LoRA improved MAE by about 0.0880.
LoRA improved SMAPE by about 0.00164.
```

The improvement is real in this small evaluation, but not enough to declare the
adapter generally stronger.

## 13. What This Round Proved

Fact:

```text
The full local pipeline works:
data fetch -> window build -> baseline -> TimesFM load -> LoRA train -> adapter save -> evaluation
```

Fact:

```text
The r=4 adapter can train on Apple Silicon MPS.
```

Fact:

```text
The trained adapter slightly beat zero-shot on the small balanced evaluation.
```

Inference:

```text
The market-macro-risk domain has enough signal to justify a second round.
```

Not proven yet:

```text
The adapter generalizes across time.
The adapter is production-ready.
The adapter helps downstream trading decisions.
The adapter beats zero-shot under strict rolling backtest.
```

## 14. What To Learn Next

Next LoRA concepts to learn through the next run:

```text
train / validation / test split
rolling backtest
overfitting
adapter capacity r=4 vs r=8
why lower training loss can still produce worse forecasts
```

Recommended next experiment:

```text
Keep r=4.
Increase steps to 1000.
Add strict time-based validation.
Compare against the same zero-shot windows.
Only after that try r=8.
```

## 15. One-Sentence Summary

LoRA lets us keep TimesFM 2.5 frozen and train a small domain adapter; this
round proved the Time0 pipeline works and produced the first market-macro-risk
adapter with a small measured improvement over zero-shot.
