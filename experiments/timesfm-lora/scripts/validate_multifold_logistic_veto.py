from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from diagnose_router_override_failures import (
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import (
    FeatureFrame,
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
from router_fallback_veto import VetoExample, build_veto_matrix
from validate_feature_veto_rule import relative_lift
from validate_multifold_feature_veto import changed_windows, default_validation_cuts, metric_delta, subset_by_predicate
from validate_multifold_supervised_veto import supervised_examples
from validate_multifold_two_feature_veto import negative_delta, verdict_for_final


MetricName = str


@dataclass(frozen=True)
class LogisticVetoConfig:
    l2: float
    probability_threshold: float
    learning_rate: float
    steps: int


@dataclass(frozen=True)
class LogisticVetoModel:
    config: LogisticVetoConfig
    frame: FeatureFrame
    mean: np.ndarray
    scale: np.ndarray
    weights: np.ndarray
    bias: float
    training_examples: int
    training_positive_rate: float
    training_loss: float
    training_brier: float


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
            "reports/router-logistic-veto-strict-gate-alignment-normalized-"
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
    parser.add_argument("--l2", type=float, action="append")
    parser.add_argument("--probability-threshold", type=float, action="append")
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--max-validation-fold-no-exposure", type=int, default=0)
    parser.add_argument("--selection-gate", choices=["strict", "robust"], default="strict")
    parser.add_argument("--include-series", action="store_true")
    return parser.parse_args()


def default_l2_values(requested: list[float] | None) -> list[float]:
    raw_values = requested or [0.0, 0.001, 0.01, 0.1]
    values: list[float] = []
    for value in raw_values:
        if value >= 0.0 and value not in values:
            values.append(value)
    return values


def default_threshold_values(requested: list[float] | None) -> list[float]:
    raw_values = requested or [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    values: list[float] = []
    for value in raw_values:
        if 0.0 <= value <= 1.0 and value not in values:
            values.append(value)
    return values


def config_summary(config: LogisticVetoConfig) -> dict[str, Any]:
    return {
        "model": "logistic_fallback_veto",
        "l2": config.l2,
        "probability_threshold": config.probability_threshold,
        "learning_rate": config.learning_rate,
        "steps": config.steps,
    }


def config_from_summary(payload: dict[str, Any]) -> LogisticVetoConfig:
    return LogisticVetoConfig(
        l2=float(payload["l2"]),
        probability_threshold=float(payload["probability_threshold"]),
        learning_rate=float(payload["learning_rate"]),
        steps=int(payload["steps"]),
    )


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0)))


