from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import torch
from forecast_data import build_windows, count_windows_by_series, load_series_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--field", default="level")
    parser.add_argument("--model-id", default=".hf-cache/timesfm-2.5-200m-transformers")
    parser.add_argument("--adapter-dir")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--max-windows", type=int, default=200)
    parser.add_argument("--skip-windows", type=int, default=0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", required=True)
    parser.add_argument("--predictions-output")
    return parser.parse_args()


def select_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


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


def mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values)


def stddev(values: tuple[float, ...], current_mean: float) -> float:
    variance = sum((value - current_mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def context_features(past: tuple[float, ...]) -> dict[str, float]:
    current_mean = mean(past)
    return {
        "past_last": past[-1],
        "past_mean": current_mean,
        "past_std": stddev(past, current_mean),
        "past_min": min(past),
        "past_max": max(past),
        "past_trend": past[-1] - past[0],
    }


@dataclass
class SeriesAccumulator:
    windows: int = 0
    actual: list[float] = field(default_factory=list)
    predicted: list[float] = field(default_factory=list)


def main() -> None:
    args = parse_args()
    device = select_device(args.device)
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

    from transformers import TimesFm2_5ModelForPrediction

    model = TimesFm2_5ModelForPrediction.from_pretrained(args.model_id, torch_dtype=torch.float32)
    if args.adapter_dir:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter_dir)
    model.to(device)
    model.eval()

    actual: list[float] = []
    predicted: list[float] = []
    prediction_records: list[dict[str, object]] = []
    per_series: dict[str, SeriesAccumulator] = {}
    with torch.no_grad():
        for index, window in enumerate(windows, start=1):
            past = torch.tensor(window.past, dtype=torch.float32, device=device)
            output = model(
                past_values=[past],
                forecast_context_len=args.context_len,
                return_dict=True,
            )
            forecast = output.mean_predictions[0, : args.horizon_len].detach().cpu().tolist()
            forecast_values = [float(value) for value in forecast]
            actual_values = list(window.future)
            actual.extend(window.future)
            predicted.extend(forecast_values)
            series_metrics = per_series.setdefault(window.series_id, SeriesAccumulator())
            series_metrics.windows += 1
            series_metrics.actual.extend(window.future)
            series_metrics.predicted.extend(forecast_values)
            if args.predictions_output:
                prediction_records.append(
                    {
                        "window_id": f"{window.series_id}:{window.start_index}",
                        "window_index": index,
                        "series_id": window.series_id,
                        "start_index": window.start_index,
                        "field": args.field,
                        "model_id": args.model_id,
                        "adapter_dir": args.adapter_dir,
                        "context_len": args.context_len,
                        "horizon_len": args.horizon_len,
                        "skip_windows": args.skip_windows,
                        "features": context_features(window.past),
                        "actual": actual_values,
                        "predicted": forecast_values,
                        **metric_report(actual_values, forecast_values),
                    }
                )
            if index % 25 == 0:
                print(f"[eval] windows={index}")

    per_series_report = {}
    for series_id, values in sorted(per_series.items()):
        per_series_report[series_id] = {
            "windows": values.windows,
            **metric_report(values.actual, values.predicted),
        }

    report = {
        "field": args.field,
        "model_id": args.model_id,
        "adapter_dir": args.adapter_dir,
        "context_len": args.context_len,
        "horizon_len": args.horizon_len,
        "windows": len(windows),
        "skip_windows": args.skip_windows,
        "windows_by_series": count_windows_by_series(windows),
        "device": str(device),
        **metric_report(actual, predicted),
        "per_series": per_series_report,
    }
    if args.predictions_output:
        predictions_output = Path(args.predictions_output)
        predictions_output.parent.mkdir(parents=True, exist_ok=True)
        predictions_archive = {
            "field": args.field,
            "model_id": args.model_id,
            "adapter_dir": args.adapter_dir,
            "context_len": args.context_len,
            "horizon_len": args.horizon_len,
            "windows": len(prediction_records),
            "skip_windows": args.skip_windows,
            "device": str(device),
            "records": prediction_records,
        }
        predictions_output.write_text(json.dumps(predictions_archive, indent=2) + "\n")
        report["predictions_output"] = str(predictions_output)
        report["prediction_records"] = len(prediction_records)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
