from __future__ import annotations

import argparse
import json
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
    with torch.no_grad():
        for index, window in enumerate(windows, start=1):
            past = torch.tensor(window.past, dtype=torch.float32, device=device)
            output = model(
                past_values=[past],
                forecast_context_len=args.context_len,
                return_dict=True,
            )
            forecast = output.mean_predictions[0, : args.horizon_len].detach().cpu().tolist()
            actual.extend(window.future)
            predicted.extend(float(value) for value in forecast)
            if index % 25 == 0:
                print(f"[eval] windows={index}")

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
        "mae": mae(actual, predicted),
        "smape": smape(actual, predicted),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
