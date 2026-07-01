from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from forecast_data import ForecastWindow, build_windows, count_windows_by_series, load_series_csv


@dataclass(frozen=True)
class NormalizationStats:
    mean: float
    std: float
    count: int
    train_windows: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--output-field")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--train-windows", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    return parser.parse_args()


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return Path(__file__).resolve().parents[1] / raw_path


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


def compute_stats(train_windows: list[ForecastWindow]) -> dict[str, NormalizationStats]:
    grouped = group_windows_by_series(train_windows)
    stats: dict[str, NormalizationStats] = {}
    for series_id, windows in sorted(grouped.items()):
        values = future_values(windows)
        if not values:
            raise ValueError(f"no train future values for {series_id}")
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std = math.sqrt(variance)
        if std == 0 or not math.isfinite(std):
            raise ValueError(f"invalid train std for {series_id}: {std}")
        stats[series_id] = NormalizationStats(
            mean=mean,
            std=std,
            count=len(values),
            train_windows=len(windows),
        )
    return stats


def source_symbol_for(row: dict[str, str]) -> str:
    source_symbol = row.get("source_symbol", "")
    if source_symbol:
        return source_symbol
    return row["series_id"].split(":", maxsplit=1)[0]


def write_normalized_csv(
    *,
    input_path: Path,
    output_path: Path,
    field: str,
    output_field: str,
    stats: dict[str, NormalizationStats],
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with input_path.open(newline="") as input_handle, output_path.open("w", newline="") as output_handle:
        reader = csv.DictReader(input_handle)
        required = {"series_id", "timestamp", "field", "value"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")

        fieldnames = ["series_id", "timestamp", "field", "value", "source_symbol", "source"]
        writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            if row["field"] != field:
                continue
            try:
                value = float(row["value"])
            except ValueError:
                continue
            if not math.isfinite(value):
                continue

            series_id = row["series_id"]
            if series_id not in stats:
                raise ValueError(f"missing normalization stats for {series_id}")
            current_stats = stats[series_id]
            source_symbol = source_symbol_for(row)
            normalized = (value - current_stats.mean) / current_stats.std
            writer.writerow(
                {
                    "series_id": f"{source_symbol}:{output_field}",
                    "timestamp": row["timestamp"],
                    "field": output_field,
                    "value": f"{normalized:.10f}",
                    "source_symbol": source_symbol,
                    "source": row.get("source", ""),
                }
            )
            rows_written += 1
    return rows_written


def main() -> None:
    args = parse_args()
    input_path = experiment_path(args.csv).resolve()
    output_path = experiment_path(args.output).resolve()
    metadata_path = experiment_path(args.metadata).resolve()
    output_field = args.output_field or f"{args.field}_zscore_train{args.train_windows}"

    grouped = load_series_csv(input_path, field=args.field)
    train_windows = build_windows(
        grouped,
        context_len=args.context_len,
        horizon_len=args.horizon_len,
        max_windows=args.train_windows,
        skip_windows=0,
    )
    if len(train_windows) != args.train_windows:
        raise SystemExit(f"expected {args.train_windows} train windows, got {len(train_windows)}")

    stats = compute_stats(train_windows)
    missing_stats = set(grouped).difference(stats)
    if missing_stats:
        raise SystemExit(f"missing train stats for series: {sorted(missing_stats)}")

    rows_written = write_normalized_csv(
        input_path=input_path,
        output_path=output_path,
        field=args.field,
        output_field=output_field,
        stats=stats,
    )

    metadata = {
        "input_csv": str(input_path),
        "output_csv": str(output_path),
        "base_field": args.field,
        "output_field": output_field,
        "context_len": args.context_len,
        "horizon_len": args.horizon_len,
        "train_windows": len(train_windows),
        "train_windows_by_series": count_windows_by_series(train_windows),
        "normalization_grain": "train_window_future_values",
        "formula": "z = (value - train_future_mean) / train_future_std",
        "rows_written": rows_written,
        "per_series": {series_id: asdict(value) for series_id, value in sorted(stats.items())},
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
