from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rolling_grid import (
    ALL_CUTS,
    DEFAULT_ADAPTER_PREFIX,
    DEFAULT_FULL_BALANCED_ADAPTER,
    FAMILIES,
    GRID_CHOICES,
    selected_cuts,
    selected_families,
    train_jobs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/market/daily_market_series.csv")
    parser.add_argument("--csv-template")
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--field-template")
    parser.add_argument("--adapter-prefix", default=DEFAULT_ADAPTER_PREFIX)
    parser.add_argument("--full-balanced-adapter", default=DEFAULT_FULL_BALANCED_ADAPTER)
    parser.add_argument("--no-full-balanced-adapter", action="store_true")
    parser.add_argument("--model-id", default=".hf-cache/timesfm-2.5-200m-transformers")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--lora-r", type=int, default=4)
    parser.add_argument("--lora-alpha", type=int, default=8)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--grid", choices=GRID_CHOICES, default="expanded")
    parser.add_argument("--cut", action="append", type=int, choices=ALL_CUTS)
    parser.add_argument("--family", action="append", choices=FAMILIES)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def formatted(value: str, *, cut: int) -> str:
    return value.format(cut=cut)


def command_for(args: argparse.Namespace, job) -> list[str]:
    csv_path = formatted(args.csv_template or args.csv, cut=job.cut)
    field = formatted(args.field_template or args.field, cut=job.cut)
    return [
        sys.executable,
        "scripts/finetune_lora.py",
        "--csv",
        csv_path,
        "--field",
        field,
        "--model-id",
        args.model_id,
        "--output-dir",
        job.output_dir,
        "--max-windows",
        str(job.max_windows),
        "--skip-windows",
        str(job.skip_windows),
        "--context-len",
        str(args.context_len),
        "--horizon-len",
        str(args.horizon_len),
        "--batch-size",
        str(args.batch_size),
        "--max-steps",
        str(args.max_steps),
        "--log-every",
        str(args.log_every),
        "--learning-rate",
        str(args.learning_rate),
        "--lora-r",
        str(args.lora_r),
        "--lora-alpha",
        str(args.lora_alpha),
        "--lora-dropout",
        str(args.lora_dropout),
        "--device",
        args.device,
    ]


def main() -> None:
    args = parse_args()
    root = experiment_root()
    cuts = selected_cuts(grid=args.grid, selected=args.cut)
    families = selected_families(args.family)
    full_balanced_adapter = None if args.no_full_balanced_adapter else args.full_balanced_adapter
    jobs = train_jobs(
        cuts=cuts,
        families=families,
        adapter_prefix=args.adapter_prefix,
        full_balanced_adapter=full_balanced_adapter,
    )
    if not jobs:
        raise SystemExit("no train jobs selected")

    for index, job in enumerate(jobs, start=1):
        output_dir = root / job.output_dir
        summary_path = output_dir / "training_summary.json"
        if not args.overwrite and summary_path.exists():
            print(f"[train-grid] skip existing {index}/{len(jobs)} family={job.family} cut={job.cut}")
            continue

        command = command_for(args, job)
        print(
            "[train-grid] run "
            f"{index}/{len(jobs)} family={job.family} cut={job.cut} "
            f"max_windows={job.max_windows} skip_windows={job.skip_windows}"
        )
        print(" ".join(command))
        if args.dry_run:
            continue
        subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
