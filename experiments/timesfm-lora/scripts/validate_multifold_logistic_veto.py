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
    false_positive_weight: float
    training_weighting: str
    training_time_bins: int
    abstention_mode: str
    positive_probability_quantile: float
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
    abstention_probability_gate: float | None
    training_examples: int
    training_positive_rate: float
    training_loss: float
    training_brier: float
    training_probability_summary: dict[str, Any]


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
    parser.add_argument("--false-positive-weight", type=float, action="append")
    parser.add_argument(
        "--training-weighting",
        choices=[
            "global-label-balanced",
            "cut-label-balanced",
            "time-bin-label-balanced",
            "margin-label-balanced",
            "time-bin-margin-balanced",
        ],
        action="append",
    )
    parser.add_argument("--training-time-bins", type=int, default=3)
    parser.add_argument("--abstention-mode", choices=["none", "positive-quantile"], action="append")
    parser.add_argument("--positive-probability-quantile", type=float, action="append")
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--min-validation-changed-windows", type=int, default=1)
    parser.add_argument("--min-validation-fold-changed-windows", type=int, default=1)
    parser.add_argument("--min-final-changed-windows", type=int, default=1)
    parser.add_argument("--max-validation-fold-no-exposure", type=int, default=0)
    parser.add_argument("--selection-gate", choices=["strict", "robust"], default="strict")
    parser.add_argument("--selection-objective", choices=["combined", "worst-fold"], default="combined")
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


def final_exposure_pass(final_report: dict[str, Any], min_changed_windows: int) -> bool:
    return changed_windows(final_report) >= min_changed_windows


def verdict_for_final_with_exposure(final_report: dict[str, Any], min_changed_windows: int) -> str:
    base_verdict = verdict_for_final(final_report)
    if base_verdict == "not_validated_no_future_exposure":
        return base_verdict
    if not final_exposure_pass(final_report, min_changed_windows):
        return "not_validated_final_underexposed"
    return base_verdict


def default_false_positive_weights(requested: list[float] | None) -> list[float]:
    raw_values = requested or [1.0]
    values: list[float] = []
    for value in raw_values:
        if value > 0.0 and value not in values:
            values.append(value)
    return values


def default_training_weightings(requested: list[str] | None) -> list[str]:
    raw_values = requested or ["global-label-balanced"]
    values: list[str] = []
    for value in raw_values:
        if value not in values:
            values.append(value)
    return values


def default_abstention_modes(requested: list[str] | None) -> list[str]:
    raw_values = requested or ["none"]
    values: list[str] = []
    for value in raw_values:
        if value not in values:
            values.append(value)
    return values


def default_positive_probability_quantiles(requested: list[float] | None) -> list[float]:
    raw_values = requested or [0.75]
    values: list[float] = []
    for value in raw_values:
        if 0.0 <= value <= 1.0 and value not in values:
            values.append(value)
    return values


def example_margin_summary(examples: list[VetoExample]) -> dict[str, Any]:
    if not examples:
        return {
            "examples": 0,
            "fallback_better": 0,
            "selected_better": 0,
        }
    margins = np.asarray([abs(example.regret_vs_fallback) for example in examples], dtype=float)
    return {
        "examples": len(examples),
        "fallback_better": sum(example.regret_vs_fallback > 0.0 for example in examples),
        "selected_better": sum(example.regret_vs_fallback <= 0.0 for example in examples),
        "mean_abs_regret": float(margins.mean()),
        "median_abs_regret": float(np.median(margins)),
        "p90_abs_regret": float(np.quantile(margins, 0.9)),
        "max_abs_regret": float(margins.max()),
    }


def config_summary(config: LogisticVetoConfig) -> dict[str, Any]:
    return {
        "model": "logistic_fallback_veto",
        "l2": config.l2,
        "probability_threshold": config.probability_threshold,
        "false_positive_weight": config.false_positive_weight,
        "training_weighting": config.training_weighting,
        "training_time_bins": config.training_time_bins,
        "abstention_mode": config.abstention_mode,
        "positive_probability_quantile": config.positive_probability_quantile,
        "learning_rate": config.learning_rate,
        "steps": config.steps,
    }


