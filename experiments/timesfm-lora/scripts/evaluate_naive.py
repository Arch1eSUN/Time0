from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from forecast_data import build_windows, count_windows_by_series, load_series_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--max-windows", type=int, default=5000)
    parser.add_argument("--skip-windows", type=int, default=0)
    parser.add_argument("--seasonal-lag", type=int, default=20)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def mae(actual: list[float], predicted: list[float]) -> float:
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def smape(actual: list[float], predicted: list[float]) -> float:
    total = 0.0
    for a, p in zip(actual, predicted):
        denominator = (abs(a) + abs(p)) / 2
        total += 0.0 if denominator == 0 else abs(a - p) / denominator
    return total / len(actual)


def metric_report(actual: list[float], predicted: list[float]) -> dict[str, float]:
    return {
        "mae": mae(actual, predicted),
        "smape": smape(actual, predicted),
    }


@dataclass
class NaiveSeriesAccumulator:
    windows: int = 0
    last_actual: list[float] = field(default_factory=list)
    last_predicted: list[float] = field(default_factory=list)
    seasonal_actual: list[float] = field(default_factory=list)
    seasonal_predicted: list[float] = field(default_factory=list)


def main() -> None:
    args = parse_args()
    grouped = load_series_csv(Path(args.csv), field=args.field)
    windows = build_windows(
        grouped,
        context_len=args.context_len,
        horizon_len=args.horizon_len,
        max_windows=args.max_windows,
        skip_windows=args.skip_windows,
    )
    if not windows:
        raise SystemExit("no forecast windows; lower context/horizon or provide more data")

    last_actual: list[float] = []
    last_predicted: list[float] = []
    seasonal_actual: list[float] = []
    seasonal_predicted: list[float] = []
    per_series: dict[str, NaiveSeriesAccumulator] = {}

    for window in windows:
        series_metrics = per_series.setdefault(window.series_id, NaiveSeriesAccumulator())
        series_metrics.windows += 1

        last_value = window.past[-1]
        for actual in window.future:
            last_actual.append(actual)
            last_predicted.append(last_value)
            series_metrics.last_actual.append(actual)
            series_metrics.last_predicted.append(last_value)

        seasonal_source = window.past[-args.seasonal_lag :] if len(window.past) >= args.seasonal_lag else window.past
        seasonal_values = list(seasonal_source)
        while len(seasonal_values) < len(window.future):
            seasonal_values.extend(seasonal_source)
        for actual, predicted in zip(window.future, seasonal_values[: len(window.future)]):
            seasonal_actual.append(actual)
            seasonal_predicted.append(predicted)
            series_metrics.seasonal_actual.append(actual)
            series_metrics.seasonal_predicted.append(predicted)

    per_series_report = {}
    for series_id, values in sorted(per_series.items()):
        per_series_report[series_id] = {
            "windows": values.windows,
            "last_value": metric_report(values.last_actual, values.last_predicted),
            "seasonal_naive": {
                "lag": args.seasonal_lag,
                **metric_report(values.seasonal_actual, values.seasonal_predicted),
            },
        }

    report = {
        "field": args.field,
        "context_len": args.context_len,
        "horizon_len": args.horizon_len,
        "windows": len(windows),
        "skip_windows": args.skip_windows,
        "series": len(grouped),
        "windows_by_series": count_windows_by_series(windows),
        "last_value": {
            "mae": mae(last_actual, last_predicted),
            "smape": smape(last_actual, last_predicted),
        },
        "seasonal_naive": {
            "lag": args.seasonal_lag,
            **metric_report(seasonal_actual, seasonal_predicted),
        },
        "per_series": per_series_report,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
