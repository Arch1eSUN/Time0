from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


MetricName = str


@dataclass(frozen=True)
class CandidateConfig:
    name: str
    kind: str
    family: str | None = None
    k: int | None = None
    include_series: bool = False


@dataclass(frozen=True)
class FeatureFrame:
    matrix: np.ndarray
    names: list[str]
    series_ids: list[str]
    mean: np.ndarray
    std: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="reports/router-rows-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument(
        "--output",
        default="reports/no-leak-prediction-router-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--cold-start-family", default="recent2000")
    parser.add_argument("--fallback-family", default="recent2000")
    parser.add_argument("--min-validation-lift", type=float, default=0.01)
    parser.add_argument("--softmax-steps", type=int, default=2000)
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return experiment_root() / raw_path


def load_router_rows(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text())
    if report.get("method") != "prediction_archive_router_rows":
        raise ValueError(f"{path} is not a prediction archive router-row report")
    if int(report["rows"]) != len(report["data"]):
        raise ValueError(f"{path} rows={report['rows']} but data has {len(report['data'])}")
    return report


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)


def improvement(reference: float, candidate: float) -> float:
    return (reference - candidate) / reference


def rows_by_cut(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["cut"]), []).append(row)
    return {cut: grouped[cut] for cut in sorted(grouped)}


def flatten_runtime_features(
    row: dict[str, Any],
    *,
    families: list[str],
    series_ids: list[str],
    include_series: bool,
) -> tuple[list[float], list[str]]:
    runtime_features = row["runtime_features"]
    values: list[float] = []
    names: list[str] = []

    for group_name in ("context", "prediction_disagreement"):
        group = runtime_features[group_name]
        for key in sorted(group):
            names.append(f"{group_name}.{key}")
            values.append(float(group[key]))

    prediction_summaries = runtime_features["prediction_summaries"]
    for family in families:
        summary = prediction_summaries[family]
        for key in sorted(summary):
            names.append(f"prediction_summaries.{family}.{key}")
            values.append(float(summary[key]))

    if include_series:
        series_id = row["series_id"]
        for known_series_id in series_ids:
            names.append(f"series_id.{known_series_id}")
            values.append(1.0 if series_id == known_series_id else 0.0)

    return values, names


def build_feature_frame(
    rows: list[dict[str, Any]],
    *,
    families: list[str],
    series_ids: list[str],
    include_series: bool,
    reference: FeatureFrame | None = None,
) -> FeatureFrame:
    raw_rows: list[list[float]] = []
    names: list[str] | None = None
    for row in rows:
        values, feature_names = flatten_runtime_features(
            row,
            families=families,
            series_ids=series_ids,
            include_series=include_series,
        )
        if names is None:
            names = feature_names
        elif names != feature_names:
            raise ValueError("feature names changed across rows")
        raw_rows.append(values)

    matrix = np.array(raw_rows, dtype=float)
    if reference is None:
        feature_mean = matrix.mean(axis=0)
        feature_std = matrix.std(axis=0)
        feature_std[feature_std < 1e-9] = 1.0
    else:
        feature_mean = reference.mean
        feature_std = reference.std

    return FeatureFrame(
        matrix=(matrix - feature_mean) / feature_std,
        names=names or [],
        series_ids=series_ids,
        mean=feature_mean,
        std=feature_std,
    )


def family_error(row: dict[str, Any], family: str, metric: MetricName) -> float:
    return float(row["label"]["family_errors"][family][metric])