def config_from_summary(payload: dict[str, Any]) -> LogisticVetoConfig:
    return LogisticVetoConfig(
        l2=float(payload["l2"]),
        probability_threshold=float(payload["probability_threshold"]),
        false_positive_weight=float(payload.get("false_positive_weight", 1.0)),
        training_weighting=str(payload.get("training_weighting", "global-label-balanced")),
        training_time_bins=int(payload.get("training_time_bins", 3)),
        abstention_mode=str(payload.get("abstention_mode", "none")),
        positive_probability_quantile=float(payload.get("positive_probability_quantile", 0.75)),
        learning_rate=float(payload["learning_rate"]),
        steps=int(payload["steps"]),
    )


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0)))


def normalized_matrix(matrix: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return np.nan_to_num((matrix - mean) / scale, nan=0.0, posinf=0.0, neginf=0.0)


def labels_from_examples(examples: list[VetoExample]) -> np.ndarray:
    return np.array([1.0 if example.regret_vs_fallback > 0.0 else 0.0 for example in examples], dtype=float)


def example_start_index(example: VetoExample) -> int:
    if "start_index" in example.row:
        return int(example.row["start_index"])
    return int(example.row["runtime_features"]["start_index"])


def example_cut_label_summary(examples: list[VetoExample]) -> dict[str, Any]:
    summary: dict[str, dict[str, int]] = {}
    for example in examples:
        cut = str(int(example.row["cut"]))
        label_name = "fallback_better" if example.regret_vs_fallback > 0.0 else "selected_better"
        if cut not in summary:
            summary[cut] = {"fallback_better": 0, "selected_better": 0}
        summary[cut][label_name] += 1
    return dict(sorted(summary.items(), key=lambda item: int(item[0])))


def time_bin_assignments(examples: list[VetoExample], bin_count: int) -> list[tuple[int, int]]:
    effective_bin_count = max(1, bin_count)
    cut_start_indices: dict[int, list[int]] = {}
    for example in examples:
        cut = int(example.row["cut"])
        cut_start_indices.setdefault(cut, []).append(example_start_index(example))

    cut_rank_maps: dict[int, dict[int, int]] = {}
    for cut, start_indices in cut_start_indices.items():
        unique_start_indices = sorted(set(start_indices))
        cut_rank_maps[cut] = {start_index: rank for rank, start_index in enumerate(unique_start_indices)}

    assignments: list[tuple[int, int]] = []
    for example in examples:
        cut = int(example.row["cut"])
        rank_map = cut_rank_maps[cut]
        unique_count = len(rank_map)
        if unique_count <= 1:
            time_bin = 0
        else:
            rank = rank_map[example_start_index(example)]
            time_bin = min(effective_bin_count - 1, (rank * effective_bin_count) // unique_count)
        assignments.append((cut, time_bin))
    return assignments


def example_time_bin_label_summary(examples: list[VetoExample], bin_count: int) -> dict[str, Any]:
    summary: dict[str, dict[str, dict[str, int | None]]] = {}
    assignments = time_bin_assignments(examples, bin_count)
    for example, (cut, time_bin) in zip(examples, assignments):
        cut_key = str(cut)
        bin_key = str(time_bin)
        label_name = "fallback_better" if example.regret_vs_fallback > 0.0 else "selected_better"
        start_index = example_start_index(example)
        if cut_key not in summary:
            summary[cut_key] = {}
        if bin_key not in summary[cut_key]:
            summary[cut_key][bin_key] = {
                "fallback_better": 0,
                "selected_better": 0,
                "start_index_min": None,
                "start_index_max": None,
            }
        bucket = summary[cut_key][bin_key]
        bucket[label_name] = int(bucket[label_name]) + 1
        current_min = bucket["start_index_min"]
        current_max = bucket["start_index_max"]
        bucket["start_index_min"] = start_index if current_min is None else min(int(current_min), start_index)
        bucket["start_index_max"] = start_index if current_max is None else max(int(current_max), start_index)
    return {
        cut: dict(sorted(bins.items(), key=lambda item: int(item[0])))
        for cut, bins in sorted(summary.items(), key=lambda item: int(item[0]))
    }


def balanced_sample_weights(labels: np.ndarray) -> np.ndarray:
    positive_rate = float(labels.mean())
    if positive_rate <= 0.0 or positive_rate >= 1.0:
        return np.ones_like(labels)
    positive_weight = 0.5 / positive_rate
    negative_weight = 0.5 / (1.0 - positive_rate)
    return np.where(labels > 0.5, positive_weight, negative_weight)


def normalized_weights(weights: np.ndarray) -> np.ndarray:
    mean_weight = float(weights.mean())
    if mean_weight <= 0.0:
        return np.ones_like(weights)
    return weights / mean_weight


def false_positive_sample_weights(labels: np.ndarray, false_positive_weight: float) -> np.ndarray:
    balanced_weights = balanced_sample_weights(labels)
    return np.where(labels > 0.5, balanced_weights, balanced_weights * false_positive_weight)


def margin_sample_weights(examples: list[VetoExample], min_weight: float = 0.25, max_weight: float = 4.0) -> np.ndarray:
    margins = np.asarray([abs(example.regret_vs_fallback) for example in examples], dtype=float)
    nonzero_margins = margins[margins > 0.0]
    if len(nonzero_margins) == 0:
        return np.ones_like(margins)
    median_margin = float(np.median(nonzero_margins))
    if median_margin <= 0.0:
        return np.ones_like(margins)
    bounded_weights = np.clip(margins / median_margin, min_weight, max_weight)
    return normalized_weights(bounded_weights)


def cut_label_balanced_sample_weights(examples: list[VetoExample], labels: np.ndarray) -> np.ndarray:
    groups = [(int(example.row["cut"]),) for example in examples]
    return group_label_balanced_sample_weights(groups, labels)


def time_bin_label_balanced_sample_weights(examples: list[VetoExample], labels: np.ndarray, bin_count: int) -> np.ndarray:
    return group_label_balanced_sample_weights(time_bin_assignments(examples, bin_count), labels)


def group_label_balanced_sample_weights(groups: list[tuple[int, ...]], labels: np.ndarray) -> np.ndarray:
    weights = np.zeros_like(labels)
    unique_groups = sorted(set(groups))
    if not unique_groups:
        return np.ones_like(labels)
    group_mass = 1.0 / len(unique_groups)
    for group in unique_groups:
        group_indices = [index for index, candidate_group in enumerate(groups) if candidate_group == group]
        positive_indices = [index for index in group_indices if labels[index] > 0.5]
        negative_indices = [index for index in group_indices if labels[index] <= 0.5]
        if positive_indices and negative_indices:
            positive_mass = group_mass * 0.5
            negative_mass = group_mass * 0.5
        elif positive_indices:
            positive_mass = group_mass
            negative_mass = 0.0
        else:
            positive_mass = 0.0
            negative_mass = group_mass
        for index in positive_indices:
            weights[index] = positive_mass / len(positive_indices)
        for index in negative_indices:
            weights[index] = negative_mass / len(negative_indices)
        if group_indices and weights[group_indices].sum() == 0.0:
            weights[group_indices] = group_mass / len(group_indices)
    return normalized_weights(weights)


def sample_weights_for_examples(
    examples: list[VetoExample], labels: np.ndarray, config: LogisticVetoConfig
) -> np.ndarray:
    margin_weights = margin_sample_weights(examples)
    if config.training_weighting == "time-bin-margin-balanced":
        balanced_weights = time_bin_label_balanced_sample_weights(examples, labels, config.training_time_bins)
        class_weights = np.where(labels > 0.5, balanced_weights, balanced_weights * config.false_positive_weight)
        return normalized_weights(class_weights * margin_weights)
    if config.training_weighting == "margin-label-balanced":
        class_weights = false_positive_sample_weights(labels, config.false_positive_weight)
        return normalized_weights(class_weights * margin_weights)
    if config.training_weighting == "time-bin-label-balanced":
        balanced_weights = time_bin_label_balanced_sample_weights(examples, labels, config.training_time_bins)
        return np.where(labels > 0.5, balanced_weights, balanced_weights * config.false_positive_weight)
    if config.training_weighting == "cut-label-balanced":
        balanced_weights = cut_label_balanced_sample_weights(examples, labels)
        return np.where(labels > 0.5, balanced_weights, balanced_weights * config.false_positive_weight)
    return false_positive_sample_weights(labels, config.false_positive_weight)


def logistic_loss(probabilities: np.ndarray, labels: np.ndarray, weights: np.ndarray, model_weights: np.ndarray, l2: float) -> float:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    data_loss = -float((weights * (labels * np.log(clipped) + (1.0 - labels) * np.log(1.0 - clipped))).mean())
    return data_loss + 0.5 * l2 * float((model_weights * model_weights).sum())


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    return float(((probabilities - labels) ** 2).mean())


def probability_distribution_summary(probabilities: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    positive_probabilities = probabilities[labels > 0.5]
    negative_probabilities = probabilities[labels <= 0.5]
    return {
        "mean_probability": float(probabilities.mean()) if len(probabilities) else None,
        "positive_mean_probability": float(positive_probabilities.mean()) if len(positive_probabilities) else None,
        "negative_mean_probability": float(negative_probabilities.mean()) if len(negative_probabilities) else None,
        "positive_p50_probability": float(np.quantile(positive_probabilities, 0.5))
        if len(positive_probabilities)
        else None,
        "positive_p75_probability": float(np.quantile(positive_probabilities, 0.75))
        if len(positive_probabilities)
        else None,
        "positive_p90_probability": float(np.quantile(positive_probabilities, 0.9))
        if len(positive_probabilities)
        else None,
        "negative_p90_probability": float(np.quantile(negative_probabilities, 0.9))
        if len(negative_probabilities)
        else None,
    }


def abstention_probability_gate(
    probabilities: np.ndarray, labels: np.ndarray, config: LogisticVetoConfig
) -> float | None:
    if config.abstention_mode == "none":
        return None
    if config.abstention_mode == "positive-quantile":
        positive_probabilities = probabilities[labels > 0.5]
        if len(positive_probabilities) == 0:
            return 1.0
        quantile_gate = float(np.quantile(positive_probabilities, config.positive_probability_quantile))
        return max(config.probability_threshold, quantile_gate)
    raise ValueError(f"unsupported abstention mode: {config.abstention_mode}")


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
    sample_weights = sample_weights_for_examples(examples, labels, config)
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
    abstention_gate = abstention_probability_gate(probabilities, labels, config)
    return LogisticVetoModel(
        config=config,
        frame=frame,
        mean=mean,
        scale=scale,
        weights=model_weights,
        bias=bias,
        abstention_probability_gate=abstention_gate,
        training_examples=len(examples),
        training_positive_rate=float(labels.mean()),
        training_loss=logistic_loss(probabilities, labels, sample_weights, model_weights, config.l2),
        training_brier=brier_score(probabilities, labels),
        training_probability_summary=probability_distribution_summary(probabilities, labels),
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
            "abstention_mode": model.config.abstention_mode,
            "abstention_probability_gate": model.abstention_probability_gate,
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
    benefit_signal_windows = 0
    confidence_abstained_windows = 0
    for local_index, probability in enumerate(probabilities):
        global_index = override_indices[local_index]
        selected_family = selected_families[global_index]
        if float(probability) >= model.config.probability_threshold:
            benefit_signal_windows += 1
            if model.abstention_probability_gate is not None and float(probability) < model.abstention_probability_gate:
                confidence_abstained_windows += 1
                kept_probabilities.append(float(probability))
                continue
            vetoed[global_index] = fallback_family
            vetoed_probabilities.append(float(probability))
            vetoed_by_family[selected_family] = vetoed_by_family.get(selected_family, 0) + 1
        else:
            kept_probabilities.append(float(probability))

    return vetoed, {
        "mode": "logistic_fallback_probability_veto",
        "changed_windows": len(vetoed_probabilities),
        "benefit_signal_windows": benefit_signal_windows,
        "confidence_abstained_windows": confidence_abstained_windows,
        "training_examples": model.training_examples,
        "training_positive_rate": model.training_positive_rate,
        "training_loss": model.training_loss,
        "training_brier": model.training_brier,
        "training_probability_summary": model.training_probability_summary,
        "current_overrides": len(override_indices),
        "probability_threshold": model.config.probability_threshold,
        "abstention_mode": model.config.abstention_mode,
        "positive_probability_quantile": model.config.positive_probability_quantile,
        "abstention_probability_gate": model.abstention_probability_gate,
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
    min_changed_windows: int,
    min_fold_changed_windows: int,
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

    fold_metric_deltas = [metric_delta(report) for report in fold_reports]
    fold_negative_regressions = sum(negative_delta(report) > 0 for report in fold_reports)
    fold_metric_regressions = sum(delta <= 0.0 for delta in fold_metric_deltas)
    fold_changed_windows = [changed_windows(report) for report in fold_reports]
    fold_no_exposure = sum(changed_windows(report) == 0 for report in fold_reports)
    fold_under_min_exposure = sum(changed < min_fold_changed_windows for changed in fold_changed_windows)
    combined_negative_delta = negative_delta(combined_report)
    combined_metric_delta = metric_delta(combined_report)
    combined_changed_windows = changed_windows(combined_report)
    exposure_pass = (
        combined_changed_windows >= min_changed_windows
        and fold_under_min_exposure <= max_fold_no_exposure
    )
    robust_pass = (
        exposure_pass
        and combined_metric_delta > 0.0
        and combined_negative_delta <= 0
        and fold_negative_regressions == 0
    )

    return {
        "config": config_summary(config),
        "combined": combined_report,
        "folds": fold_reports,
        "summary": {
            "combined_metric_delta": combined_metric_delta,
            "combined_negative_series_delta": combined_negative_delta,
            "combined_changed_windows": combined_changed_windows,
            "fold_metric_deltas": fold_metric_deltas,
            "min_fold_metric_delta": min(fold_metric_deltas) if fold_metric_deltas else 0.0,
            "mean_fold_metric_delta": float(sum(fold_metric_deltas) / len(fold_metric_deltas))
            if fold_metric_deltas
            else 0.0,
            "fold_changed_windows": fold_changed_windows,
            "fold_negative_regressions": fold_negative_regressions,
            "fold_metric_regressions": fold_metric_regressions,
            "fold_no_exposure": fold_no_exposure,
            "fold_under_min_exposure": fold_under_min_exposure,
            "max_fold_no_exposure": max_fold_no_exposure,
            "min_validation_changed_windows": min_changed_windows,
            "min_validation_fold_changed_windows": min_fold_changed_windows,
            "exposure_pass": exposure_pass,
            "robust_pass": robust_pass,
        },
    }


def validation_positive(score: dict[str, Any]) -> bool:
    return (
        float(score["summary"]["combined_metric_delta"]) > 0.0
        and int(score["summary"]["combined_negative_series_delta"]) <= 0
        and int(score["summary"]["fold_negative_regressions"]) == 0
        and bool(score["summary"].get("exposure_pass", True))
    )


def strict_validation_positive(score: dict[str, Any]) -> bool:
    return (
        validation_positive(score)
        and int(score["summary"]["fold_metric_regressions"]) == 0
        and int(score["summary"]["fold_no_exposure"]) <= int(score["summary"]["max_fold_no_exposure"])
    )


def ranked_validation_scores(
    scores: list[dict[str, Any]], *, selection_objective: str = "combined"
) -> list[dict[str, Any]]:
    if selection_objective == "worst-fold":
        return sorted(
            scores,
            key=lambda score: (
                strict_validation_positive(score),
                bool(score["summary"]["robust_pass"]),
                float(score["summary"]["combined_metric_delta"]) > 0.0,
                -int(score["summary"]["fold_negative_regressions"]),
                -int(score["summary"]["combined_negative_series_delta"]),
                bool(score["summary"].get("exposure_pass", True)),
                float(score["summary"].get("min_fold_metric_delta", 0.0)),
                float(score["summary"].get("mean_fold_metric_delta", 0.0)),
                -int(score["summary"]["fold_metric_regressions"]),
                float(score["summary"]["combined_metric_delta"]),
                -int(score["summary"].get("fold_under_min_exposure", 0)),
                -int(score["summary"]["fold_no_exposure"]),
                changed_windows(score["combined"]),
            ),
            reverse=True,
        )
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
            bool(score["summary"].get("exposure_pass", True)),
            -int(score["summary"].get("fold_under_min_exposure", 0)),
            -int(score["summary"]["fold_no_exposure"]),
            changed_windows(score["combined"]),
        ),
        reverse=True,
    )


def select_validation_config(
    scores: list[dict[str, Any]], *, selection_gate: str, selection_objective: str
) -> dict[str, Any]:
    strict_passing = [score for score in scores if strict_validation_positive(score)]
    if selection_gate == "strict":
        if not strict_passing:
            return {
                "selection_reason": "strict_gate_no_candidate",
                "strict_gate_pass": False,
            }
        selected = dict(ranked_validation_scores(strict_passing, selection_objective=selection_objective)[0])
        selected["selection_reason"] = "strict_positive"
        selected["strict_gate_pass"] = True
        return selected

    passing = [score for score in scores if bool(score["summary"]["robust_pass"])]
    validation_positive_scores = [score for score in scores if validation_positive(score)]
    pool = passing or validation_positive_scores or scores
    selected = dict(ranked_validation_scores(pool, selection_objective=selection_objective)[0])
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
            false_positive_weight=false_positive_weight,
            training_weighting=training_weighting,
            training_time_bins=args.training_time_bins,
            abstention_mode=abstention_mode,
            positive_probability_quantile=positive_probability_quantile,
            learning_rate=args.learning_rate,
            steps=args.steps,
        )
        for l2 in default_l2_values(args.l2)
        for threshold in default_threshold_values(args.probability_threshold)
        for false_positive_weight in default_false_positive_weights(args.false_positive_weight)
        for training_weighting in default_training_weightings(args.training_weighting)
        for abstention_mode in default_abstention_modes(args.abstention_mode)
        for positive_probability_quantile in default_positive_probability_quantiles(
            args.positive_probability_quantile
        )
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
            min_changed_windows=args.min_validation_changed_windows,
            min_fold_changed_windows=args.min_validation_fold_changed_windows,
        )
        for config in configs
    ]
    selected_validation = select_validation_config(
        validation_scores,
        selection_gate=args.selection_gate,
        selection_objective=args.selection_objective,
    )
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
        verdict = verdict_for_final_with_exposure(final_report, args.min_final_changed_windows)
        final_report["min_final_changed_windows"] = args.min_final_changed_windows
        final_report["final_exposure_pass"] = final_exposure_pass(
            final_report, args.min_final_changed_windows
        )
        final_report["promotion_verdict"] = verdict

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
        "selection_objective": args.selection_objective,
        "initial_discovery_max_cut": args.initial_discovery_max_cut,
        "validation_cuts": validation_cuts,
        "final_holdout_min_cut": args.final_holdout_min_cut,
        "l2_values": default_l2_values(args.l2),
        "probability_thresholds": default_threshold_values(args.probability_threshold),
        "false_positive_weights": default_false_positive_weights(args.false_positive_weight),
        "training_weightings": default_training_weightings(args.training_weighting),
        "training_time_bins": args.training_time_bins,
        "abstention_modes": default_abstention_modes(args.abstention_mode),
        "positive_probability_quantiles": default_positive_probability_quantiles(
            args.positive_probability_quantile
        ),
        "learning_rate": args.learning_rate,
        "steps": args.steps,
        "training_target": (
            "fallback_better_probability_with_false_positive_penalty_optional_temporal_balance_"
            "and_optional_training_positive_quantile_abstention"
        ),
        "min_validation_changed_windows": args.min_validation_changed_windows,
        "min_validation_fold_changed_windows": args.min_validation_fold_changed_windows,
        "min_final_changed_windows": args.min_final_changed_windows,
        "max_validation_fold_no_exposure": args.max_validation_fold_no_exposure,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "discovery_examples": len(discovery_examples),
        "discovery_example_margin_summary": example_margin_summary(discovery_examples),
        "discovery_example_cut_summary": example_cut_label_summary(discovery_examples),
        "discovery_example_time_bin_summary": example_time_bin_label_summary(
            discovery_examples, args.training_time_bins
        ),
        "final_train_examples": len(final_train_examples),
        "final_train_example_margin_summary": example_margin_summary(final_train_examples),
        "final_train_example_cut_summary": example_cut_label_summary(final_train_examples),
        "final_train_example_time_bin_summary": example_time_bin_label_summary(
            final_train_examples, args.training_time_bins
        ),
        "validation_candidate_count": len(validation_scores),
        "validation_robust_pass_count": sum(bool(score["summary"]["robust_pass"]) for score in validation_scores),
        "validation_positive_count": sum(validation_positive(score) for score in validation_scores),
        "validation_strict_positive_count": sum(strict_validation_positive(score) for score in validation_scores),
        "validation_score_summaries": [
            compact_validation_score(score)
            for score in ranked_validation_scores(validation_scores, selection_objective=args.selection_objective)
        ],
        "selected_validation": selected_validation,
        "selected_config": config_summary(selected_config) if selected_config else None,
        "final_holdout_evaluated": final_report is not None,
        "final_holdout": final_report,
        "verdict": verdict,
        "guardrail": (
            "Logistic fallback-veto probabilities are trained on discovery override "
            "examples with optional extra weight on harmful-veto labels and optional "
            "cut- or time-bin-balanced discovery sample weights. Optional abstention "
            "gates are calibrated from training-split positive probabilities only. "
            "Candidates are selected on chronological validation folds, and strict "
            "mode fails closed before final holdout when no candidate avoids fold "
            "metric/downside regressions or the minimum validation exposure gate. "
            "Final holdout promotion also requires the configured minimum final "
            "exposure. Robust diagnostics can rank by combined lift or worst-fold "
            "validation utility."
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
        "selection_objective": report["selection_objective"],
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
        "min_final_changed_windows": report["min_final_changed_windows"],
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
                "final_exposure_pass": final_holdout["final_exposure_pass"],
                "final_promotion_verdict": final_holdout["promotion_verdict"],
            }
        )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
