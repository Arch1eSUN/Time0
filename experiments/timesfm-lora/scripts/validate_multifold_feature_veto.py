from __future__ import annotations

import argparse
import json
from typing import Any, Callable

from diagnose_router_override_failures import (
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import learned_candidate_configs, load_router_rows, rows_by_cut
from evaluate_router_fallback_veto import base_selection_by_cut, compact_policy_summary, experiment_path
from validate_feature_veto_rule import (
    FeatureRule,
    discover_best_rule,
    feature_matrix,
    negative_series_count,
    rule_from_summary,
    rule_summary,
    split_report,
)


MetricName = str


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
            "reports/router-feature-veto-multifold-validation-alignment-normalized-"
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
    parser.add_argument("--initial-discovery-max-cut", type=int, default=3500)
    parser.add_argument("--validation-cut", type=int, action="append")
    parser.add_argument("--final-holdout-min-cut", type=int, default=4250)
    parser.add_argument("--candidate-limit", type=int, default=200)
    parser.add_argument("--min-discovery-vetoed", type=int, default=8)
    parser.add_argument("--max-thresholds-per-feature", type=int, default=96)
    parser.add_argument(
        "--candidate-objective",
        choices=["aggregate", "downside-aware", "downside-first"],
        default="downside-first",
    )
    parser.add_argument("--max-discovery-negative-increase", type=int, default=0)
    parser.add_argument("--include-series", action="store_true")
    return parser.parse_args()


def default_validation_cuts(args: argparse.Namespace) -> list[int]:
    if args.validation_cut:
        return sorted(set(int(cut) for cut in args.validation_cut))
    return [3750, 4000, 4250]


def subset_by_predicate(
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    predicate: Callable[[dict[str, Any]], bool],
) -> tuple[list[dict[str, Any]], list[str], list[list[float]]]:
    filtered_rows: list[dict[str, Any]] = []
    filtered_selected: list[str] = []
    filtered_matrix: list[list[float]] = []
    for row, selected_family, feature_values in zip(rows, selected_families, matrix):
        if predicate(row):
            filtered_rows.append(row)
            filtered_selected.append(selected_family)
            filtered_matrix.append(feature_values)
    return filtered_rows, filtered_selected, filtered_matrix


def negative_delta(report: dict[str, Any]) -> int:
    return negative_series_count(report, "feature_veto") - negative_series_count(report, "original")


def metric_delta(report: dict[str, Any]) -> float:
    return float(report["metric_delta"])


def changed_windows(report: dict[str, Any]) -> int:
    return int(report["veto"]["changed_windows"])


def split_for_rule(
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
    return split_report(
        name=name,
        rows=rows,
        selected_families=selected_families,
        matrix=matrix,
        rule=rule,
        families=families,
        fallback_family=fallback_family,
        metric=metric,
    )


def validation_score(
    *,
    rule: FeatureRule,
    validation_rows: list[dict[str, Any]],
    validation_selected: list[str],
    validation_matrix: list[list[float]],
    validation_cuts: list[int],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    combined_report = split_for_rule(
        name="validation_combined",
        rows=validation_rows,
        selected_families=validation_selected,
        matrix=validation_matrix,
        rule=rule,
        families=families,
        fallback_family=fallback_family,
        metric=metric,
    )
    fold_reports: list[dict[str, Any]] = []
    for cut in validation_cuts:
        fold_rows, fold_selected, fold_matrix = subset_by_predicate(
            validation_rows,
            validation_selected,
            validation_matrix,
            lambda row, cut=cut: int(row["cut"]) == cut,
        )
        fold_reports.append(
            split_for_rule(
                name=f"validation_cut{cut}",
                rows=fold_rows,
                selected_families=fold_selected,
                matrix=fold_matrix,
                rule=rule,
                families=families,
                fallback_family=fallback_family,
                metric=metric,
            )
        )

    fold_negative_regressions = sum(negative_delta(report) > 0 for report in fold_reports)
    fold_metric_regressions = sum(metric_delta(report) <= 0.0 for report in fold_reports)
    fold_no_exposure = sum(changed_windows(report) == 0 for report in fold_reports)
    combined_negative_delta = negative_delta(combined_report)
    combined_metric_delta = metric_delta(combined_report)
    robust_pass = (
        changed_windows(combined_report) > 0
        and combined_metric_delta > 0.0
        and combined_negative_delta <= 0
        and fold_negative_regressions == 0
    )

    return {
        "rule": rule_summary(rule),
        "combined": combined_report,
        "folds": fold_reports,
        "summary": {
            "combined_metric_delta": combined_metric_delta,
            "combined_negative_series_delta": combined_negative_delta,
            "fold_negative_regressions": fold_negative_regressions,
            "fold_metric_regressions": fold_metric_regressions,
            "fold_no_exposure": fold_no_exposure,
            "robust_pass": robust_pass,
        },
    }


def select_validation_rule(scores: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [score for score in scores if bool(score["summary"]["robust_pass"])]
    pool = passing or scores
    ranked = sorted(
        pool,
        key=lambda score: (
            bool(score["summary"]["robust_pass"]),
            -int(score["summary"]["fold_negative_regressions"]),
            -int(score["summary"]["combined_negative_series_delta"]),
            float(score["summary"]["combined_metric_delta"]),
            -int(score["summary"]["fold_metric_regressions"]),
        ),
        reverse=True,
    )
    selected = dict(ranked[0])
    selected["selection_reason"] = "robust_pass" if passing else "best_available_no_robust_pass"
    return selected


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    router_rows = load_router_rows(experiment_path(args.input))
    router_report = json.loads(experiment_path(args.router_report).read_text())
    policy = selected_policy(router_report, args.policy_summary)
    rows = list(router_rows["data"])
    cuts = [int(cut) for cut in router_rows["cuts"]]
    families = list(router_rows["families"])
    cut_rows = rows_by_cut(rows)
    validation_cuts = default_validation_cuts(args)

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

    discovery_rows, discovery_selected, discovery_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        matrix,
        lambda row: int(row["cut"]) <= args.initial_discovery_max_cut,
    )
    validation_rows, validation_selected, validation_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        matrix,
        lambda row: int(row["cut"]) in set(validation_cuts),
    )
    final_rows, final_selected, final_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        matrix,
        lambda row: int(row["cut"]) > args.final_holdout_min_cut,
    )

    _best_rule, top_discovery_rules, discovery_selection_report = discover_best_rule(
        rows=discovery_rows,
        selected_families=discovery_selected,
        matrix=discovery_matrix,
        feature_names=feature_names,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
        min_vetoed=args.min_discovery_vetoed,
        max_thresholds_per_feature=args.max_thresholds_per_feature,
        top_rules=args.candidate_limit,
        selection_objective=args.candidate_objective,
        max_discovery_negative_increase=args.max_discovery_negative_increase,
    )
    candidate_rules = [rule_from_summary(item["rule"]) for item in top_discovery_rules]
    validation_scores = [
        validation_score(
            rule=rule,
            validation_rows=validation_rows,
            validation_selected=validation_selected,
            validation_matrix=validation_matrix,
            validation_cuts=validation_cuts,
            families=families,
            fallback_family=args.fallback_family,
            metric=args.metric,
        )
        for rule in candidate_rules
    ]
    selected_validation = select_validation_rule(validation_scores)
    selected_rule = rule_from_summary(selected_validation["rule"])
    final_report = split_for_rule(
        name="final_holdout_after_validation",
        rows=final_rows,
        selected_families=final_selected,
        matrix=final_matrix,
        rule=selected_rule,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )

    final_negative_delta = negative_delta(final_report)
    final_relative_lift = float(final_report["feature_veto"]["relative_lift_vs_fallback"])
    if final_report["verdict"] == "rule_improves_split" and final_negative_delta <= 0 and final_relative_lift > 0.0:
        verdict = "future_validated_positive"
    elif final_report["verdict"] == "rule_improves_split" and final_negative_delta <= 0:
        verdict = "incremental_positive_but_below_fallback"
    elif final_report["verdict"] == "rule_improves_split":
        verdict = "aggregate_positive_downside_regressed"
    elif final_report["verdict"] == "no_rule_exposure":
        verdict = "not_validated_no_future_exposure"
    else:
        verdict = "not_promotable"

    return {
        "method": "multifold_feature_veto_validation",
        "input": args.input,
        "router_report": args.router_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "include_series": args.include_series,
        "candidate_objective": args.candidate_objective,
        "initial_discovery_max_cut": args.initial_discovery_max_cut,
        "validation_cuts": validation_cuts,
        "final_holdout_min_cut": args.final_holdout_min_cut,
        "candidate_limit": args.candidate_limit,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "feature_count": len(feature_names),
        "discovery_selection_report": discovery_selection_report,
        "validation_candidate_count": len(validation_scores),
        "validation_robust_pass_count": sum(bool(score["summary"]["robust_pass"]) for score in validation_scores),
        "selected_validation": selected_validation,
        "selected_rule": rule_summary(selected_rule),
        "final_holdout": final_report,
        "verdict": verdict,
        "guardrail": (
            "Candidate feature-veto rules are generated on the initial discovery "
            "split, selected using chronological validation cuts, and evaluated "
            "once on the final holdout cuts."
        ),
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    final_holdout = report["final_holdout"]
    print(
        json.dumps(
            {
                "output": str(output_path),
                "verdict": report["verdict"],
                "candidate_objective": report["candidate_objective"],
                "validation_cuts": report["validation_cuts"],
                "final_holdout_min_cut": report["final_holdout_min_cut"],
                "validation_candidate_count": report["validation_candidate_count"],
                "validation_robust_pass_count": report["validation_robust_pass_count"],
                "selected_rule": report["selected_rule"],
                "selection_reason": report["selected_validation"]["selection_reason"],
                "final_windows": final_holdout["windows"],
                "final_changed_windows": final_holdout["veto"]["changed_windows"],
                "final_metric_delta": final_holdout["metric_delta"],
                "final_negative_series": {
                    "original": final_holdout["original"]["series_summary"]["negative_routed_series_count"],
                    "feature_veto": final_holdout["feature_veto"]["series_summary"]["negative_routed_series_count"],
                },
                "final_verdict": final_holdout["verdict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