def selection_metrics(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    families: list[str],
    metric: MetricName,
) -> dict[str, Any]:
    if len(rows) != len(selected_families):
        raise ValueError("row and selection lengths differ")

    selected_mae = [family_error(row, family, "mae") for row, family in zip(rows, selected_families)]
    selected_smape = [family_error(row, family, "smape") for row, family in zip(rows, selected_families)]
    zero_mae = [family_error(row, "zero-shot", "mae") for row in rows]
    zero_smape = [family_error(row, "zero-shot", "smape") for row in rows]
    oracle_mae = [float(row["label"]["best_mae"]) for row in rows]
    oracle_smape = [
        family_error(row, row["label"]["best_family_by_mae"], "smape") for row in rows
    ]

    family_mean_mae = {
        family: mean([family_error(row, family, "mae") for row in rows]) for family in families
    }
    family_mean_smape = {
        family: mean([family_error(row, family, "smape") for row in rows]) for family in families
    }

    selected_metric = selected_mae if metric == "mae" else selected_smape
    zero_metric = zero_mae if metric == "mae" else zero_smape

    return {
        "windows": len(rows),
        "selected_counts": dict(sorted(Counter(selected_families).items())),
        "selected_mae": mean(selected_mae),
        "selected_mae_improvement_vs_zero_shot": improvement(mean(zero_mae), mean(selected_mae)),
        "selected_smape": mean(selected_smape),
        "selected_smape_improvement_vs_zero_shot": improvement(mean(zero_smape), mean(selected_smape)),
        "selection_metric": metric,
        "selected_metric": mean(selected_metric),
        "selected_metric_improvement_vs_zero_shot": improvement(mean(zero_metric), mean(selected_metric)),
        "zero_shot_mae": mean(zero_mae),
        "zero_shot_smape": mean(zero_smape),
        "family_mean_mae": family_mean_mae,
        "family_mean_smape": family_mean_smape,
        "best_fixed_family_by_mae": min(families, key=lambda family: family_mean_mae[family]),
        "best_fixed_family_by_smape": min(families, key=lambda family: family_mean_smape[family]),
        "leaky_oracle_per_window_mae": mean(oracle_mae),
        "leaky_oracle_per_window_mae_improvement_vs_zero_shot": improvement(mean(zero_mae), mean(oracle_mae)),
        "leaky_oracle_per_window_smape": mean(oracle_smape),
        "leaky_oracle_per_window_smape_improvement_vs_zero_shot": improvement(
            mean(zero_smape), mean(oracle_smape)
        ),
    }


def fixed_selection(rows: list[dict[str, Any]], family: str) -> list[str]:
    return [family for _row in rows]


def labels_for(rows: list[dict[str, Any]], families: list[str]) -> np.ndarray:
    return np.array([families.index(row["label"]["best_family_by_mae"]) for row in rows], dtype=int)


def fit_softmax(
    train_rows: list[dict[str, Any]],
    *,
    families: list[str],
    include_series: bool,
    steps: int,
) -> tuple[FeatureFrame, np.ndarray]:
    series_ids = sorted({str(row["series_id"]) for row in train_rows}) if include_series else []
    frame = build_feature_frame(
        train_rows,
        families=families,
        series_ids=series_ids,
        include_series=include_series,
    )
    design = np.c_[frame.matrix, np.ones(frame.matrix.shape[0])]
    labels = labels_for(train_rows, families)
    weights = np.zeros((design.shape[1], len(families)), dtype=float)
    learning_rate = 0.2
    l2 = 1e-3

    for _step in range(steps):
        logits = design @ weights
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        gradient = probabilities
        gradient[np.arange(labels.shape[0]), labels] -= 1.0
        gradient /= labels.shape[0]
        weight_gradient = design.T @ gradient + l2 * weights
        weight_gradient[-1] -= l2 * weights[-1]
        weights -= learning_rate * weight_gradient

    return frame, weights


def predict_softmax(
    model: tuple[FeatureFrame, np.ndarray],
    eval_rows: list[dict[str, Any]],
    *,
    families: list[str],
) -> list[str]:
    frame, weights = model
    eval_frame = build_feature_frame(
        eval_rows,
        families=families,
        series_ids=frame.series_ids,
        include_series=bool(frame.series_ids),
        reference=frame,
    )
    design = np.c_[eval_frame.matrix, np.ones(eval_frame.matrix.shape[0])]
    labels = (design @ weights).argmax(axis=1)
    return [families[int(label)] for label in labels]


def predict_knn_regret(
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    families: list[str],
    k: int,
    include_series: bool,
    metric: MetricName,
) -> list[str]:
    series_ids = sorted({str(row["series_id"]) for row in train_rows}) if include_series else []
    train_frame = build_feature_frame(
        train_rows,
        families=families,
        series_ids=series_ids,
        include_series=include_series,
    )
    eval_frame = build_feature_frame(
        eval_rows,
        families=families,
        series_ids=series_ids,
        include_series=include_series,
        reference=train_frame,
    )
    train_errors = np.array(
        [[family_error(row, family, metric) for family in families] for row in train_rows],
        dtype=float,
    )
    selected: list[str] = []
    neighbor_count = min(k, len(train_rows))
    for row_features in eval_frame.matrix:
        distances = ((train_frame.matrix - row_features) ** 2).sum(axis=1)
        indices = np.argpartition(distances, neighbor_count - 1)[:neighbor_count]
        scores = train_errors[indices].mean(axis=0)
        selected.append(families[int(scores.argmin())])
    return selected


