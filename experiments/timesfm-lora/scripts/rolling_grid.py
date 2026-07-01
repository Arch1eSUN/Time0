from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_CUTS = (4000, 5000, 5500)
EXPANDED_EXTRA_CUTS = (3500, 3750, 4250, 4500, 4750, 5250)
EXPANDED_CUTS = tuple(sorted(BASE_CUTS + EXPANDED_EXTRA_CUTS))
ALL_CUTS = EXPANDED_CUTS

FAMILIES = ("zero-shot", "full", "recent1500", "recent2000", "recent3000")
GRID_CHOICES = ("base", "expanded")

RECENT_WINDOWS = {
    "recent1500": 1500,
    "recent2000": 2000,
    "recent3000": 3000,
}


@dataclass(frozen=True)
class ArchiveJob:
    family: str
    cut: int
    adapter_dir: str | None


@dataclass(frozen=True)
class TrainJob:
    family: str
    cut: int
    output_dir: str
    max_windows: int
    skip_windows: int


def cuts_for_grid(grid: str) -> tuple[int, ...]:
    if grid == "base":
        return BASE_CUTS
    if grid == "expanded":
        return EXPANDED_CUTS
    raise ValueError(f"unsupported grid: {grid}")


def selected_cuts(*, grid: str, selected: list[int] | None) -> list[int]:
    allowed = cuts_for_grid(grid)
    if not selected:
        return list(allowed)
    invalid = sorted(set(selected).difference(ALL_CUTS))
    if invalid:
        raise ValueError(f"unsupported cuts: {invalid}")
    outside_grid = sorted(set(selected).difference(allowed))
    if outside_grid:
        raise ValueError(f"cuts are not in {grid} grid: {outside_grid}")
    return [cut for cut in allowed if cut in selected]


def selected_families(selected: list[str] | None) -> list[str]:
    if not selected:
        return list(FAMILIES)
    invalid = sorted(set(selected).difference(FAMILIES))
    if invalid:
        raise ValueError(f"unsupported families: {invalid}")
    return [family for family in FAMILIES if family in selected]


def adapter_dir_for(family: str, cut: int) -> str | None:
    if family == "zero-shot":
        return None
    if family == "full":
        if cut == 5000:
            return "adapters/market-macro-realized-vol-20-h20-r4-step200-balanced"
        return f"adapters/market-macro-realized-vol-20-h20-r4-step200-train{cut}"
    if family in RECENT_WINDOWS:
        return f"adapters/market-macro-realized-vol-20-h20-r4-step200-{family}-train{cut}"
    raise ValueError(f"unsupported family: {family}")


def train_job_for(family: str, cut: int) -> TrainJob | None:
    adapter_dir = adapter_dir_for(family, cut)
    if adapter_dir is None:
        return None
    if family == "full":
        return TrainJob(
            family=family,
            cut=cut,
            output_dir=adapter_dir,
            max_windows=cut,
            skip_windows=0,
        )
    if family in RECENT_WINDOWS:
        window_count = RECENT_WINDOWS[family]
        return TrainJob(
            family=family,
            cut=cut,
            output_dir=adapter_dir,
            max_windows=window_count,
            skip_windows=max(0, cut - window_count),
        )
    raise ValueError(f"unsupported family: {family}")


def archive_jobs(*, cuts: list[int], families: list[str]) -> list[ArchiveJob]:
    return [
        ArchiveJob(family=family, cut=cut, adapter_dir=adapter_dir_for(family, cut))
        for cut in cuts
        for family in families
    ]


def train_jobs(*, cuts: list[int], families: list[str]) -> list[TrainJob]:
    jobs: list[TrainJob] = []
    for cut in cuts:
        for family in families:
            job = train_job_for(family, cut)
            if job is not None:
                jobs.append(job)
    return jobs


def slug_for(job: ArchiveJob) -> str:
    return f"market-macro-realized-vol-20-h20-r4-{job.family}-holdout500-skip{job.cut}"


def report_path(job: ArchiveJob) -> Path:
    return Path("reports") / f"archive-export-timesfm-{slug_for(job)}.json"


def predictions_path(job: ArchiveJob) -> Path:
    return Path("reports") / f"predictions-timesfm-{slug_for(job)}.json"
