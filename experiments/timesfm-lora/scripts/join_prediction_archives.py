from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from export_prediction_archives import ADAPTERS, CUTS, FAMILIES, ArchiveJob, predictions_path


FORBIDDEN_RUNTIME_KEYS = {"actual", "mae", "smape", "best_family", "family_errors", "label"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="reports/router-rows-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument("--cut", action="append", type=int, choices=CUTS)
    parser.add_argument("--family", action="append", choices=FAMILIES)
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return experiment_root() / raw_path


def selected_values(values: tuple[int, ...] | tuple[str, ...], selected: list[int] | list[str] | None) -> list:
    if not selected:
        return list(values)
    return [value for value in values if value in selected]


def archive_path(family: str, cut: int) -> Path:
    return experiment_root() / predictions_path(ArchiveJob(family=family, cut=cut, adapter_dir=ADAPTERS[family][cut]))


def load_archive(*, family: str, cut: int) -> dict[str, Any]:
    path = archive_path(family, cut)
    if not path.exists():
        raise FileNotFoundError(f"missing prediction archive: {path}")

    archive = json.loads(path.read_text())
    if int(archive["skip_windows"]) != cut:
        raise ValueError(f"{path} has skip_windows={archive['skip_windows']}, expected {cut}")
    if int(archive["windows"]) != len(archive["records"]):
        raise ValueError(f"{path} windows={archive['windows']} but records={len(archive['records'])}")
    return archive


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)


def population_std(values: list[float]) -> float:
    center = mean(values)
    return (sum((value - center) ** 2 for value in values) / len(values)) ** 0.5


def summarize_prediction(values: list[float]) -> dict[str, float]:
    return {
        "predicted_first": values[0],
        "predicted_last": values[-1],
        "predicted_mean": mean(values),
        "predicted_std": population_std(values),
        "predicted_min": min(values),
        "predicted_max": max(values),
        "predicted_trend": values[-1] - values[0],
    }


def prediction_disagreement(predictions_by_family: dict[str, list[float]]) -> dict[str, float]:
    family_summaries = {
        family: summarize_prediction(prediction) for family, prediction in predictions_by_family.items()
    }
    predicted_means = [summary["predicted_mean"] for summary in family_summaries.values()]
    predicted_lasts = [summary["predicted_last"] for summary in family_summaries.values()]
    predicted_trends = [summary["predicted_trend"] for summary in family_summaries.values()]
    per_step_spreads = [
        max(step_values) - min(step_values) for step_values in zip(*predictions_by_family.values(), strict=True)
    ]

    return {
        "family_predicted_mean_range": max(predicted_means) - min(predicted_means),
        "family_predicted_mean_std": population_std(predicted_means),
        "family_predicted_last_range": max(predicted_lasts) - min(predicted_lasts),
        "family_predicted_last_std": population_std(predicted_lasts),
        "family_predicted_trend_range": max(predicted_trends) - min(predicted_trends),
        "horizon_prediction_spread_mean": mean(per_step_spreads),
        "horizon_prediction_spread_max": max(per_step_spreads),
    }