def select_candidate(
    config: CandidateConfig,
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    families: list[str],
    metric: MetricName,
    softmax_steps: int,
) -> list[str]:
    if config.kind == "fixed":
        if config.family is None:
            raise ValueError(f"{config.name} is missing family")
        return fixed_selection(eval_rows, config.family)
    if config.kind == "softmax":
        model = fit_softmax(
            train_rows,
            families=families,
            include_series=config.include_series,
            steps=softmax_steps,
        )
        return predict_softmax(model, eval_rows, families=families)
    if config.kind == "knn_regret":
        if config.k is None:
            raise ValueError(f"{config.name} is missing k")
        return predict_knn_regret(
            train_rows,
            eval_rows,
            families=families,
            k=config.k,
            include_series=config.include_series,
            metric=metric,
        )
    raise ValueError(f"unsupported candidate kind: {config.kind}")


def aggregate_cut_reports(cut_reports: list[dict[str, Any]], metric: MetricName) -> dict[str, Any]:
    selected: list[str] = []
    rows: list[dict[str, Any]] = []
    families = list(cut_reports[0]["families"])
    for cut_report in cut_reports:
        selected.extend(cut_report["selected_families"])
        rows.extend(cut_report["rows"])
    return selection_metrics(rows=rows, selected_families=selected, families=families, metric=metric)


def chronological_candidate_report(
    *,
    config: CandidateConfig,
    cut_rows: dict[int, list[dict[str, Any]]],
    cuts: list[int],
    families: list[str],
    metric: MetricName,
    cold_start_family: str,
    softmax_steps: int,
) -> dict[str, Any]:
    per_cut: list[dict[str, Any]] = []
    for cut in cuts:
        prior_cuts = [prior for prior in cuts if prior < cut]
        eval_rows = cut_rows[cut]
        if not prior_cuts:
            selected = fixed_selection(eval_rows, cold_start_family)
            decision = {
                "mode": "cold_start",
                "selected_config": f"fixed:{cold_start_family}",
                "prior_cuts": prior_cuts,
            }
        else:
            train_rows = [row for prior in prior_cuts for row in cut_rows[prior]]
            selected = select_candidate(
                config,
                train_rows,
                eval_rows,
                families=families,
                metric=metric,
                softmax_steps=softmax_steps,
            )
            decision = {
                "mode": "chronological_train_prior_cuts",
                "selected_config": config.name,
                "prior_cuts": prior_cuts,
            }
        metrics = selection_metrics(rows=eval_rows, selected_families=selected, families=families, metric=metric)
        per_cut.append(
            {
                "cut": cut,
                "families": families,
                "rows": eval_rows,
                "selected_families": selected,
                "decision": decision,
                "metrics": metrics,
            }
        )

    routed = [cut for cut in per_cut if cut["decision"]["mode"] != "cold_start"]
    return {
        "config": config.__dict__,
        "per_cut": strip_private_rows(per_cut),
        "all_cuts": aggregate_cut_reports(per_cut, metric),
        "routed_cuts_only": aggregate_cut_reports(routed, metric) if routed else None,
    }


def validate_candidate_on_cut(
    *,
    config: CandidateConfig,
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    families: list[str],
    metric: MetricName,
    softmax_steps: int,
) -> dict[str, Any]:
    selected = select_candidate(
        config,
        train_rows,
        validation_rows,
        families=families,
        metric=metric,
        softmax_steps=softmax_steps,
    )
    metrics = selection_metrics(
        rows=validation_rows,
        selected_families=selected,
        families=families,
        metric=metric,
    )
    return {
        "config": config.__dict__,
        "metrics": metrics,
    }


