from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from typing import Any, Callable

from diagnose_router_override_failures import (
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import (
    family_error,
    fixed_selection,
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
from validate_feature_veto_rule import (
    FeatureRule,
    discover_best_rule,
    feature_matrix,
    relative_lift,
    rule_from_summary,
    rule_matches,
    rule_summary,
)
from validate_multifold_feature_veto import changed_windows, default_validation_cuts, metric_delta, subset_by_predicate


MetricName = str


@dataclass(frozen=True)
class TwoFeatureRule:
    first: FeatureRule
    second: FeatureRule


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
            "reports/router-two-feature-veto-multifold-validation-alignment-normalized-"
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
    parser.add_argument("--single-candidate-limit", type=int, default=60)
    parser.add_argument("--pair-candidate-limit", type=int, default=400)
    parser.add_argument("--min-discovery-vetoed", type=int, default=8)
    parser.add_argument("--min-pair-discovery-vetoed", type=int, default=3)
    parser.add_argument("--max-validation-fold-no-exposure", type=int, default=0)
    parser.add_argument("--max-thresholds-per-feature", type=int, default=96)
    parser.add_argument(
        "--candidate-objective",
        choices=["aggregate", "downside-aware", "downside-first"],
        default="downside-first",
    )
    parser.add_argument("--max-discovery-negative-increase", type=int, default=0)
    parser.add_argument("--include-series", action="store_true")
    return parser.parse_args()


def two_feature_summary(rule: TwoFeatureRule) -> dict[str, Any]:
    return {
        "operator": "and",
        "first": rule_summary(rule.first),
        "second": rule_summary(rule.second),
    }


def two_feature_from_summary(payload: dict[str, Any]) -> TwoFeatureRule:
    return TwoFeatureRule(
        first=rule_from_summary(payload["first"]),
        second=rule_from_summary(payload["second"]),
    )


def two_feature_matches(rule: TwoFeatureRule, feature_values: list[float]) -> bool:
    return rule_matches(rule.first, feature_values) and rule_matches(rule.second, feature_values)


def apply_two_feature_rule(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    rule: TwoFeatureRule,
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
        should_veto = selected_family != fallback_family and two_feature_matches(rule, feature_values)
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


def two_feature_split_report(
    *,
    name: str,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    matrix: list[list[float]],
    rule: TwoFeatureRule,
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    if not rows:
        return {
            "name": name,
            "windows": 0,
            "rule": two_feature_summary(rule),
            "original": None,
            "feature_veto": None,
            "veto": {"changed_windows": 0},
            "metric_delta": 0.0,
            "relative_metric_delta_vs_original": 0.0,
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
    veto_selected, veto_stats = apply_two_feature_rule(
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
    metric_delta_value = original_metric - veto_metric
    if veto_stats["changed_windows"] == 0:
        verdict = "no_rule_exposure"
    elif metric_delta_value > 0.0:
        verdict = "rule_improves_split"
    elif metric_delta_value == 0.0:
        verdict = "rule_no_metric_change"
    else:
        verdict = "rule_hurts_split"

    return {
        "name": name,
        "windows": len(rows),
        "rule": two_feature_summary(rule),
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
        "metric_delta": metric_delta_value,
        "relative_metric_delta_vs_original": metric_delta_value / original_metric,
        "verdict": verdict,
    }


def negative_series_count(report: dict[str, Any], section: str) -> int:
    payload = report[section]
    if payload is None:
        return 0
    return int(payload["series_summary"]["negative_routed_series_count"])


def negative_delta(report: dict[str, Any]) -> int:
    return negative_series_count(report, "feature_veto") - negative_series_count(report, "original")


def pair_discovery_score(
    *,
    rule: TwoFeatureRule,
    discovery_rows: list[dict[str, Any]],
    discovery_selected: list[str],
    discovery_matrix: list[list[float]],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    report = two_feature_split_report(
        name="discovery_pair",
        rows=discovery_rows,
        selected_families=discovery_selected,
        matrix=discovery_matrix,
        rule=rule,
        families=families,
        fallback_family=fallback_family,
        metric=metric,
    )
    return {
        "rule": two_feature_summary(rule),
        "changed_windows": changed_windows(report),
        "metric_delta": metric_delta(report),
        "negative_series_delta": negative_delta(report),
        "report": report,
    }


def generate_pair_candidates(
    *,
    single_rules: list[FeatureRule],
    discovery_rows: list[dict[str, Any]],
    discovery_selected: list[str],
    discovery_matrix: list[list[float]],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    min_pair_discovery_vetoed: int,
    max_discovery_negative_increase: int,
    pair_candidate_limit: int,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for first, second in itertools.combinations(single_rules, 2):
        if first.feature_index == second.feature_index:
            continue
        rule = TwoFeatureRule(first=first, second=second)
        score = pair_discovery_score(
            rule=rule,
            discovery_rows=discovery_rows,
            discovery_selected=discovery_selected,
            discovery_matrix=discovery_matrix,
            families=families,
            fallback_family=fallback_family,
            metric=metric,
        )
        if int(score["changed_windows"]) < min_pair_discovery_vetoed:
            continue
        if float(score["metric_delta"]) <= 0.0:
            continue
        if int(score["negative_series_delta"]) > max_discovery_negative_increase:
            continue
        scored.append(score)

    scored.sort(
        key=lambda item: (
            -int(item["negative_series_delta"]),
            float(item["metric_delta"]),
            int(item["changed_windows"]),
        ),
        reverse=True,
    )
    return scored[:pair_candidate_limit]


def two_feature_validation_score(
    *,
    rule: TwoFeatureRule,
    validation_rows: list[dict[str, Any]],
    validation_selected: list[str],
    validation_matrix: list[list[float]],
    validation_cuts: list[int],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    max_fold_no_exposure: int,
) -> dict[str, Any]:
    combined_report = two_feature_split_report(
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
            two_feature_split_report(
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
        and fold_no_exposure <= max_fold_no_exposure
    )

    return {
        "rule": two_feature_summary(rule),
        "combined": combined_report,
        "folds": fold_reports,
        "summary": {
            "combined_metric_delta": combined_metric_delta,
            "combined_negative_series_delta": combined_negative_delta,
            "fold_negative_regressions": fold_negative_regressions,
            "fold_metric_regressions": fold_metric_regressions,
            "fold_no_exposure": fold_no_exposure,
            "max_fold_no_exposure": max_fold_no_exposure,
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


def verdict_for_final(final_report: dict[str, Any]) -> str:
    final_negative_delta = negative_delta(final_report)
    final_relative_lift = float(final_report["feature_veto"]["relative_lift_vs_fallback"])
    if final_report["verdict"] == "rule_improves_split" and final_negative_delta <= 0 and final_relative_lift > 0.0:
        return "future_validated_positive"
    if final_report["verdict"] == "rule_improves_split" and final_negative_delta <= 0:
        return "incremental_positive_but_below_fallback"
    if final_report["verdict"] == "rule_improves_split":
        return "aggregate_positive_downside_regressed"
    if final_report["verdict"] == "no_rule_exposure":
        return "not_validated_no_future_exposure"
    return "not_promotable"


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

    _best_rule, top_single_rules, discovery_selection_report = discover_best_rule(
        rows=discovery_rows,
        selected_families=discovery_selected,
        matrix=discovery_matrix,
        feature_names=feature_names,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
        min_vetoed=args.min_discovery_vetoed,
        max_thresholds_per_feature=args.max_thresholds_per_feature,
        top_rules=args.single_candidate_limit,
        selection_objective=args.candidate_objective,
        max_discovery_negative_increase=args.max_discovery_negative_increase,
    )
    single_rules = [rule_from_summary(item["rule"]) for item in top_single_rules]
    pair_candidates = generate_pair_candidates(
        single_rules=single_rules,
        discovery_rows=discovery_rows,
        discovery_selected=discovery_selected,
        discovery_matrix=discovery_matrix,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
        min_pair_discovery_vetoed=args.min_pair_discovery_vetoed,
        max_discovery_negative_increase=args.max_discovery_negative_increase,
        pair_candidate_limit=args.pair_candidate_limit,
    )
    validation_scores = [
        two_feature_validation_score(
            rule=two_feature_from_summary(candidate["rule"]),
            validation_rows=validation_rows,
            validation_selected=validation_selected,
            validation_matrix=validation_matrix,
            validation_cuts=validation_cuts,
            families=families,
            fallback_family=args.fallback_family,
            metric=args.metric,
            max_fold_no_exposure=args.max_validation_fold_no_exposure,
        )
        for candidate in pair_candidates
    ]
    if not validation_scores:
        raise ValueError("no two-feature validation candidates found")

    selected_validation = select_validation_rule(validation_scores)
    selected_rule = two_feature_from_summary(selected_validation["rule"])
    final_report = two_feature_split_report(
        name="final_holdout_after_validation",
        rows=final_rows,
        selected_families=final_selected,
        matrix=final_matrix,
        rule=selected_rule,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )

    return {
        "method": "multifold_two_feature_veto_validation",
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
        "single_candidate_limit": args.single_candidate_limit,
        "pair_candidate_limit": args.pair_candidate_limit,
        "max_validation_fold_no_exposure": args.max_validation_fold_no_exposure,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "feature_count": len(feature_names),
        "discovery_selection_report": discovery_selection_report,
        "single_candidate_count": len(single_rules),
        "pair_candidate_count": len(pair_candidates),
        "validation_candidate_count": len(validation_scores),
        "validation_robust_pass_count": sum(bool(score["summary"]["robust_pass"]) for score in validation_scores),
        "selected_validation": selected_validation,
        "selected_rule": two_feature_summary(selected_rule),
        "final_holdout": final_report,
        "verdict": verdict_for_final(final_report),
        "guardrail": (
            "Two-feature AND veto rules are built from initial discovery single-rule "
            "candidates, selected using chronological validation cuts, and evaluated "
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
                "single_candidate_count": report["single_candidate_count"],
                "pair_candidate_count": report["pair_candidate_count"],
                "max_validation_fold_no_exposure": report["max_validation_fold_no_exposure"],
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
                "final_relative_lift": final_holdout["feature_veto"]["relative_lift_vs_fallback"],
                "final_verdict": final_holdout["verdict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