def validate_no_leak(value: Any, *, path: str = "runtime_features") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_RUNTIME_KEYS:
                raise ValueError(f"leaky runtime feature key at {path}.{key}")
            validate_no_leak(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_leak(child, path=f"{path}[{index}]")


def validate_record_alignment(*, cut: int, family: str, base: dict[str, Any], candidate: dict[str, Any]) -> None:
    comparable_keys = ("window_id", "series_id", "start_index", "field", "context_len", "horizon_len", "skip_windows")
    for key in comparable_keys:
        if base[key] != candidate[key]:
            raise ValueError(f"cut={cut} family={family} key={key} mismatch: {base[key]} != {candidate[key]}")
    if base["actual"] != candidate["actual"]:
        raise ValueError(f"cut={cut} family={family} window_id={base['window_id']} actual mismatch")


def best_family_by_mae(families: list[str], family_errors: dict[str, dict[str, float]]) -> str:
    return min(families, key=lambda family: family_errors[family]["mae"])


def build_row(*, cut: int, families: list[str], records_by_family: dict[str, dict[str, Any]]) -> dict[str, Any]:
    base_family = families[0]
    base_record = records_by_family[base_family]
    for family in families[1:]:
        validate_record_alignment(cut=cut, family=family, base=base_record, candidate=records_by_family[family])

    predictions_by_family = {family: records_by_family[family]["predicted"] for family in families}
    prediction_summaries = {
        family: summarize_prediction(predictions_by_family[family]) for family in families
    }
    family_errors = {
        family: {
            "mae": float(records_by_family[family]["mae"]),
            "smape": float(records_by_family[family]["smape"]),
        }
        for family in families
    }
    ranked = sorted((values["mae"], family) for family, values in family_errors.items())
    best_family = best_family_by_mae(families, family_errors)

    runtime_features = {
        "cut": cut,
        "window_index": int(base_record["window_index"]),
        "series_id": base_record["series_id"],
        "start_index": int(base_record["start_index"]),
        "context": base_record["features"],
        "prediction_summaries": prediction_summaries,
        "prediction_disagreement": prediction_disagreement(predictions_by_family),
    }
    validate_no_leak(runtime_features)

    return {
        "row_id": f"cut{cut}:{base_record['window_id']}",
        "cut": cut,
        "window_id": base_record["window_id"],
        "series_id": base_record["series_id"],
        "start_index": int(base_record["start_index"]),
        "runtime_features": runtime_features,
        "label": {
            "best_family_by_mae": best_family,
            "best_mae": family_errors[best_family]["mae"],
            "second_best_mae": ranked[1][0] if len(ranked) > 1 else ranked[0][0],
            "best_margin_mae": (ranked[1][0] - ranked[0][0]) if len(ranked) > 1 else 0.0,
            "family_errors": family_errors,
            "actual": base_record["actual"],
        },
    }


def summarize_rows(rows: list[dict[str, Any]], families: list[str]) -> dict[str, Any]:
    label_counts = Counter(row["label"]["best_family_by_mae"] for row in rows)
    label_counts_by_cut: dict[str, Counter[str]] = defaultdict(Counter)
    family_mae: dict[str, list[float]] = defaultdict(list)
    family_smape: dict[str, list[float]] = defaultdict(list)
    oracle_mae: list[float] = []
    oracle_smape: list[float] = []
    margins: list[float] = []

    for row in rows:
        cut_key = str(row["cut"])
        best = row["label"]["best_family_by_mae"]
        label_counts_by_cut[cut_key][best] += 1
        oracle_mae.append(float(row["label"]["best_mae"]))
        oracle_smape.append(float(row["label"]["family_errors"][best]["smape"]))
        margins.append(float(row["label"]["best_margin_mae"]))
        for family in families:
            family_mae[family].append(float(row["label"]["family_errors"][family]["mae"]))
            family_smape[family].append(float(row["label"]["family_errors"][family]["smape"]))

    fixed_family_mean_mae = {family: mean(family_mae[family]) for family in families}
    fixed_family_mean_smape = {family: mean(family_smape[family]) for family in families}
    zero_mae = fixed_family_mean_mae["zero-shot"]
    zero_smape = fixed_family_mean_smape["zero-shot"]
    oracle_mean_mae = mean(oracle_mae)
    oracle_mean_smape = mean(oracle_smape)

    return {
        "label_counts": dict(sorted(label_counts.items())),
        "label_counts_by_cut": {
            cut: dict(sorted(counts.items())) for cut, counts in sorted(label_counts_by_cut.items())
        },
        "fixed_family_mean_mae": fixed_family_mean_mae,
        "fixed_family_mean_smape": fixed_family_mean_smape,
        "best_fixed_family_by_mae": min(families, key=lambda family: fixed_family_mean_mae[family]),
        "leaky_oracle_per_window": {
            "mae": oracle_mean_mae,
            "mae_improvement_vs_zero_shot": (zero_mae - oracle_mean_mae) / zero_mae,
            "smape": oracle_mean_smape,
            "smape_improvement_vs_zero_shot": (zero_smape - oracle_mean_smape) / zero_smape,
            "warning": "Upper bound only. It uses future errors to choose the best family per row.",
        },
        "label_margin_mae": {
            "mean": mean(margins),
            "min": min(margins),
            "max": max(margins),
        },
    }


def build_router_rows(*, cuts: list[int], families: list[str]) -> dict[str, Any]:
    if "zero-shot" not in families:
        raise ValueError("zero-shot must be included so router rows have a fixed baseline")
    if len(families) < 2:
        raise ValueError("at least two families are required")

    rows: list[dict[str, Any]] = []
    archive_paths: dict[str, dict[str, str]] = {}
    expected_horizon: int | None = None
    expected_field: str | None = None

    for cut in cuts:
        archives = {family: load_archive(family=family, cut=cut) for family in families}
        archive_paths[str(cut)] = {family: str(archive_path(family, cut)) for family in families}
        record_ids = {
            family: [record["window_id"] for record in archive["records"]] for family, archive in archives.items()
        }
        base_ids = record_ids[families[0]]
        for family in families[1:]:
            if record_ids[family] != base_ids:
                raise ValueError(f"cut={cut} family={family} window_id order does not match {families[0]}")

        for archive in archives.values():
            horizon = int(archive["horizon_len"])
            field = str(archive["field"])
            if expected_horizon is None:
                expected_horizon = horizon
            if expected_field is None:
                expected_field = field
            if horizon != expected_horizon:
                raise ValueError(f"cut={cut} horizon_len={horizon}, expected {expected_horizon}")
            if field != expected_field:
                raise ValueError(f"cut={cut} field={field}, expected {expected_field}")

        for index, _window_id in enumerate(base_ids):
            records_by_family = {family: archives[family]["records"][index] for family in families}
            rows.append(build_row(cut=cut, families=families, records_by_family=records_by_family))

    return {
        "method": "prediction_archive_router_rows",
        "field": expected_field,
        "horizon_len": expected_horizon,
        "cuts": cuts,
        "families": families,
        "rows": len(rows),
        "guardrail": (
            "runtime_features contain only context features and prediction-derived summaries. "
            "actuals, errors, and best-family labels are stored under label only."
        ),
        "summary": summarize_rows(rows, families),
        "archive_paths": archive_paths,
        "data": rows,
    }


def main() -> None:
    args = parse_args()
    cuts = selected_values(CUTS, args.cut)
    families = selected_values(FAMILIES, args.family)
    report = build_router_rows(cuts=cuts, families=families)

    output = experiment_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "rows": report["rows"],
                "cuts": report["cuts"],
                "families": report["families"],
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