def validation_gated_report(
    *,
    learned_configs: list[CandidateConfig],
    cut_rows: dict[int, list[dict[str, Any]]],
    cuts: list[int],
    families: list[str],
    metric: MetricName,
    cold_start_family: str,
    fallback_family: str,
    min_validation_lift: float,
    softmax_steps: int,
) -> dict[str, Any]:
    per_cut: list[dict[str, Any]] = []
    fallback_config = CandidateConfig(name=f"fixed:{fallback_family}", kind="fixed", family=fallback_family)

    for cut in cuts:
        prior_cuts = [prior for prior in cuts if prior < cut]
        eval_rows = cut_rows[cut]
        if not prior_cuts:
            selected = fixed_selection(eval_rows, cold_start_family)
            decision = {
                "mode": "cold_start",
                "selected_config": f"fixed:{cold_start_family}",
                "prior_cuts": prior_cuts,
            }
        elif len(prior_cuts) == 1:
            selected = fixed_selection(eval_rows, fallback_family)
            decision = {
                "mode": "fallback_no_validation_cut",
                "selected_config": fallback_config.name,
                "prior_cuts": prior_cuts,
            }
        else:
            train_cuts = prior_cuts[:-1]
            validation_cut = prior_cuts[-1]
            train_rows = [row for train_cut in train_cuts for row in cut_rows[train_cut]]
            validation_rows = cut_rows[validation_cut]
            fallback_validation = validate_candidate_on_cut(
                config=fallback_config,
                train_rows=train_rows,
                validation_rows=validation_rows,
                families=families,
                metric=metric,
                softmax_steps=softmax_steps,
            )
            learned_validation = [
                validate_candidate_on_cut(
                    config=config,
                    train_rows=train_rows,
                    validation_rows=validation_rows,
                    families=families,
                    metric=metric,
                    softmax_steps=softmax_steps,
                )
                for config in learned_configs
            ]
            best_learned = min(
                learned_validation,
                key=lambda item: float(item["metrics"]["selected_metric"]),
            )
            fallback_metric = float(fallback_validation["metrics"]["selected_metric"])
            best_learned_metric = float(best_learned["metrics"]["selected_metric"])
            required_metric = fallback_metric * (1.0 - min_validation_lift)
            should_route = best_learned_metric <= required_metric
            selected_config = (
                CandidateConfig(**best_learned["config"]) if should_route else fallback_config
            )
            all_prior_rows = [row for prior in prior_cuts for row in cut_rows[prior]]
            selected = select_candidate(
                selected_config,
                all_prior_rows,
                eval_rows,
                families=families,
                metric=metric,
                softmax_steps=softmax_steps,
            )
            decision = {
                "mode": "validation_gated",
                "prior_cuts": prior_cuts,
                "train_cuts_for_validation": train_cuts,
                "validation_cut": validation_cut,
                "fallback_config": fallback_config.name,
                "fallback_validation_metric": fallback_metric,
                "best_learned_config": best_learned["config"]["name"],
                "best_learned_validation_metric": best_learned_metric,
                "required_metric_to_switch": required_metric,
                "min_validation_lift": min_validation_lift,
                "selected_config": selected_config.name,
                "learned_validation": learned_validation,
            }

        metrics = selection_metrics(rows=eval_rows, selected_families=selected, families=families, metric=metric)
        per_cut.append(
            {
                "cut": cut,
                "families": families,
                "rows": eval_rows,
                "selected_families": selected,
                "decision": decision,
                "metrics": metrics,
            }
        )

    routed = [cut for cut in per_cut if cut["decision"]["mode"] != "cold_start"]
    return {
        "policy": "validation_gated_prediction_router",
        "guardrail": (
            "A learned router is used only when it beats the fallback family on "
            "the latest prior validation cut by min_validation_lift."
        ),
        "per_cut": strip_private_rows(per_cut),
        "all_cuts": aggregate_cut_reports(per_cut, metric),
        "routed_cuts_only": aggregate_cut_reports(routed, metric) if routed else None,
    }


def fixed_family_reports(
    *,
    cut_rows: dict[int, list[dict[str, Any]]],
    cuts: list[int],
    families: list[str],
    metric: MetricName,
) -> dict[str, Any]:
    all_rows = [row for cut in cuts for row in cut_rows[cut]]
    routed_rows = [row for cut in cuts[1:] for row in cut_rows[cut]]
    return {
        family: {
            "all_cuts": selection_metrics(
                rows=all_rows,
                selected_families=fixed_selection(all_rows, family),
                families=families,
                metric=metric,
            ),
            "routed_cuts_only": selection_metrics(
                rows=routed_rows,
                selected_families=fixed_selection(routed_rows, family),
                families=families,
                metric=metric,
            ),
        }
        for family in families
    }


