from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


CUTS = (4000, 5000, 5500)
FAMILIES = ("zero-shot", "full", "recent1500", "recent2000", "recent3000")

ADAPTERS: dict[str, dict[int, str | None]] = {
    "zero-shot": {
        4000: None,
        5000: None,
        5500: None,
    },
    "full": {
        4000: "adapters/market-macro-realized-vol-20-h20-r4-step200-train4000",
        5000: "adapters/market-macro-realized-vol-20-h20-r4-step200-balanced",
        5500: "adapters/market-macro-realized-vol-20-h20-r4-step200-train5500",
    },
    "recent1500": {
        4000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train4000",
        5000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train5000",
        5500: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent1500-train5500",
    },
    "recent2000": {
        4000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train4000",
        5000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train5000",
        5500: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent2000-train5500",
    },
    "recent3000": {
        4000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train4000",
        5000: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train5000",
        5500: "adapters/market-macro-realized-vol-20-h20-r4-step200-recent3000-train5500",
    },
}


@dataclass(frozen=True)
class ArchiveJob:
    family: str
    cut: int
    adapter_dir: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/market/daily_market_series.csv")
    parser.add_argument("--field", default="realized_vol_20")
    parser.add_argument("--model-id", default=".hf-cache/timesfm-2.5-200m-transformers")
    parser.add_argument("--context-len", type=int, default=128)
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--max-windows", type=int, default=500)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--cut", action="append", type=int, choices=CUTS)
    parser.add_argument("--family", action="append", choices=FAMILIES)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def selected_values(values: tuple[int, ...] | tuple[str, ...], selected: list[int] | list[str] | None) -> list:
    if not selected:
        return list(values)
    return [value for value in values if value in selected]


def build_jobs(args: argparse.Namespace) -> list[ArchiveJob]:
    cuts = selected_values(CUTS, args.cut)
    families = selected_values(FAMILIES, args.family)
    return [ArchiveJob(family=family, cut=cut, adapter_dir=ADAPTERS[family][cut]) for cut in cuts for family in families]


def slug_for(job: ArchiveJob) -> str:
    return f"market-macro-realized-vol-20-h20-r4-{job.family}-holdout500-skip{job.cut}"


def report_path(job: ArchiveJob) -> Path:
    return Path("reports") / f"archive-export-timesfm-{slug_for(job)}.json"


def predictions_path(job: ArchiveJob) -> Path:
    return Path("reports") / f"predictions-timesfm-{slug_for(job)}.json"


def command_for(args: argparse.Namespace, job: ArchiveJob) -> list[str]:
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
    jobs = build_jobs(args)
    if not jobs:
        raise SystemExit("no export jobs selected")

    for index, job in enumerate(jobs, start=1):
        report = root / report_path(job)
        predictions = root / predictions_path(job)
        if not args.overwrite and report.exists() and predictions.exists():
            print(f"[archive] skip existing {index}/{len(jobs)} family={job.family} cut={job.cut}")
            continue

        command = command_for(args, job)
        print(f"[archive] run {index}/{len(jobs)} family={job.family} cut={job.cut}")
        print(" ".join(command))
        if args.dry_run:
            continue
        subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
