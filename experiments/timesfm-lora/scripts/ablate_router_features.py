from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METADATA_KEYS = {"cut", "window_index", "series_id", "start_index"}
FORBIDDEN_RUNTIME_KEYS = {"actual", "mae", "smape", "best_family", "family_errors", "label"}

PRESETS = {
    "baseline": ("context", "prediction_summaries", "prediction_disagreement"),
    "context-regime": (
        "context",
        "context_regime",
        "prediction_summaries",
        "prediction_disagreement",
    ),
    "normalized-disagreement": (
        "context",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_disagreement_normalized",
    ),
    "alignment": (
        "context",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_context_alignment",
    ),
    "regime-alignment": (
        "context",
        "context_regime",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_context_alignment",
    ),
    "alignment-normalized": (
        "context",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_disagreement_normalized",
        "prediction_context_alignment",
    ),
    "regime-no-alignment": (
        "context",
        "context_regime",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_disagreement_normalized",
    ),
    "all": (
        "context",
        "context_regime",
        "prediction_summaries",
        "prediction_disagreement",
        "prediction_disagreement_normalized",
        "prediction_context_alignment",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preset", choices=sorted(PRESETS), required=True)
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return experiment_root() / raw_path


def validate_no_leak(value: Any, *, path: str = "runtime_features") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_RUNTIME_KEYS:
                raise ValueError(f"leaky runtime feature key at {path}.{key}")
            validate_no_leak(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_leak(child, path=f"{path}[{index}]")


def ablated_runtime_features(runtime_features: dict[str, Any], keep_groups: set[str]) -> dict[str, Any]:
    ablated = {
        key: value
        for key, value in runtime_features.items()
        if key in METADATA_KEYS or key in keep_groups
    }
    missing = sorted(group for group in keep_groups if group not in ablated)
    if missing:
        raise ValueError(f"input is missing runtime feature groups: {missing}")
    validate_no_leak(ablated)
    return ablated


def build_report(source: dict[str, Any], *, preset: str) -> dict[str, Any]:
    keep_groups = set(PRESETS[preset])
    rows = []
    for row in source["data"]:
        copied = dict(row)
        copied["runtime_features"] = ablated_runtime_features(
            row["runtime_features"],
            keep_groups=keep_groups,
        )
        rows.append(copied)

    report = dict(source)
    report["feature_set"] = f"{source.get('feature_set', 'unknown')}:ablation:{preset}"
    report["feature_ablation"] = {
        "preset": preset,
        "kept_groups": sorted(keep_groups),
        "guardrail": (
            "Ablation removes only runtime feature groups. Labels, actuals, and "
            "current-window errors remain unavailable to router features."
        ),
    }
    report["data"] = rows
    return report


def main() -> None:
    args = parse_args()
    input_path = experiment_path(args.input)
    output_path = experiment_path(args.output)
    source = json.loads(input_path.read_text())
    report = build_report(source, preset=args.preset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "preset": args.preset,
                "rows": report["rows"],
                "kept_groups": report["feature_ablation"]["kept_groups"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