def strip_private_rows(cut_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for report in cut_reports:
        public.append(
            {
                "cut": report["cut"],
                "decision": report["decision"],
                "metrics": report["metrics"],
            }
        )
    return public


def learned_candidate_configs() -> list[CandidateConfig]:
    configs = [
        CandidateConfig(name="softmax", kind="softmax", include_series=False),
        CandidateConfig(name="softmax_series", kind="softmax", include_series=True),
    ]
    for include_series in (False, True):
        suffix = "series" if include_series else "no_series"
        for k in (25, 50, 100):
            configs.append(
                CandidateConfig(
                    name=f"knn_regret_{suffix}_k{k}",
                    kind="knn_regret",
                    k=k,
                    include_series=include_series,
                )
            )
    return configs


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = experiment_path(args.input)
    source = load_router_rows(input_path)
    rows = list(source["data"])
    cuts = [int(cut) for cut in source["cuts"]]
    families = list(source["families"])
    if args.cold_start_family not in families:
        raise ValueError(f"unknown cold-start family: {args.cold_start_family}")
    if args.fallback_family not in families:
        raise ValueError(f"unknown fallback family: {args.fallback_family}")

    cut_rows = rows_by_cut(rows)
    configs = learned_candidate_configs()
    chronological_diagnostics = {
        config.name: chronological_candidate_report(
            config=config,
            cut_rows=cut_rows,
            cuts=cuts,
            families=families,
            metric=args.metric,
            cold_start_family=args.cold_start_family,
            softmax_steps=args.softmax_steps,
        )
        for config in configs
    }
    gated = validation_gated_report(
        learned_configs=configs,
        cut_rows=cut_rows,
        cuts=cuts,
        families=families,
        metric=args.metric,
        cold_start_family=args.cold_start_family,
        fallback_family=args.fallback_family,
        min_validation_lift=args.min_validation_lift,
        softmax_steps=args.softmax_steps,
    )

    best_diagnostic = min(
        chronological_diagnostics.values(),
        key=lambda item: float(item["routed_cuts_only"]["selected_metric"]),
    )
    fixed = fixed_family_reports(cut_rows=cut_rows, cuts=cuts, families=families, metric=args.metric)
    fallback_metric = fixed[args.fallback_family]["routed_cuts_only"]["selected_metric"]
    gated_metric = gated["routed_cuts_only"]["selected_metric"]

    return {
        "method": "no_leak_prediction_level_router",
        "input": str(input_path),
        "selection_metric": args.metric,
        "cold_start_family": args.cold_start_family,
        "fallback_family": args.fallback_family,
        "min_validation_lift": args.min_validation_lift,
        "cuts": cuts,
        "families": families,
        "rows": len(rows),
        "guardrail": (
            "Router policies train only on prior cuts. Runtime features are read "
            "from joined router rows; actuals/errors are used only for offline "
            "training labels and final evaluation."
        ),
        "fixed_family_baselines": fixed,
        "policies": {
            "validation_gated": gated,
            "chronological_diagnostics": chronological_diagnostics,
        },
        "summary": {
            "best_chronological_diagnostic": best_diagnostic["config"]["name"],
            "best_chronological_diagnostic_routed_metric": best_diagnostic["routed_cuts_only"][
                "selected_metric"
            ],
            "best_chronological_diagnostic_routed_improvement_vs_zero_shot": best_diagnostic[
                "routed_cuts_only"
            ]["selected_metric_improvement_vs_zero_shot"],
            "fallback_family_routed_metric": fallback_metric,
            "fallback_family_routed_improvement_vs_zero_shot": fixed[args.fallback_family][
                "routed_cuts_only"
            ]["selected_metric_improvement_vs_zero_shot"],
            "validation_gated_routed_metric": gated_metric,
            "validation_gated_routed_improvement_vs_zero_shot": gated["routed_cuts_only"][
                "selected_metric_improvement_vs_zero_shot"
            ],
            "validation_gated_delta_vs_fallback_metric": fallback_metric - gated_metric,
            "verdict": (
                "No learned prediction-level router is promotion-ready. The "
                "validation-gated policy keeps the fallback when learned routing "
                "does not clear the prior-cut validation lift requirement."
            ),
        },
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
                "rows": report["rows"],
                "summary": report["summary"],
                "validation_gated_per_cut": report["policies"]["validation_gated"]["per_cut"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
