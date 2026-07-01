from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rolling_grid import (
    ALL_CUTS,
    FAMILIES,
    GRID_CHOICES,
    archive_jobs,
    predictions_path,
    report_path,
    selected_cuts,
    selected_families,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/market/daily_market_series.csv")
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--model-id", default=".hf-cache/timesfm-2.5-200m-transformers")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--max-windows", type=int, default=500)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--grid", choices=GRID_CHOICES, default="base")
    parser.add_argument("--cut", action="append", type=int, choices=ALL_CUTS)
    parser.add_argument("--family", action="append", choices=FAMILIES)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def command_for(args: argparse.Namespace, job) -> list[str]:
    command = [
        sys.executable,
        "scripts/evaluate_timesfm.py",
        "--csv",
        args.csv,
        "--field",
        args.field,
        "--model-id",
        args.model_id,
        "--context-len",
        str(args.context_len),
        "--horizon-len",
        str(args.horizon_len),
        "--max-windows",
        str(args.max_windows),
        "--skip-windows",
        str(job.cut),
        "--device",
        args.device,
        "--output",
        str(report_path(job)),
        "--predictions-output",
        str(predictions_path(job)),
    ]
    if job.adapter_dir:
        command.extend(["--adapter-dir", job.adapter_dir])
    return command


def main() -> None:
    args = parse_args()
    root = experiment_root()
    cuts = selected_cuts(grid=args.grid, selected=args.cut)
    families = selected_families(args.family)
    jobs = archive_jobs(cuts=cuts, families=families)
    if not jobs:
        raise SystemExit("no export jobs selected")

    for index, job in enumerate(jobs, start=1):
        report = root / report_path(job)
        predictions = root / predictions_path(job)
        if not args.overwrite and report.exists() and predictions.exists():
            print(f"[archive] skip existing {index}/{len(jobs)} family={job.family} cut={job.cut}")
            continue
        if not args.dry_run and job.adapter_dir and not (root / job.adapter_dir).exists():
            raise FileNotFoundError(f"missing adapter for family={job.family} cut={job.cut}: {root / job.adapter_dir}")

        command = command_for(args, job)
        print(f"[archive] run {index}/{len(jobs)} family={job.family} cut={job.cut}")
        print(" ".join(command))
        if args.dry_run:
            continue
        subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
