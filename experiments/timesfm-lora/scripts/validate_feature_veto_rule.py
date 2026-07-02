from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Any

from diagnose_router_override_failures import (
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import (
    family_error,
    fixed_selection,
    flatten_runtime_features,
    learned_candidate_configs,
    load_router_rows,
    rows_by_cut,
    selection_metrics,
)
from evaluate_router_fallback_veto import (
    base_selection_by_cut,
    compact_policy_summary,
    experiment_path,
    series_delta_summary,
)


MetricName = str


@dataclass(frozen=True)
class FeatureRule:
    feature_name: str
    feature_index: int
    direction: str
    threshold: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument(
        "--router-report",
        default=(
            "reports/router-fallback-veto-series-risk-objective-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "reports/router-feature-veto-frozen-validation-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--candidate-set", choices=["baseline", "loss-aware", "knn-regret"], default="knn-regret")
    parser.add_argument("--cold-start-family", default="recent2000")
    parser.add_argument("--fallback-family", default="recent2000")
    parser.add_argument("--min-validation-lift", type=float, default=0.005)
    parser.add_argument("--softmax-steps", type=int, default=2000)
    parser.add_argument("--policy-summary", default="best_veto_by_delta")
    parser.add_argument("--discovery-max-cut", type=int, default=3500)
    parser.add_argument("--min-discovery-vetoed", type=int, default=8)
    parser.add_argument("--max-thresholds-per-feature", type=int, default=96)
    parser.add_argument("--top-rules", type=int, default=20)
    parser.add_argument("--include-series", action="store_true")
    return parser.parse_args()


def relative_lift(reference: float, candidate: float) -> float:
    return (reference - candidate) / reference


def subset_by_cut(
    rows: list[dict[str, Any]],
    selected_families: list[str],
    *,
    max_cut_inclusive: int | None = None,
    min_cut_exclusive: int | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    filtered_rows: list[dict[str, Any]] = []
    filtered_selected: list[str] = []
    for row, selected_family in zip(rows, selected_families):
        cut = int(row["cut"])
        if max_cut_inclusive is not None and cut > max_cut_inclusive:
            continue
        if min_cut_exclusive is not None and cut <= min_cut_exclusive:
            continue
        filtered_rows.append(row)
        filtered_selected.append(selected_family)
    return filtered_rows, filtered_selected


def finite(value: float) -> bool:
    return math.isfinite(value)


def threshold_candidates(values: list[float], limit: int) -> list[float]:
    unique_values = sorted({value for value in values if finite(value)})
    if not unique_values:
        return []
    if len(unique_values) <= limit:
        return unique_values
    step = (len(unique_values) - 1) / (limit - 1)
    return [unique_values[round(index * step)] for index in range(limit)]


def feature_matrix(
    rows: list[dict[str, Any]],
    *,
    families: list[str],
    include_series: bool,
) -> tuple[list[list[float]], list[str]]:
    series_ids = sorted({str(row["series_id"]) for row in rows})
    matrix: list[list[float]] = []
    feature_names: list[str] | None = None
    for row in rows:
        values, names = flatten_runtime_features(
            row,
            families=families,
            series_ids=series_ids,
            include_series=include_series,
        )
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise ValueError("runtime feature names changed between rows")
        matrix.append(values)
    return matrix, feature_names or []


def rule_matches(rule: FeatureRule, feature_values: list[float]) -> bool:
    value = feature_values[rule.feature_index]
    if not finite(value):
        return False
    if rule.direction == "<=":
        return value <= rule.threshold
    if rule.direction == ">=":
        return value >= rule.threshold
    raise ValueError(f"unknown rule direction: {rule.direction}")


def apply_rule(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    rule: FeatureRule,
    fallback_family: str,
    metric: MetricName,
) -> tuple[list[str], dict[str, Any]]:
    next_selected: list[str] = []
    changed_windows = 0
    harmful_vetoed = 0
    beneficial_blocked = 0
    neutral_vetoed = 0
    selected_family_counts: dict[str, int] = {}
    delta_sum = 0.0

    for row, selected_family, feature_values in zip(rows, selected_families, matrix):
        should_veto = selected_family != fallback_family and rule_matches(rule, feature_values)
        if not should_veto:
            next_selected.append(selected_family)
            continue

        delta = family_error(row, fallback_family, metric) - family_error(row, selected_family, metric)
        changed_windows += 1
        delta_sum += delta
        selected_family_counts[selected_family] = selected_family_counts.get(selected_family, 0) + 1
        if delta < 0.0:
            harmful_vetoed += 1
        elif delta > 0.0:
            beneficial_blocked += 1
        else:
            neutral_vetoed += 1
        next_selected.append(fallback_family)

    return next_selected, {
        "changed_windows": changed_windows,
        "harmful_vetoed": harmful_vetoed,
        "beneficial_blocked": beneficial_blocked,
        "neutral_vetoed": neutral_vetoed,
        "veto_delta_sum": delta_sum,
        "veto_delta_mean": delta_sum / changed_windows if changed_windows else 0.0,
        "vetoed_selected_family_counts": dict(sorted(selected_family_counts.items())),
    }


def fixed_fallback_metric(
    *,
    rows: list[dict[str, Any]],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> float:
    return float(
        selection_metrics(
            rows=rows,
            selected_families=fixed_selection(rows, fallback_family),
            families=families,
            metric=metric,
        )["selected_metric"]
    )


def split_report(
    *,
    name: str,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    rule: FeatureRule,
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    if not rows:
        return {
            "name": name,
            "windows": 0,
            "rule": rule_summary(rule),
            "original": None,
            "feature_veto": None,
            "veto": {"changed_windows": 0},
            "metric_delta": 0.0,
            "verdict": "no_windows",
        }

    fallback_metric = fixed_fallback_metric(
        rows=rows,
        families=families,
        fallback_family=fallback_family,
        metric=metric,
    )
    original_metrics = selection_metrics(
        rows=rows,
        selected_families=selected_families,
        families=families,
        metric=metric,
    )
    veto_selected, veto_stats = apply_rule(
        rows=rows,
        selected_families=selected_families,
        matrix=matrix,
        rule=rule,
        fallback_family=fallback_family,
        metric=metric,
    )
    veto_metrics = selection_metrics(
        rows=rows,
        selected_families=veto_selected,
        families=families,
        metric=metric,
    )
    original_metric = float(original_metrics["selected_metric"])
    veto_metric = float(veto_metrics["selected_metric"])
    metric_delta = original_metric - veto_metric
    if veto_stats["changed_windows"] == 0:
        verdict = "no_rule_exposure"
    elif metric_delta > 0.0:
        verdict = "rule_improves_split"
    elif metric_delta == 0.0:
        verdict = "rule_no_metric_change"
    else:
        verdict = "rule_hurts_split"

    return {
        "name": name,
        "windows": len(rows),
        "rule": rule_summary(rule),
        "original": {
            "metrics": original_metrics,
            "relative_lift_vs_fallback": relative_lift(fallback_metric, original_metric),
            "series_summary": series_delta_summary(
                rows=rows,
                selected_families=selected_families,
                fallback_family=fallback_family,
                metric=metric,
            ),
        },
        "feature_veto": {
            "metrics": veto_metrics,
            "relative_lift_vs_fallback": relative_lift(fallback_metric, veto_metric),
            "series_summary": series_delta_summary(
                rows=rows,
                selected_families=veto_selected,
                fallback_family=fallback_family,
                metric=metric,
            ),
        },
        "veto": veto_stats,
        "metric_delta": metric_delta,
        "relative_metric_delta_vs_original": metric_delta / original_metric,
        "verdict": verdict,
    }


def rule_summary(rule: FeatureRule) -> dict[str, Any]:
    return {
        "feature_name": rule.feature_name,
        "feature_index": rule.feature_index,
        "direction": rule.direction,
        "threshold": rule.threshold,
    }


def negative_series_count(split: dict[str, Any], section: str) -> int:
    payload = split[section]
    if payload is None:
        return 0
    return int(payload["series_summary"]["negative_routed_series_count"])


def candidate_score(
    *,
    selected_families: list[str],
    matrix: list[list[float]],
    selected_to_fallback_deltas: list[float],
    rule: FeatureRule,
    fallback_family: str,
    original_metric: float,
) -> dict[str, Any]:
    changed_windows = 0
    harmful_vetoed = 0
    beneficial_blocked = 0
    neutral_vetoed = 0
    selected_family_counts: dict[str, int] = {}
    delta_sum = 0.0

    for selected_family, feature_values, delta in zip(selected_families, matrix, selected_to_fallback_deltas):
        if selected_family == fallback_family or not rule_matches(rule, feature_values):
            continue
        changed_windows += 1
        delta_sum += delta
        selected_family_counts[selected_family] = selected_family_counts.get(selected_family, 0) + 1
        if delta < 0.0:
            harmful_vetoed += 1
        elif delta > 0.0:
            beneficial_blocked += 1
        else:
            neutral_vetoed += 1

    veto_metric = original_metric + (delta_sum / len(selected_families))
    metric_delta = original_metric - veto_metric
    return {
        "rule": rule_summary(rule),
        "selected_metric": veto_metric,
        "metric_delta": metric_delta,
        "relative_metric_delta_vs_original": metric_delta / original_metric,
        "veto": {
            "changed_windows": changed_windows,
            "harmful_vetoed": harmful_vetoed,
            "beneficial_blocked": beneficial_blocked,
            "neutral_vetoed": neutral_vetoed,
            "veto_delta_sum": delta_sum,
            "veto_delta_mean": delta_sum / changed_windows if changed_windows else 0.0,
            "vetoed_selected_family_counts": dict(sorted(selected_family_counts.items())),
        },
    }


def discover_best_rule(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    feature_names: list[str],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    min_vetoed: int,
    max_thresholds_per_feature: int,
    top_rules: int,
) -> tuple[FeatureRule, list[dict[str, Any]]]:
    override_indices = [
        index for index, selected_family in enumerate(selected_families) if selected_family != fallback_family
    ]
    if not override_indices:
        raise ValueError("discovery split has no override windows")
    original_metric = float(
        selection_metrics(
            rows=rows,
            selected_families=selected_families,
            families=families,
            metric=metric,
        )["selected_metric"]
    )
    selected_to_fallback_deltas = [
        family_error(row, fallback_family, metric) - family_error(row, selected_family, metric)
        if selected_family != fallback_family
        else 0.0
        for row, selected_family in zip(rows, selected_families)
    ]

    scored: list[dict[str, Any]] = []
    for feature_index, feature_name in enumerate(feature_names):
        values = [matrix[index][feature_index] for index in override_indices]
        for threshold in threshold_candidates(values, max_thresholds_per_feature):
            for direction in ("<=", ">="):
                rule = FeatureRule(
                    feature_name=feature_name,
                    feature_index=feature_index,
                    direction=direction,
                    threshold=threshold,
                )
                score = candidate_score(
                    selected_families=selected_families,
                    matrix=matrix,
                    selected_to_fallback_deltas=selected_to_fallback_deltas,
                    rule=rule,
                    fallback_family=fallback_family,
                    original_metric=original_metric,
                )
                if score["veto"]["changed_windows"] < min_vetoed:
                    continue
                if score["metric_delta"] <= 0.0:
                    continue
                scored.append(score)

    if not scored:
        raise ValueError("no positive discovery feature-veto rule found")

    scored.sort(
        key=lambda item: (
            float(item["metric_delta"]),
            int(item["veto"]["harmful_vetoed"]) - int(item["veto"]["beneficial_blocked"]),
            -int(item["veto"]["changed_windows"]),
        ),
        reverse=True,
    )
    best_rule_payload = scored[0]["rule"]
    best_rule = FeatureRule(
        feature_name=str(best_rule_payload["feature_name"]),
        feature_index=int(best_rule_payload["feature_index"]),
        direction=str(best_rule_payload["direction"]),
        threshold=float(best_rule_payload["threshold"]),
    )
    return best_rule, scored[:top_rules]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    router_rows = load_router_rows(experiment_path(args.input))
    router_report = json.loads(experiment_path(args.router_report).read_text())
    policy = selected_policy(router_report, args.policy_summary)
    rows = list(router_rows["data"])
    cuts = [int(cut) for cut in router_rows["cuts"]]
    families = list(router_rows["families"])
    cut_rows = rows_by_cut(rows)
    base_selections = base_selection_by_cut(
        cuts=cuts,
        cut_rows=cut_rows,
        families=families,
        learned_configs=learned_candidate_configs(args.candidate_set),
        metric=args.metric,
        cold_start_family=args.cold_start_family,
        fallback_family=args.fallback_family,
        min_validation_lift=args.min_validation_lift,
        softmax_steps=args.softmax_steps,
    )
    per_cut = reconstruct_policy_reports(
        cuts=cuts,
        cut_rows=cut_rows,
        base_selections=base_selections,
        families=families,
        policy=policy,
        metric=args.metric,
        fallback_family=args.fallback_family,
    )
    routed_rows, routed_selected = routed_rows_and_selection(per_cut)
    matrix, feature_names = feature_matrix(
        routed_rows,
        families=families,
        include_series=args.include_series,
    )

    discovery_rows, discovery_selected = subset_by_cut(
        routed_rows,
        routed_selected,
        max_cut_inclusive=args.discovery_max_cut,
    )
    future_rows, future_selected = subset_by_cut(
        routed_rows,
        routed_selected,
        min_cut_exclusive=args.discovery_max_cut,
    )
    discovery_indices = [index for index, row in enumerate(routed_rows) if int(row["cut"]) <= args.discovery_max_cut]
    future_indices = [index for index, row in enumerate(routed_rows) if int(row["cut"]) > args.discovery_max_cut]
    discovery_matrix = [matrix[index] for index in discovery_indices]
    future_matrix = [matrix[index] for index in future_indices]

    best_rule, top_discovery_rules = discover_best_rule(
        rows=discovery_rows,
        selected_families=discovery_selected,
        matrix=discovery_matrix,
        feature_names=feature_names,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
        min_vetoed=args.min_discovery_vetoed,
        max_thresholds_per_feature=args.max_thresholds_per_feature,
        top_rules=args.top_rules,
    )
    discovery_report = split_report(
        name="discovery_through_cut",
        rows=discovery_rows,
        selected_families=discovery_selected,
        matrix=discovery_matrix,
        rule=best_rule,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    future_report = split_report(
        name="future_after_discovery_cut",
        rows=future_rows,
        selected_families=future_selected,
        matrix=future_matrix,
        rule=best_rule,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    future_original_negative = negative_series_count(future_report, "original")
    future_veto_negative = negative_series_count(future_report, "feature_veto")
    if future_report["verdict"] == "rule_improves_split" and future_veto_negative <= future_original_negative:
        verdict = "future_validated_positive"
    elif future_report["verdict"] == "rule_improves_split":
        verdict = "aggregate_positive_downside_regressed"
    elif future_report["verdict"] == "no_rule_exposure":
        verdict = "not_validated_no_future_exposure"
    else:
        verdict = "not_promotable"

    return {
        "method": "single_feature_fallback_veto_frozen_validation",
        "input": args.input,
        "router_report": args.router_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "include_series": args.include_series,
        "discovery_max_cut": args.discovery_max_cut,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "feature_count": len(feature_names),
        "best_rule": rule_summary(best_rule),
        "top_discovery_rules": top_discovery_rules,
        "discovery_split": discovery_report,
        "future_split": future_report,
        "verdict": verdict,
        "guardrail": (
            "The feature threshold is selected only on the discovery split. "
            "Only future_after_discovery_cut can validate whether this no-leak "
            "runtime feature veto generalizes."
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
                "verdict": report["verdict"],
                "include_series": report["include_series"],
                "discovery_max_cut": report["discovery_max_cut"],
                "best_rule": report["best_rule"],
                "discovery_changed_windows": report["discovery_split"]["veto"]["changed_windows"],
                "discovery_metric_delta": report["discovery_split"]["metric_delta"],
                "future_windows": report["future_split"]["windows"],
                "future_changed_windows": report["future_split"]["veto"]["changed_windows"],
                "future_metric_delta": report["future_split"]["metric_delta"],
                "future_verdict": report["future_split"]["verdict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
