from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from forecast_data import ForecastWindowDataset, build_windows, count_windows_by_series, load_series_csv
from torch.utils.data import DataLoader


@dataclass(frozen=True)
class TrainConfig:
    csv: str
    field: str
    model_id: str
    output_dir: str
    seed: int
    max_windows: int
    skip_windows: int
    context_len: int
    horizon_len: int
    batch_size: int
    max_steps: int
    log_every: int
    learning_rate: float
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    device: str
    inspect_data_only: bool


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--model-id", default="google/timesfm-2.5-200m-transformers")
    parser.add_argument("--output-dir", default="adapters/market-vol-h20-r4")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-windows", type=int, default=5000)
    parser.add_argument("--skip-windows", type=int, default=0)
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--lora-r", type=int, default=4)
    parser.add_argument("--lora-alpha", type=int, default=8)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--inspect-data-only", action="store_true")
    args = parser.parse_args()
    return TrainConfig(
        csv=args.csv,
        field=args.field,
        model_id=args.model_id,
        output_dir=args.output_dir,
        seed=args.seed,
        max_windows=args.max_windows,
        skip_windows=args.skip_windows,
        context_len=args.context_len,
        horizon_len=args.horizon_len,
        batch_size=args.batch_size,
        max_steps=args.max_steps,
        log_every=args.log_every,
        learning_rate=args.learning_rate,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        device=args.device,
        inspect_data_only=args.inspect_data_only,
    )


def select_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def collate_batch(batch: list[tuple[torch.Tensor, torch.Tensor]], device: torch.device) -> tuple[list[torch.Tensor], torch.Tensor]:
    past_values = [past.to(device) for past, _ in batch]
    future_values = torch.stack([future for _, future in batch], dim=0).to(device)
    return past_values, future_values


def main() -> None:
    cfg = parse_args()
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    root = Path(__file__).resolve().parents[1]
    csv_path = (root / cfg.csv).resolve() if not Path(cfg.csv).is_absolute() else Path(cfg.csv)
    grouped = load_series_csv(csv_path, field=cfg.field)
    windows = build_windows(
        grouped,
        context_len=cfg.context_len,
        horizon_len=cfg.horizon_len,
        max_windows=cfg.max_windows,
        skip_windows=cfg.skip_windows,
    )

    print(f"[data] field={cfg.field} series={len(grouped)} windows={len(windows)}")
    print(f"[data] skip_windows={cfg.skip_windows}")
    print(f"[data] windows_by_series={json.dumps(count_windows_by_series(windows), sort_keys=True)}")
    print(f"[data] context_len={cfg.context_len} horizon_len={cfg.horizon_len}")
    if not windows:
        raise SystemExit("no forecast windows; lower context/horizon or provide more data")
    if cfg.inspect_data_only:
        return

    from peft import LoraConfig, get_peft_model
    from transformers import TimesFm2_5ModelForPrediction

    output_dir = (root / cfg.output_dir).resolve() if not Path(cfg.output_dir).is_absolute() else Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = select_device(cfg.device)
    print(f"[train] device={device}")
    print(f"[lora] r={cfg.lora_r} alpha={cfg.lora_alpha} dropout={cfg.lora_dropout}")

    dataset = ForecastWindowDataset(windows)
    loader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=True, collate_fn=lambda batch: batch)
    model = TimesFm2_5ModelForPrediction.from_pretrained(cfg.model_id, torch_dtype=torch.float32)
    model.to(device)

    lora_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        lora_dropout=cfg.lora_dropout,
        target_modules="all-linear",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    model.train()

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate)
    losses: list[float] = []
    started = time.time()
    step = 0

    while step < cfg.max_steps:
        for raw_batch in loader:
            past_values, future_values = collate_batch(raw_batch, device)
            optimizer.zero_grad(set_to_none=True)
            output = model(
                past_values=past_values,
                future_values=future_values,
                forecast_context_len=cfg.context_len,
                return_dict=True,
            )
            loss = output.loss
            loss.backward()
            optimizer.step()
            step += 1
            loss_value = float(loss.detach().cpu())
            losses.append(loss_value)
            if step == 1 or step == cfg.max_steps or step % cfg.log_every == 0:
                print(f"[train] step={step} loss={loss_value:.8f}")
            if step >= cfg.max_steps:
                break

    model.save_pretrained(output_dir)
    summary = {
        "config": asdict(cfg),
        "device": str(device),
        "series": len(grouped),
        "windows": len(windows),
        "skip_windows": cfg.skip_windows,
        "windows_by_series": count_windows_by_series(windows),
        "losses": losses,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    (output_dir / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[done] saved adapter to {output_dir}")


if __name__ == "__main__":
    main()