def normalized_matrix(matrix: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return np.nan_to_num((matrix - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)


def labels_from_examples(examples: list[VetoExample]) -> np.ndarray:
    return np.array([1.0 if example.regret_vs_fallback > 0.0 else 0.0 for example in examples], dtype=float)


def balanced_sample_weights(labels: np.ndarray) -> np.ndarray:
    positive_rate = float(labels.mean())
    if positive_rate <= 0.0 or positive_rate >= 1.0:
        return np.ones_like(labels)
    positive_weight = 0.5 / positive_rate
    negative_weight = 0.5 / (1.0 - positive_rate)
    return np.where(labels > 0.5, positive_weight, negative_weight)


def logistic_loss(probabilities: np.ndarray, labels: np.ndarray, weights: np.ndarray, model_weights: np.ndarray, l2: float) -> float:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    data_loss = -float((weights * (labels * np.log(clipped) + (1.0 - labels) * np.log(1.0 - clipped))).mean())
    return data_loss + 0.5 * l2 * float((model_weights * model_weights).sum())


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    return float(((probabilities - labels) ** 2).mean())


def train_logistic_model(
    *,
    examples: list[VetoExample],
    families: list[str],
    include_series: bool,
    config: LogisticVetoConfig,
) -> LogisticVetoModel:
    if not examples:
        raise ValueError("cannot train logistic veto without examples")

    train_rows = [example.row for example in examples]
    train_families = [example.selected_family for example in examples]
    labels = labels_from_examples(examples)
    frame, matrix = build_veto_matrix(
        rows=train_rows,
        selected_families=train_families,
        families=families,
        include_series=include_series,
    )
    mean = np.nanmean(matrix, axis=0)
    scale = np.nanstd(matrix, axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    features = normalized_matrix(matrix, mean, scale)
    sample_weights = balanced_sample_weights(labels)
    model_weights = np.zeros(features.shape[1], dtype=float)
    bias = 0.0

    for _step in range(config.steps):
        probabilities = sigmoid(features @ model_weights + bias)
        errors = (probabilities - labels) * sample_weights
        gradient = (features.T @ errors) / len(labels) + config.l2 * model_weights
        bias_gradient = float(errors.mean())
        model_weights -= config.learning_rate * gradient
        bias -= config.learning_rate * bias_gradient

    probabilities = sigmoid(features @ model_weights + bias)
    return LogisticVetoModel(
        config=config,
        frame=frame,
        mean=mean,
        scale=scale,
        weights=model_weights,
        bias=bias,
        training_examples=len(examples),
        training_positive_rate=float(labels.mean()),
        training_loss=logistic_loss(probabilities, labels, sample_weights, model_weights, config.l2),
        training_brier=brier_score(probabilities, labels),
    )


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


def apply_logistic_veto(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    model: LogisticVetoModel,
    families: list[str],
    fallback_family: str,
    include_series: bool,
) -> tuple[list[str], dict[str, Any]]:
    override_indices = [
        index for index, selected_family in enumerate(selected_families) if selected_family != fallback_family
    ]
    if not override_indices:
        return selected_families, {
            "mode": "no_current_overrides",
            "changed_windows": 0,
            "training_examples": model.training_examples,
        }

    override_rows = [rows[index] for index in override_indices]
    override_families = [selected_families[index] for index in override_indices]
    _eval_frame, matrix = build_veto_matrix(
        rows=override_rows,
        selected_families=override_families,
        families=families,
        include_series=include_series,
        reference=model.frame,
    )
    features = normalized_matrix(matrix, model.mean, model.scale)
    probabilities = sigmoid(features @ model.weights + model.bias)
    vetoed = list(selected_families)
    vetoed_probabilities: list[float] = []
    kept_probabilities: list[float] = []
    vetoed_by_family: dict[str, int] = {}
    for local_index, probability in enumerate(probabilities):
        global_index = override_indices[local_index]
        selected_family = selected_families[global_index]
        if float(probability) >= model.config.probability_threshold:
            vetoed[global_index] = fallback_family
            vetoed_probabilities.append(float(probability))
            vetoed_by_family[selected_family] = vetoed_by_family.get(selected_family, 0) + 1
        else:
            kept_probabilities.append(float(probability))

    return vetoed, {
        "mode": "logistic_fallback_probability_veto",
        "changed_windows": len(vetoed_probabilities),
        "training_examples": model.training_examples,
        "training_positive_rate": model.training_positive_rate,
        "training_loss": model.training_loss,
        "training_brier": model.training_brier,
        "current_overrides": len(override_indices),
        "probability_threshold": model.config.probability_threshold,
        "mean_probability": float(probabilities.mean()) if len(probabilities) else None,
        "mean_vetoed_probability": sum(vetoed_probabilities) / len(vetoed_probabilities) if vetoed_probabilities else None,
        "mean_kept_probability": sum(kept_probabilities) / len(kept_probabilities) if kept_probabilities else None,
        "vetoed_by_family": dict(sorted(vetoed_by_family.items())),
    }


def logistic_split_report(
    *,
    name: str,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    training_examples: list[VetoExample],
    config: LogisticVetoConfig,
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
    model = train_logistic_model(
        examples=training_examples,
        families=families,
        include_series=include_series,
        config=config,
    )
    veto_selected, veto_stats = apply_logistic_veto(
        rows=rows,
        selected_families=selected_families,
        model=model,
        families=families,
        fallback_family=fallback_family,
        include_series=include_series,
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
    changed = int(veto_stats["changed_windows"])
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
        "veto": veto_stats,
        "metric_delta": metric_delta_value,
        "relative_metric_delta_vs_original": metric_delta_value / original_metric,
        "verdict": verdict,
    }


def validation_score(
    *,
    config: LogisticVetoConfig,
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
    combined_report = logistic_split_report(
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
            logistic_split_report(
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


def ranked_validation_scores(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        scores,
        key=lambda score: (
            strict_validation_positive(score),
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


def select_validation_config(scores: list[dict[str, Any]], *, selection_gate: str) -> dict[str, Any]:
    strict_passing = [score for score in scores if strict_validation_positive(score)]
    if selection_gate == "strict":
        if not strict_passing:
            return {
                "selection_reason": "strict_gate_no_candidate",
                "strict_gate_pass": False,
            }
        selected = dict(ranked_validation_scores(strict_passing)[0])
        selected["selection_reason"] = "strict_positive"
        selected["strict_gate_pass"] = True
        return selected

    passing = [score for score in scores if bool(score["summary"]["robust_pass"])]
    validation_positive_scores = [score for score in scores if validation_positive(score)]
    pool = passing or validation_positive_scores or scores
    selected = dict(ranked_validation_scores(pool)[0])
    if passing:
        selected["selection_reason"] = "robust_pass"
    elif validation_positive_scores:
        selected["selection_reason"] = "validation_positive_no_robust_pass"
    else:
        selected["selection_reason"] = "best_available_no_robust_pass"
    selected["strict_gate_pass"] = strict_validation_positive(selected)
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
        LogisticVetoConfig(
            l2=l2,
            probability_threshold=threshold,
            learning_rate=args.learning_rate,
            steps=args.steps,
        )
        for l2 in default_l2_values(args.l2)
        for threshold in default_threshold_values(args.probability_threshold)
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
    selected_validation = select_validation_config(validation_scores, selection_gate=args.selection_gate)
    selected_config: LogisticVetoConfig | None = None
    final_report: dict[str, Any] | None = None
    verdict = "strict_gate_no_candidate"
    if args.selection_gate != "strict" or bool(selected_validation.get("strict_gate_pass", True)):
        selected_config = config_from_summary(selected_validation["config"])
        final_report = logistic_split_report(
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
        verdict = verdict_for_final(final_report)

    return {
        "method": "multifold_logistic_fallback_veto_validation",
        "input": args.input,
        "router_report": args.router_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "include_series": args.include_series,
        "selection_gate": args.selection_gate,
        "initial_discovery_max_cut": args.initial_discovery_max_cut,
        "validation_cuts": validation_cuts,
        "final_holdout_min_cut": args.final_holdout_min_cut,
        "l2_values": default_l2_values(args.l2),
        "probability_thresholds": default_threshold_values(args.probability_threshold),
        "learning_rate": args.learning_rate,
        "steps": args.steps,
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
            for score in ranked_validation_scores(validation_scores)
        ],
        "selected_validation": selected_validation,
        "selected_config": config_summary(selected_config) if selected_config else None,
        "final_holdout_evaluated": final_report is not None,
        "final_holdout": final_report,
        "verdict": verdict,
        "guardrail": (
            "Logistic fallback-veto probabilities are trained on discovery override "
            "examples, selected on chronological validation folds, and strict mode "
            "fails closed before final holdout when no candidate avoids fold metric/downside regressions."
        ),
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    payload = {
        "output": str(output_path),
        "verdict": report["verdict"],
        "selection_gate": report["selection_gate"],
        "validation_cuts": report["validation_cuts"],
        "discovery_examples": report["discovery_examples"],
        "final_train_examples": report["final_train_examples"],
        "validation_candidate_count": report["validation_candidate_count"],
        "validation_robust_pass_count": report["validation_robust_pass_count"],
        "validation_positive_count": report["validation_positive_count"],
        "validation_strict_positive_count": report["validation_strict_positive_count"],
        "selected_config": report["selected_config"],
        "selection_reason": report["selected_validation"]["selection_reason"],
        "final_holdout_evaluated": report["final_holdout_evaluated"],
    }
    final_holdout = report["final_holdout"]
    if final_holdout is not None:
        payload.update(
            {
                "final_windows": final_holdout["windows"],
                "final_changed_windows": final_holdout["veto"]["changed_windows"],
                "final_metric_delta": final_holdout["metric_delta"],
                "final_negative_series": {
                    "original": final_holdout["original"]["series_summary"]["negative_routed_series_count"],
                    "feature_veto": final_holdout["feature_veto"]["series_summary"]["negative_routed_series_count"],
                },
                "final_relative_lift": final_holdout["feature_veto"]["relative_lift_vs_fallback"],
                "final_verdict": final_holdout["verdict"],
            }
        )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
