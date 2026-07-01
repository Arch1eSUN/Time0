from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from summarize_router_attribution import build_report, experiment_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--write-attribution-dir")
    parser.add_argument("--tolerance", type=float, default=1e-12)
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError(f"unsupported manifest schema_version: {manifest.get('schema_version')}")
    required = {"id", "router", "validation", "feature_surface"}
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"manifest is missing required keys: {missing}")
    return manifest


def report_args(manifest: dict[str, Any], surface: dict[str, Any]) -> SimpleNamespace:
    router = manifest["router"]
    return SimpleNamespace(
        input=surface["input"],
        output="",
        metric=router["selection_metric"],
        policy=router["policy"],
        cold_start_family=router["cold_start_family"],
        fallback_family=router["fallback_family"],
        min_validation_lift=float(router["min_validation_lift"]),
        min_series_validation_lift=float(router["min_series_validation_lift"]),
        series_risk_decay=float(router["series_risk_decay"]),
        veto_k=int(router["veto_k"]),
        veto_regret_threshold=float(router["veto_regret_threshold"]),
        veto_feature_mode=router["veto_feature_mode"],
        softmax_steps=int(router["softmax_steps"]),
        candidate_set=router["candidate_set"],
    )


def assert_surface_metadata(
    *,
    manifest: dict[str, Any],
    surface: dict[str, Any],
    report: dict[str, Any],
) -> None:
    expected_groups = set(manifest["feature_surface"]["required_runtime_feature_groups"])
    if int(report["rows"]) != int(surface["rows"]):
        raise ValueError(f"{surface['name']} rows mismatch: {report['rows']} != {surface['rows']}")
    if [int(cut) for cut in report["cuts"]] != [int(cut) for cut in surface["cuts"]]:
        raise ValueError(f"{surface['name']} cuts mismatch: {report['cuts']} != {surface['cuts']}")
    if list(report["families"]) != list(manifest["candidate_families"]):
        raise ValueError(f"{surface['name']} families mismatch")

    first_runtime_features = report["per_cut"][0]["decision"]
    if "policy" not in first_runtime_features:
        raise ValueError(f"{surface['name']} missing decision policy metadata")

    input_report = json.loads(experiment_path(surface["input"]).read_text())
    first_row_groups = set(input_report["data"][0]["runtime_features"])
    missing_groups = sorted(expected_groups.difference(first_row_groups))
    if missing_groups:
        raise ValueError(f"{surface['name']} missing runtime feature groups: {missing_groups}")


def surface_result(
    *,
    manifest: dict[str, Any],
    surface: dict[str, Any],
    tolerance: float,
    write_attribution_dir: Path | None,
) -> dict[str, Any]:
    args = report_args(manifest, surface)
    report = build_report(args)
    assert_surface_metadata(manifest=manifest, surface=surface, report=report)

    metric = report["selection_metric"]
    routed = report["summary"]["routed_cuts_only"]
    delta = float(routed[f"selected_{metric}_delta_vs_fallback"])
    expected_delta = float(surface["expected_routed_delta_vs_fallback"])
    delta_error = abs(delta - expected_delta)
    min_delta = float(manifest["validation"]["min_routed_delta_vs_fallback"])
    passed = delta >= min_delta and delta_error <= tolerance

    attribution_output = None
    if write_attribution_dir is not None:
        write_attribution_dir.mkdir(parents=True, exist_ok=True)
        attribution_output = write_attribution_dir / f"{manifest['id']}-{surface['name']}-attribution.json"
        attribution_output.write_text(json.dumps(report, indent=2) + "\n")

    return {
        "surface": surface["name"],
        "input": surface["input"],
        "rows": report["rows"],
        "cuts": report["cuts"],
        "selected_metric": routed[f"selected_{metric}"],
        "fallback_metric": routed[f"fallback_{metric}"],
        "delta_vs_fallback": delta,
        "expected_delta_vs_fallback": expected_delta,
        "delta_error": delta_error,
        "positive_routed_series_count": report["summary"]["positive_routed_series_count"],
        "negative_routed_series_count": report["summary"]["negative_routed_series_count"],
        "selected_counts": routed["selected_counts"],
        "passed": passed,
        "attribution_output": str(attribution_output) if attribution_output else None,
    }


def main() -> None:
    args = parse_args()
    manifest_path = experiment_path(args.manifest)
    output_path = experiment_path(args.output)
    write_attribution_dir = (
        experiment_path(args.write_attribution_dir) if args.write_attribution_dir else None
    )
    manifest = load_manifest(manifest_path)
    surfaces = manifest["validation"]["surfaces"]
    results = [
        surface_result(
            manifest=manifest,
            surface=surface,
            tolerance=args.tolerance,
            write_attribution_dir=write_attribution_dir,
        )
        for surface in surfaces
    ]
    required = set(manifest["validation"]["required_surfaces"])
    observed = {result["surface"] for result in results}
    missing_required = sorted(required.difference(observed))
    if missing_required:
        raise ValueError(f"missing required surfaces: {missing_required}")

    passed = all(result["passed"] for result in results)
    report = {
        "method": "router_manifest_evaluation",
        "manifest": str(manifest_path),
        "manifest_id": manifest["id"],
        "status": manifest["status"],
        "router": manifest["router"],
        "feature_surface": manifest["feature_surface"],
        "passed": passed,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
