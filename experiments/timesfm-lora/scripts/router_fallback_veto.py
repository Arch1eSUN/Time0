from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from evaluate_prediction_router import FeatureFrame, build_feature_frame, family_error


MetricName = str


@dataclass(frozen=True)
class VetoExample:
    row: dict[str, Any]
    selected_family: str
    regret_vs_fallback: float


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)


def historical_veto_examples(
    *,
    prior_cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    base_selections: dict[int, dict[str, Any]],
    fallback_family: str,
    metric: MetricName,
) -> list[VetoExample]:
    examples: list[VetoExample] = []
    for cut in prior_cuts:
        selected_families = base_selections[cut]["selected_families"]
        for row, selected_family in zip(cut_rows[cut], selected_families):
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


def selected_family_matrix(selected_families: list[str], families: list[str]) -> np.ndarray:
    matrix = np.zeros((len(selected_families), len(families)), dtype=float)
    family_index = {family: index for index, family in enumerate(families)}
    for row_index, selected_family in enumerate(selected_families):
        matrix[row_index, family_index[selected_family]] = 1.0
    return matrix


def build_veto_matrix(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    families: list[str],
    include_series: bool,
    reference: FeatureFrame | None = None,
) -> tuple[FeatureFrame, np.ndarray]:
    if reference is None:
        series_ids = sorted({str(row["series_id"]) for row in rows}) if include_series else []
    else:
        series_ids = reference.series_ids
    frame = build_feature_frame(
        rows,
        families=families,
        series_ids=series_ids,
        include_series=include_series,
        reference=reference,
    )
    family_matrix = selected_family_matrix(selected_families, families)
    return frame, np.c_[frame.matrix, family_matrix]


def apply_neighbor_regret_veto(
    *,
    eval_rows: list[dict[str, Any]],
    selected_families: list[str],
    examples: list[VetoExample],
    families: list[str],
    fallback_family: str,
    include_series: bool,
    k: int,
    regret_threshold: float,
) -> tuple[list[str], dict[str, Any]]:
    if not examples:
        return selected_families, {
            "mode": "no_historical_override_examples",
            "historical_examples": 0,
            "vetoed_windows": 0,
        }

    train_rows = [example.row for example in examples]
    train_families = [example.selected_family for example in examples]
    train_regrets = np.array([example.regret_vs_fallback for example in examples], dtype=float)
    train_frame, train_matrix = build_veto_matrix(
        rows=train_rows,
        selected_families=train_families,
        families=families,
        include_series=include_series,
    )
    neighbor_count = min(k, len(examples))

    override_indices = [
        index for index, selected_family in enumerate(selected_families) if selected_family != fallback_family
    ]
    if not override_indices:
        return selected_families, {
            "mode": "no_current_overrides",
            "historical_examples": len(examples),
            "vetoed_windows": 0,
        }

    override_rows = [eval_rows[index] for index in override_indices]
    override_families = [selected_families[index] for index in override_indices]
    _eval_frame, eval_matrix = build_veto_matrix(
        rows=override_rows,
        selected_families=override_families,
        families=families,
        include_series=include_series,
        reference=train_frame,
    )

    vetoed = list(selected_families)
    risk_scores: list[float] = []
    harm_rates: list[float] = []
    vetoed_scores: list[float] = []
    kept_scores: list[float] = []
    for local_index, row_features in enumerate(eval_matrix):
        distances = ((train_matrix - row_features) ** 2).sum(axis=1)
        indices = np.argpartition(distances, neighbor_count - 1)[:neighbor_count]
        neighbor_regrets = train_regrets[indices]
        mean_regret = float(neighbor_regrets.mean())
        harm_rate = float((neighbor_regrets > 0.0).mean())
        risk_scores.append(mean_regret)
        harm_rates.append(harm_rate)
        global_index = override_indices[local_index]
        if mean_regret > regret_threshold:
            vetoed[global_index] = fallback_family
            vetoed_scores.append(mean_regret)
        else:
            kept_scores.append(mean_regret)

    return vetoed, {
        "mode": "neighbor_regret_veto",
        "historical_examples": len(examples),
        "current_overrides": len(override_indices),
        "neighbor_count": neighbor_count,
        "regret_threshold": regret_threshold,
        "vetoed_windows": len(vetoed_scores),
        "mean_neighbor_regret": mean(risk_scores),
        "mean_neighbor_harm_rate": mean(harm_rates),
        "mean_vetoed_neighbor_regret": mean(vetoed_scores) if vetoed_scores else None,
        "mean_kept_neighbor_regret": mean(kept_scores) if kept_scores else None,
    }
