from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from forecast_data import ForecastWindow, build_windows, count_windows_by_series, load_series_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--train-windows", type=int, required=True)
    parser.add_argument("--holdout-windows", type=int, default=500)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        raise ValueError("cannot compute percentile for empty values")
    index = quantile * (len(sorted_values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def summarize_values(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise ValueError("cannot summarize empty values")
    sorted_values = sorted(values)
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "count": len(values),
        "mean": mean,
        "std": math.sqrt(variance),
        "min": sorted_values[0],
        "p10": percentile(sorted_values, 0.10),
        "p50": percentile(sorted_values, 0.50),
        "p90": percentile(sorted_values, 0.90),
        "max": sorted_values[-1],
    }


def future_values(windows: list[ForecastWindow]) -> list[float]:
    values: list[float] = []
    for window in windows:
        values.extend(window.future)
    return values


def group_windows_by_series(windows: list[ForecastWindow]) -> dict[str, list[ForecastWindow]]:
    grouped: dict[str, list[ForecastWindow]] = {}
    for window in windows:
        grouped.setdefault(window.series_id, []).append(window)
    return grouped


def relative_delta(after: float, before: float) -> float:
    if before == 0:
        return math.inf if after != 0 else 0.0
    return (after - before) / abs(before)


def main() -> None:
    args = parse_args()
    grouped = load_series_csv(Path(args.csv), field=args.field)
    train_windows = build_windows(
        grouped,
        context_len=args.context_len,
        horizon_len=args.horizon_len,
        max_windows=args.train_windows,
        skip_windows=0,
    )
    holdout_windows = build_windows(
        grouped,
        context_len=args.context_len,
        horizon_len=args.horizon_len,
        max_windows=args.holdout_windows,
        skip_windows=args.train_windows,
    )
    if not train_windows:
        raise SystemExit("no training windows; lower context/horizon or provide more data")
    if not holdout_windows:
        raise SystemExit("no holdout windows; lower context/horizon or provide more data")

    train_by_series = group_windows_by_series(train_windows)
    holdout_by_series = group_windows_by_series(holdout_windows)
    per_series = {}
    for series_id in sorted(set(train_by_series) | set(holdout_by_series)):
        train_summary = summarize_values(future_values(train_by_series.get(series_id, [])))
        holdout_summary = summarize_values(future_values(holdout_by_series.get(series_id, [])))
        train_mean = float(train_summary["mean"])
        holdout_mean = float(holdout_summary["mean"])
        train_std = float(train_summary["std"])
        holdout_std = float(holdout_summary["std"])
        per_series[series_id] = {
            "train_windows": len(train_by_series.get(series_id, [])),
            "holdout_windows": len(holdout_by_series.get(series_id, [])),
            "train": train_summary,
            "holdout": holdout_summary,
            "holdout_vs_train": {
                "mean_delta": holdout_mean - train_mean,
                "mean_delta_pct": relative_delta(holdout_mean, train_mean) * 100,
                "std_delta": holdout_std - train_std,
                "std_ratio": holdout_std / train_std if train_std else math.inf,
                "p90_delta": float(holdout_summary["p90"]) - float(train_summary["p90"]),
            },
        }

    train_overall = summarize_values(future_values(train_windows))
    holdout_overall = summarize_values(future_values(holdout_windows))
    report = {
        "field": args.field,
        "context_len": args.context_len,
        "horizon_len": args.horizon_len,
        "train_windows": len(train_windows),
        "holdout_windows": len(holdout_windows),
        "holdout_skip_windows": args.train_windows,
        "train_windows_by_series": count_windows_by_series(train_windows),
        "holdout_windows_by_series": count_windows_by_series(holdout_windows),
        "distribution_grain": "window_future_values",
        "overall": {
            "train": train_overall,
            "holdout": holdout_overall,
            "holdout_vs_train": {
                "mean_delta_pct": relative_delta(float(holdout_overall["mean"]), float(train_overall["mean"])) * 100,
                "std_ratio": float(holdout_overall["std"]) / float(train_overall["std"]),
            },
        },
        "per_series": per_series,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
