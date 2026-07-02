from __future__ import annotations

import argparse
import json
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
from router_fallback_veto import VetoExample, apply_neighbor_regret_veto
from validate_feature_veto_rule import relative_lift
from validate_multifold_feature_veto import changed_windows, default_validation_cuts, metric_delta, subset_by_predicate
from validate_multifold_two_feature_veto import negative_delta, verdict_for_final


MetricName = str


@dataclass(frozen=True)
class SupervisedVetoConfig:
    k: int
    regret_threshold: float


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
            "reports/router-supervised-veto-multifold-validation-alignment-normalized-"
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
    parser.add_argument("--k", type=int, action="append")
    parser.add_argument("--regret-threshold", type=float, action="append")
    parser.add_argument("--max-validation-fold-no-exposure", type=int, default=0)
    parser.add_argument("--include-series", action="store_true")
    return parser.parse_args()


def default_k_values(requested: list[int] | None) -> list[int]:
    raw_values = requested or [5, 10, 25, 50, 100]
    values: list[int] = []
    for value in raw_values:
        if value > 0 and value not in values:
            values.append(value)
    return values


def default_threshold_values(requested: list[float] | None) -> list[float]:
    raw_values = requested or [-0.001, -0.0005, 0.0, 0.00025, 0.0005, 0.001]
    values: list[float] = []
    for value in raw_values:
        if value not in values:
            values.append(value)
    return values


def config_summary(config: SupervisedVetoConfig) -> dict[str, Any]:
    return {
        "model": "knn_regret_veto",
        "k": config.k,
        "regret_threshold": config.regret_threshold,
    }


def config_from_summary(payload: dict[str, Any]) -> SupervisedVetoConfig:
    return SupervisedVetoConfig(k=int(payload["k"]), regret_threshold=float(payload["regret_threshold"]))


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


