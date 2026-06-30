from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import Dataset


@dataclass(frozen=True)
class ForecastWindow:
    series_id: str
    start_index: int
    past: tuple[float, ...]
    future: tuple[float, ...]


def load_series_csv(
    path: Path,
    *,
    field: str,
    series_column: str = "series_id",
    time_column: str = "timestamp",
    field_column: str = "field",
    value_column: str = "value",
) -> dict[str, list[tuple[str, float]]]:
    grouped: dict[str, list[tuple[str, float]]] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {series_column, time_column, field_column, value_column}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")
        for row in reader:
            if row[field_column] != field:
                continue
            try:
                value = float(row[value_column])
            except ValueError:
                continue
            if not math.isfinite(value):
                continue
            grouped.setdefault(row[series_column], []).append((row[time_column], value))

    return {key: sorted(values, key=lambda item: item[0]) for key, values in grouped.items()}


def build_windows(
    grouped: dict[str, list[tuple[str, float]]],
    *,
    context_len: int,
    horizon_len: int,
    max_windows: int,
    skip_windows: int = 0,
) -> list[ForecastWindow]:
    series_windows: list[list[ForecastWindow]] = []
    width = context_len + horizon_len
    for series_id, values in grouped.items():
        numeric_values = [value for _, value in values]
        if len(numeric_values) < width:
            continue
        current_windows: list[ForecastWindow] = []
        for start_index in range(0, len(numeric_values) - width + 1):
            past = tuple(numeric_values[start_index : start_index + context_len])
            future = tuple(numeric_values[start_index + context_len : start_index + width])
            current_windows.append(ForecastWindow(series_id, start_index, past, future))
        series_windows.append(current_windows)

    selected_windows: list[ForecastWindow] = []
    seen_windows = 0
    offset = 0
    while len(selected_windows) < max_windows:
        added = 0
        for current_windows in series_windows:
            if offset < len(current_windows):
                if seen_windows >= skip_windows:
                    selected_windows.append(current_windows[offset])
                    if len(selected_windows) >= max_windows:
                        return selected_windows
                seen_windows += 1
                added += 1
        if added == 0:
            return selected_windows
        offset += 1
    return selected_windows


class ForecastWindowDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, windows: list[ForecastWindow]) -> None:
        self.windows = windows

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        window = self.windows[index]
        past = torch.tensor(window.past, dtype=torch.float32)
        future = torch.tensor(window.future, dtype=torch.float32)
        return past, future


def count_windows_by_series(windows: list[ForecastWindow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for window in windows:
        counts[window.series_id] = counts.get(window.series_id, 0) + 1
    return counts
