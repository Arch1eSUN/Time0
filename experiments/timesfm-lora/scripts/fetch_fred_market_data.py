from __future__ import annotations

import argparse
import csv
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--series-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    return parser.parse_args()


def read_series_ids(path: Path) -> list[str]:
    series_ids = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if line:
            series_ids.append(line)
    return series_ids


def fetch_series(series_id: str) -> list[tuple[str, float]]:
    query = urllib.parse.urlencode({"id": series_id})
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"
    with urllib.request.urlopen(url, timeout=30) as response:
        text = response.read().decode("utf-8")
    rows = csv.DictReader(text.splitlines())
    values: list[tuple[str, float]] = []
    for row in rows:
        raw_value = row.get(series_id, "")
        timestamp = row.get("observation_date", "")
        if raw_value in {"", "."}:
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        if math.isfinite(value):
            values.append((timestamp, value))
    return values


def transform_series(series_id: str, values: list[tuple[str, float]], start: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    filtered = [(timestamp, value) for timestamp, value in values if timestamp >= start]
    previous_value: float | None = None
    log_changes: list[float | None] = []

    for timestamp, value in filtered:
        rows.append(
            {
                "series_id": f"{series_id}:level",
                "timestamp": timestamp,
                "field": "level",
                "value": f"{value:.10f}",
                "source_symbol": series_id,
                "source": "fred",
            }
        )
        if previous_value is not None and previous_value > 0 and value > 0:
            log_change = math.log(value / previous_value)
            log_changes.append(log_change)
            rows.append(
                {
                    "series_id": f"{series_id}:log_change",
                    "timestamp": timestamp,
                    "field": "log_change",
                    "value": f"{log_change:.10f}",
                    "source_symbol": series_id,
                    "source": "fred",
                }
            )
        else:
            log_changes.append(None)
        previous_value = value

    for idx, (timestamp, _) in enumerate(filtered):
        if idx < 20:
            continue
        trailing = [value for value in log_changes[idx - 19 : idx + 1] if value is not None]
        if len(trailing) == 20:
            realized_vol = math.sqrt(sum(value * value for value in trailing) / len(trailing)) * math.sqrt(252)
            rows.append(
                {
                    "series_id": f"{series_id}:realized_vol_20",
                    "timestamp": timestamp,
                    "field": "realized_vol_20",
                    "value": f"{realized_vol:.10f}",
                    "source_symbol": series_id,
                    "source": "fred",
                }
            )
    return rows


def main() -> None:
    args = parse_args()
    series_ids = read_series_ids(Path(args.series_file))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, str]] = []
    for series_id in series_ids:
        values = fetch_series(series_id)
        rows = transform_series(series_id, values, args.start)
        print(f"[fetch] {series_id} source_rows={len(values)} output_rows={len(rows)}")
        all_rows.extend(rows)
        time.sleep(args.sleep_seconds)

    fieldnames = ["series_id", "timestamp", "field", "value", "source_symbol", "source"]
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[done] wrote {len(all_rows)} rows to {output}")


if __name__ == "__main__":
    main()