def supervised_examples(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> list[VetoExample]:
    examples: list[VetoExample] = []
    for row, selected_family in zip(rows, selected_families):
        if selected_family == fallback_family:
            continue
        selected_error = family_error(row, selected_family, metric)
        fallback_error = family_error(row, fallback_family, metric)
        examples.append(
            VetoExample(
                row=row,
                selected_family=selected_family,
                regret_vs_fallback=selected_error - fallback_error,
            )
        )
    return examples


def supervised_split_report(
    *,
    name: str,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    training_examples: list[VetoExample],
    config: SupervisedVetoConfig,
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    include_series: bool,
) -> dict[str, Any]:
    if not rows:
        return {
            "name": name,
            "windows": 0,
            "config": config_summary(config),
            "training_examples": len(training_examples),
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
    veto_selected, neighbor_report = apply_neighbor_regret_veto(
        eval_rows=rows,
        selected_families=selected_families,
        examples=training_examples,
        families=families,
        fallback_family=fallback_family,
        include_series=include_series,
        k=config.k,
        regret_threshold=config.regret_threshold,
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
    changed = int(neighbor_report["vetoed_windows"])
    if changed == 0:
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
        "config": config_summary(config),
        "training_examples": len(training_examples),
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
        "veto": {
            "mode": "supervised_knn_regret_veto",
            "changed_windows": changed,
            "neighbor": neighbor_report,
        },
        "metric_delta": metric_delta_value,
        "relative_metric_delta_vs_original": metric_delta_value / original_metric,
        "verdict": verdict,
    }


def validation_score(
    *,
    config: SupervisedVetoConfig,
    training_examples: list[VetoExample],
    validation_rows: list[dict[str, Any]],
    validation_selected: list[str],
    validation_cuts: list[int],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    include_series: bool,
    max_fold_no_exposure: int,
) -> dict[str, Any]:
    combined_report = supervised_split_report(
        name="validation_combined",
        rows=validation_rows,
        selected_families=validation_selected,
        training_examples=training_examples,
        config=config,
        families=families,
        fallback_family=fallback_family,
        metric=metric,
        include_series=include_series,
    )
    fold_reports: list[dict[str, Any]] = []
    placeholder_matrix = [[] for _row in validation_rows]
    for cut in validation_cuts:
        fold_rows, fold_selected, _fold_matrix = subset_by_predicate(
            validation_rows,
            validation_selected,
            placeholder_matrix,
            lambda row, cut=cut: int(row["cut"]) == cut,
        )
        fold_reports.append(
            supervised_split_report(
                name=f"validation_cut{cut}",
                rows=fold_rows,
                selected_families=fold_selected,
                training_examples=training_examples,
                config=config,
                families=families,
                fallback_family=fallback_family,
                metric=metric,
                include_series=include_series,
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
        "config": config_summary(config),
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


def select_validation_config(scores: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [score for score in scores if bool(score["summary"]["robust_pass"])]
    validation_positive = [
        score
        for score in scores
        if float(score["summary"]["combined_metric_delta"]) > 0.0
        and int(score["summary"]["combined_negative_series_delta"]) <= 0
        and int(score["summary"]["fold_negative_regressions"]) == 0
    ]
    pool = passing or validation_positive or scores
    ranked = sorted(
        pool,
        key=lambda score: (
            bool(score["summary"]["robust_pass"]),
            float(score["summary"]["combined_metric_delta"]) > 0.0,
            -int(score["summary"]["fold_negative_regressions"]),
            -int(score["summary"]["combined_negative_series_delta"]),
            float(score["summary"]["combined_metric_delta"]),
            -int(score["summary"]["fold_metric_regressions"]),
            -int(score["summary"]["fold_no_exposure"]),
            changed_windows(score["combined"]),
        ),
        reverse=True,
    )
    selected = dict(ranked[0])
    if passing:
        selected["selection_reason"] = "robust_pass"
    elif validation_positive:
        selected["selection_reason"] = "validation_positive_no_robust_pass"
    else:
        selected["selection_reason"] = "best_available_no_robust_pass"
    return selected


def compact_validation_score(score: dict[str, Any]) -> dict[str, Any]:
    combined = score["combined"]
    return {
        "config": score["config"],
        "summary": score["summary"],
        "combined_changed_windows": changed_windows(combined),
        "combined_metric_delta": metric_delta(combined),
        "combined_negative_series_delta": negative_delta(combined),
    }


def validation_positive(score: dict[str, Any]) -> bool:
    return (
        float(score["summary"]["combined_metric_delta"]) > 0.0
        and int(score["summary"]["combined_negative_series_delta"]) <= 0
        and int(score["summary"]["fold_negative_regressions"]) == 0
    )


def strict_validation_positive(score: dict[str, Any]) -> bool:
    return (
        validation_positive(score)
        and int(score["summary"]["fold_metric_regressions"]) == 0
        and int(score["summary"]["fold_no_exposure"]) <= int(score["summary"]["max_fold_no_exposure"])
    )


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

    placeholder_matrix = [[] for _row in routed_rows]
    discovery_rows, discovery_selected, _discovery_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        placeholder_matrix,
        lambda row: int(row["cut"]) <= args.initial_discovery_max_cut,
    )
    validation_rows, validation_selected, _validation_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        placeholder_matrix,
        lambda row: int(row["cut"]) in set(validation_cuts),
    )
    final_rows, final_selected, _final_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        placeholder_matrix,
        lambda row: int(row["cut"]) > args.final_holdout_min_cut,
    )
    final_train_rows, final_train_selected, _final_train_matrix = subset_by_predicate(
        routed_rows,
        routed_selected,
        placeholder_matrix,
        lambda row: int(row["cut"]) <= args.final_holdout_min_cut,
    )

    discovery_examples = supervised_examples(
        rows=discovery_rows,
        selected_families=discovery_selected,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    final_train_examples = supervised_examples(
        rows=final_train_rows,
        selected_families=final_train_selected,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    if not discovery_examples:
        raise ValueError("discovery split has no override examples")

    configs = [
        SupervisedVetoConfig(k=k, regret_threshold=threshold)
        for k in default_k_values(args.k)
        for threshold in default_threshold_values(args.regret_threshold)
    ]
    validation_scores = [
        validation_score(
            config=config,
            training_examples=discovery_examples,
            validation_rows=validation_rows,
            validation_selected=validation_selected,
            validation_cuts=validation_cuts,
            families=families,
            fallback_family=args.fallback_family,
            metric=args.metric,
            include_series=args.include_series,
            max_fold_no_exposure=args.max_validation_fold_no_exposure,
        )
        for config in configs
    ]
    selected_validation = select_validation_config(validation_scores)
    selected_config = config_from_summary(selected_validation["config"])
    final_report = supervised_split_report(
        name="final_holdout_after_validation",
        rows=final_rows,
        selected_families=final_selected,
        training_examples=final_train_examples,
        config=selected_config,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
        include_series=args.include_series,
    )

    return {
        "method": "multifold_supervised_knn_regret_veto_validation",
        "input": args.input,
        "router_report": args.router_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "include_series": args.include_series,
        "initial_discovery_max_cut": args.initial_discovery_max_cut,
        "validation_cuts": validation_cuts,
        "final_holdout_min_cut": args.final_holdout_min_cut,
        "k_values": default_k_values(args.k),
        "regret_thresholds": default_threshold_values(args.regret_threshold),
        "max_validation_fold_no_exposure": args.max_validation_fold_no_exposure,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "discovery_examples": len(discovery_examples),
        "final_train_examples": len(final_train_examples),
        "validation_candidate_count": len(validation_scores),
        "validation_robust_pass_count": sum(bool(score["summary"]["robust_pass"]) for score in validation_scores),
        "validation_positive_count": sum(validation_positive(score) for score in validation_scores),
        "validation_strict_positive_count": sum(strict_validation_positive(score) for score in validation_scores),
        "validation_score_summaries": [
            compact_validation_score(score)
            for score in sorted(
                validation_scores,
                key=lambda score: (
                    bool(score["summary"]["robust_pass"]),
                    float(score["summary"]["combined_metric_delta"]) > 0.0,
                    -int(score["summary"]["fold_negative_regressions"]),
                    -int(score["summary"]["combined_negative_series_delta"]),
                    float(score["summary"]["combined_metric_delta"]),
                    -int(score["summary"]["fold_metric_regressions"]),
                    -int(score["summary"]["fold_no_exposure"]),
                    changed_windows(score["combined"]),
                ),
                reverse=True,
            )
        ],
        "selected_validation": selected_validation,
        "selected_config": config_summary(selected_config),
        "final_holdout": final_report,
        "verdict": verdict_for_final(final_report),
        "guardrail": (
            "KNN-regret veto configs are trained on discovery override examples, "
            "selected on chronological validation folds, then retrained only on "
            "pre-final examples before one final holdout evaluation."
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
                "validation_cuts": report["validation_cuts"],
                "discovery_examples": report["discovery_examples"],
                "final_train_examples": report["final_train_examples"],
                "validation_candidate_count": report["validation_candidate_count"],
                "validation_robust_pass_count": report["validation_robust_pass_count"],
                "validation_positive_count": report["validation_positive_count"],
                "validation_strict_positive_count": report["validation_strict_positive_count"],
                "selected_config": report["selected_config"],
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
