from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any

from diagnose_router_override_failures import (
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import family_error, learned_candidate_configs, load_router_rows, rows_by_cut
from evaluate_router_fallback_veto import base_selection_by_cut, compact_policy_summary, experiment_path
from validate_multifold_expected_regret_veto import (
    apply_expected_regret_veto,
    config_from_summary,
    train_expected_regret_models,
)
from validate_multifold_feature_veto import default_validation_cuts, subset_by_predicate
from validate_multifold_supervised_veto import supervised_examples


MetricName = str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        default=(
            "reports/router-expected-regret-veto-utility-strict-gate-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "reports/router-expected-regret-fold-regression-attribution-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument("--top-n", type=int, default=8)
    return parser.parse_args()


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def metric_delta_for_row(row: dict[str, Any], original_family: str, veto_family: str, metric: MetricName) -> float:
    return family_error(row, original_family, metric) - family_error(row, veto_family, metric)


def selected_config_from_report(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("selected_utility_config"):
        return dict(report["selected_utility_config"])
    selected_utility = report.get("selected_utility_validation")
    if selected_utility and selected_utility.get("config"):
        return dict(selected_utility["config"])
    summaries = report.get("validation_utility_score_summaries") or report.get("validation_score_summaries")
    if summaries:
        return dict(summaries[0]["config"])
    raise ValueError("report has no expected-regret config to diagnose")


def flatten_numeric_features(value: Any, *, prefix: str = "") -> dict[str, float]:
    if isinstance(value, bool):
        return {prefix: float(value)} if prefix else {}
    if isinstance(value, (int, float)):
        return {prefix: float(value)} if prefix else {}
    if isinstance(value, dict):
        flattened: dict[str, float] = {}
        for key in sorted(value):
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_numeric_features(value[key], prefix=child_prefix))
        return flattened
    return {}


def runtime_feature_values(row: dict[str, Any]) -> dict[str, float]:
    return flatten_numeric_features(row["runtime_features"])


def grouped_delta(rows: list[dict[str, Any]], deltas: list[float], keys: list[str], *, top_n: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row, delta in zip(rows, deltas):
        grouped[tuple(str(row[key]) for key in keys)].append(delta)
    records = [
        {
            "key": dict(zip(keys, key)),
            "windows": len(values),
            "sum_delta": sum(values),
            "mean_delta": mean(values),
            "harm_windows": sum(value < 0.0 for value in values),
            "help_windows": sum(value > 0.0 for value in values),
        }
        for key, values in grouped.items()
    ]
    return sorted(records, key=lambda record: (float(record["sum_delta"]), -int(record["windows"])))[:top_n]


def grouped_family_delta(
    rows: list[dict[str, Any]],
    original_families: list[str],
    deltas: list[float],
    *,
    top_n: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for family, delta in zip(original_families, deltas):
        grouped[family].append(delta)
    records = [
        {
            "family": family,
            "windows": len(values),
            "sum_delta": sum(values),
            "mean_delta": mean(values),
            "harm_windows": sum(value < 0.0 for value in values),
            "help_windows": sum(value > 0.0 for value in values),
        }
        for family, values in grouped.items()
    ]
    return sorted(records, key=lambda record: (float(record["sum_delta"]), -int(record["windows"])))[:top_n]


def feature_contrasts(
    rows: list[dict[str, Any]],
    deltas: list[float],
    *,
    top_n: int,
) -> list[dict[str, Any]]:
    harmed = [row for row, delta in zip(rows, deltas) if delta < 0.0]
    helped = [row for row, delta in zip(rows, deltas) if delta > 0.0]
    if not harmed or not helped:
        return []

    harmed_features = [runtime_feature_values(row) for row in harmed]
    helped_features = [runtime_feature_values(row) for row in helped]
    names = sorted(set().union(*(features.keys() for features in harmed_features + helped_features)))
    records: list[dict[str, Any]] = []
    for name in names:
        harmed_values = [features[name] for features in harmed_features if name in features]
        helped_values = [features[name] for features in helped_features if name in features]
        if not harmed_values or not helped_values:
            continue
        harmed_mean = mean(harmed_values)
        helped_mean = mean(helped_values)
        if harmed_mean is None or helped_mean is None:
            continue
        records.append(
            {
                "feature": name,
                "harmed_mean": harmed_mean,
                "helped_mean": helped_mean,
                "harm_minus_help": harmed_mean - helped_mean,
                "abs_harm_minus_help": abs(harmed_mean - helped_mean),
                "harmed_count": len(harmed_values),
                "helped_count": len(helped_values),
            }
        )
    return sorted(records, key=lambda record: float(record["abs_harm_minus_help"]), reverse=True)[:top_n]


def split_rows(
    rows: list[dict[str, Any]],
    selected_families: list[str],
    predicate: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    placeholder_matrix = [[] for _row in rows]
    split, selected, _matrix = subset_by_predicate(rows, selected_families, placeholder_matrix, predicate)
    return split, selected


def fold_attribution(
    *,
    cut: int,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    training_examples: list[Any],
    config_payload: dict[str, Any],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    include_series: bool,
    feature_surface: str,
    consensus_mode: str,
    top_n: int,
) -> dict[str, Any]:
    config = config_from_summary(config_payload)
    models = train_expected_regret_models(
        examples=training_examples,
        families=families,
        include_series=include_series,
        feature_surface=feature_surface,
        fallback_family=fallback_family,
        config=config,
        consensus_mode=consensus_mode,
    )
    veto_selected, veto_stats = apply_expected_regret_veto(
        rows=rows,
        selected_families=selected_families,
        models=models,
        families=families,
        fallback_family=fallback_family,
        include_series=include_series,
        feature_surface=feature_surface,
        consensus_mode=consensus_mode,
    )
    changed_rows: list[dict[str, Any]] = []
    changed_original_families: list[str] = []
    changed_deltas: list[float] = []
    changed_metric_contributions: list[float] = []
    for row, original_family, veto_family in zip(rows, selected_families, veto_selected):
        if original_family == veto_family:
            continue
        delta = metric_delta_for_row(row, original_family, veto_family, metric)
        changed_rows.append(row)
        changed_original_families.append(original_family)
        changed_deltas.append(delta)
        changed_metric_contributions.append(delta / len(rows))

    metric_delta = sum(changed_metric_contributions)
    helped_deltas = [delta for delta in changed_deltas if delta > 0.0]
    harmed_deltas = [delta for delta in changed_deltas if delta < 0.0]
    return {
        "cut": cut,
        "windows": len(rows),
        "changed_windows": len(changed_rows),
        "metric_delta": metric_delta,
        "verdict": "fold_improves" if metric_delta > 0.0 else "fold_regresses" if metric_delta < 0.0 else "fold_flat",
        "help_windows": len(helped_deltas),
        "harm_windows": len(harmed_deltas),
        "sum_help_delta": sum(helped_deltas),
        "sum_harm_delta": sum(harmed_deltas),
        "mean_help_delta": mean(helped_deltas),
        "mean_harm_delta": mean(harmed_deltas),
        "veto": veto_stats,
        "feature_surface": feature_surface,
        "worst_series": grouped_delta(changed_rows, changed_deltas, ["series_id"], top_n=top_n),
        "worst_original_families": grouped_family_delta(
            changed_rows,
            changed_original_families,
            changed_deltas,
            top_n=top_n,
        ),
        "feature_contrasts": feature_contrasts(changed_rows, changed_deltas, top_n=top_n),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_report_path = experiment_path(args.report)
    source_report = json.loads(source_report_path.read_text())
    router_rows = load_router_rows(experiment_path(source_report["input"]))
    router_report = json.loads(experiment_path(source_report["router_report"]).read_text())
    policy = selected_policy(router_report, source_report.get("policy_summary", "best_veto_by_delta"))
    rows = list(router_rows["data"])
    cuts = [int(cut) for cut in router_rows["cuts"]]
    families = list(router_rows["families"])
    cut_rows = rows_by_cut(rows)
    validation_cuts = [int(cut) for cut in source_report.get("validation_cuts") or default_validation_cuts(argparse.Namespace(validation_cut=None))]
    metric = str(source_report.get("metric", "mae"))
    fallback_family = str(source_report.get("fallback_family", "recent2000"))
    include_series = bool(source_report.get("include_series", False))
    feature_surface = str(source_report.get("feature_surface", "base"))
    consensus_mode = str(source_report.get("consensus_mode") or "single")
    config_payload = selected_config_from_report(source_report)

    base_selections = base_selection_by_cut(
        cuts=cuts,
        cut_rows=cut_rows,
        families=families,
        learned_configs=learned_candidate_configs(source_report.get("candidate_set", "knn-regret")),
        metric=metric,
        cold_start_family=str(source_report.get("cold_start_family", "recent2000")),
        fallback_family=fallback_family,
        min_validation_lift=float(source_report.get("min_validation_lift", 0.005)),
        softmax_steps=int(source_report.get("softmax_steps", 2000)),
    )
    per_cut = reconstruct_policy_reports(
        cuts=cuts,
        cut_rows=cut_rows,
        base_selections=base_selections,
        families=families,
        policy=policy,
        metric=metric,
        fallback_family=fallback_family,
    )
    routed_rows, routed_selected = routed_rows_and_selection(per_cut)
    initial_discovery_max_cut = int(source_report.get("initial_discovery_max_cut", 3500))
    discovery_rows, discovery_selected = split_rows(
        routed_rows,
        routed_selected,
        lambda row: int(row["cut"]) <= initial_discovery_max_cut,
    )
    discovery_examples = supervised_examples(
        rows=discovery_rows,
        selected_families=discovery_selected,
        fallback_family=fallback_family,
        metric=metric,
    )
    fold_reports = []
    for cut in validation_cuts:
        fold_rows, fold_selected = split_rows(
            routed_rows,
            routed_selected,
            lambda row, cut=cut: int(row["cut"]) == cut,
        )
        fold_reports.append(
            fold_attribution(
                cut=cut,
                rows=fold_rows,
                selected_families=fold_selected,
                training_examples=discovery_examples,
                config_payload=config_payload,
                families=families,
                fallback_family=fallback_family,
                metric=metric,
                include_series=include_series,
                feature_surface=feature_surface,
                consensus_mode=consensus_mode,
                top_n=args.top_n,
            )
        )

    regression_folds = [fold for fold in fold_reports if float(fold["metric_delta"]) <= 0.0]
    return {
        "method": "expected_regret_fold_regression_attribution",
        "source_report": args.report,
        "source_report_path": str(source_report_path),
        "input": source_report["input"],
        "router_report": source_report["router_report"],
        "policy_summary": source_report.get("policy_summary", "best_veto_by_delta"),
        "policy": compact_policy_summary(policy),
        "metric": metric,
        "fallback_family": fallback_family,
        "include_series": include_series,
        "feature_surface": feature_surface,
        "consensus_mode": consensus_mode,
        "selected_config": config_payload,
        "initial_discovery_max_cut": initial_discovery_max_cut,
        "validation_cuts": validation_cuts,
        "discovery_examples": len(discovery_examples),
        "folds": fold_reports,
        "regression_folds": regression_folds,
        "regression_fold_count": len(regression_folds),
        "worst_fold": min(fold_reports, key=lambda fold: float(fold["metric_delta"])) if fold_reports else None,
        "guardrail": (
            "This diagnostic uses the already selected expected-regret validation config and only explains "
            "validation fold regressions; it does not select or evaluate final holdout candidates."
        ),
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "source_report": report["source_report"],
                "selected_config": report["selected_config"],
                "feature_surface": report["feature_surface"],
                "validation_cuts": report["validation_cuts"],
                "regression_fold_count": report["regression_fold_count"],
                "worst_fold": {
                    "cut": report["worst_fold"]["cut"] if report["worst_fold"] else None,
                    "metric_delta": report["worst_fold"]["metric_delta"] if report["worst_fold"] else None,
                    "changed_windows": report["worst_fold"]["changed_windows"] if report["worst_fold"] else None,
                    "harm_windows": report["worst_fold"]["harm_windows"] if report["worst_fold"] else None,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
