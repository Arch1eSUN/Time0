from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evaluate_prediction_router import (
    CandidateConfig,
    MetricName,
    family_error,
    fixed_selection,
    improvement,
    learned_candidate_configs,
    load_router_rows,
    rows_by_cut,
    select_candidate,
    validate_candidate_on_cut,
)
from router_fallback_veto import apply_neighbor_regret_veto, historical_veto_examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="reports/router-rows-expanded-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument(
        "--output",
        default="reports/router-attribution-expanded-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument(
        "--policy",
        choices=[
            "validation_gated",
            "series_guarded",
            "series_multicut_guarded",
            "series_multicut_worst_guarded",
            "series_risk_penalized",
            "fallback_veto",
        ],
        default="validation_gated",
    )
    parser.add_argument("--cold-start-family", default="recent2000")
    parser.add_argument("--fallback-family", default="recent2000")
    parser.add_argument("--min-validation-lift", type=float, default=0.01)
    parser.add_argument("--min-series-validation-lift", type=float, default=0.0)
    parser.add_argument("--series-risk-decay", type=float, default=0.1)
    parser.add_argument("--veto-k", type=int, default=50)
    parser.add_argument("--veto-regret-threshold", type=float, default=0.0002)
    parser.add_argument("--veto-feature-mode", choices=["global", "series"], default="global")
    parser.add_argument("--softmax-steps", type=int, default=2000)
    parser.add_argument(
        "--candidate-set",
        choices=["baseline", "loss-aware", "knn-regret"],
        default="baseline",
    )
    return parser.parse_args()


def experiment_root() -> Path:
    return Path(__file__).resolve().parents[1]


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return experiment_root() / raw_path


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)


def metric_mean(rows: list[dict[str, Any]], selected_families: list[str], metric: MetricName) -> float:
    if len(rows) != len(selected_families):
        raise ValueError("row and selection lengths differ")
    return mean([family_error(row, family, metric) for row, family in zip(rows, selected_families)])


def series_validation_gate(
    *,
    validation_rows: list[dict[str, Any]],
    candidate_selected: list[str],
    fallback_family: str,
    metric: MetricName,
    min_series_validation_lift: float,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for row, selected_family in zip(validation_rows, candidate_selected):
        grouped[str(row["series_id"])].append((row, selected_family))

    gate: dict[str, dict[str, Any]] = {}
    for series_id, pairs in sorted(grouped.items()):
        rows = [row for row, _selected_family in pairs]
        selected = [selected_family for _row, selected_family in pairs]
        fallback = [fallback_family for _row in rows]
        candidate_metric = metric_mean(rows, selected, metric)
        fallback_metric = metric_mean(rows, fallback, metric)
        required_metric = fallback_metric * (1.0 - min_series_validation_lift)
        allowed = candidate_metric <= required_metric
        gate[series_id] = {
            "validation_windows": len(rows),
            "candidate_metric": candidate_metric,
            "fallback_metric": fallback_metric,
            "required_metric_to_allow": required_metric,
            "min_series_validation_lift": min_series_validation_lift,
            "allowed": allowed,
            "selected_counts": dict(sorted(Counter(selected).items())),
        }
    return gate


def multicut_series_validation_gate(
    *,
    selected_config: CandidateConfig,
    prior_cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    min_series_validation_lift: float,
    softmax_steps: int,
    require_each_cut: bool,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    validation_rows: list[dict[str, Any]] = []
    validation_selected: list[str] = []
    validation_reports: list[dict[str, Any]] = []
    per_cut_gates: list[tuple[int, dict[str, dict[str, Any]]]] = []

    for validation_index in range(1, len(prior_cuts)):
        validation_cut = prior_cuts[validation_index]
        train_cuts = prior_cuts[:validation_index]
        train_rows = [row for train_cut in train_cuts for row in cut_rows[train_cut]]
        current_validation_rows = cut_rows[validation_cut]
        current_selected = select_candidate(
            selected_config,
            train_rows,
            current_validation_rows,
            families=families,
            metric=metric,
            softmax_steps=softmax_steps,
        )
        current_gate = series_validation_gate(
            validation_rows=current_validation_rows,
            candidate_selected=current_selected,
            fallback_family=fallback_family,
            metric=metric,
            min_series_validation_lift=min_series_validation_lift,
        )
        per_cut_gates.append((validation_cut, current_gate))
        validation_rows.extend(current_validation_rows)
        validation_selected.extend(current_selected)
        validation_reports.append(
            {
                "validation_cut": validation_cut,
                "train_cuts": train_cuts,
                "selected_counts": dict(sorted(Counter(current_selected).items())),
                "candidate_metric": metric_mean(current_validation_rows, current_selected, metric),
                "fallback_metric": metric_mean(
                    current_validation_rows,
                    fixed_selection(current_validation_rows, fallback_family),
                    metric,
                ),
                "allowed_series": [
                    series_id for series_id, item in current_gate.items() if item["allowed"]
                ],
                "blocked_series": [
                    series_id for series_id, item in current_gate.items() if not item["allowed"]
                ],
            }
        )

    gate = series_validation_gate(
        validation_rows=validation_rows,
        candidate_selected=validation_selected,
        fallback_family=fallback_family,
        metric=metric,
        min_series_validation_lift=min_series_validation_lift,
    )
    if require_each_cut:
        for series_id, item in gate.items():
            failing_cuts = [
                validation_cut
                for validation_cut, cut_gate in per_cut_gates
                if not cut_gate[series_id]["allowed"]
            ]
            item["aggregate_allowed"] = item["allowed"]
            item["failing_validation_cuts"] = failing_cuts
            item["allowed"] = item["allowed"] and not failing_cuts
    return gate, validation_reports


def recency_weighted_series_risk_gate(
    *,
    selected_config: CandidateConfig,
    prior_cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
    min_series_validation_lift: float,
    series_risk_decay: float,
    softmax_steps: int,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not 0.0 < series_risk_decay <= 1.0:
        raise ValueError("--series-risk-decay must be in (0, 1]")

    per_cut_gates: list[tuple[int, dict[str, dict[str, Any]]]] = []
    validation_reports: list[dict[str, Any]] = []

    for validation_index in range(1, len(prior_cuts)):
        validation_cut = prior_cuts[validation_index]
        train_cuts = prior_cuts[:validation_index]
        train_rows = [row for train_cut in train_cuts for row in cut_rows[train_cut]]
        current_validation_rows = cut_rows[validation_cut]
        current_selected = select_candidate(
            selected_config,
            train_rows,
            current_validation_rows,
            families=families,
            metric=metric,
            softmax_steps=softmax_steps,
        )
        current_gate = series_validation_gate(
            validation_rows=current_validation_rows,
            candidate_selected=current_selected,
            fallback_family=fallback_family,
            metric=metric,
            min_series_validation_lift=min_series_validation_lift,
        )
        per_cut_gates.append((validation_cut, current_gate))
        validation_reports.append(
            {
                "validation_cut": validation_cut,
                "train_cuts": train_cuts,
                "selected_counts": dict(sorted(Counter(current_selected).items())),
                "candidate_metric": metric_mean(current_validation_rows, current_selected, metric),
                "fallback_metric": metric_mean(
                    current_validation_rows,
                    fixed_selection(current_validation_rows, fallback_family),
                    metric,
                ),
                "allowed_series": [
                    series_id for series_id, item in current_gate.items() if item["allowed"]
                ],
                "blocked_series": [
                    series_id for series_id, item in current_gate.items() if not item["allowed"]
                ],
            }
        )

    gate: dict[str, dict[str, Any]] = {}
    if not per_cut_gates:
        return gate, validation_reports

    validation_count = len(per_cut_gates)
    for series_id in sorted(per_cut_gates[0][1]):
        weighted_candidate_metric = 0.0
        weighted_fallback_metric = 0.0
        weighted_relative_lift = 0.0
        total_weight = 0.0
        cut_details: list[dict[str, Any]] = []

        for cut_index, (validation_cut, cut_gate) in enumerate(per_cut_gates):
            weight = series_risk_decay ** (validation_count - 1 - cut_index)
            item = cut_gate[series_id]
            candidate_metric = float(item["candidate_metric"])
            fallback_metric = float(item["fallback_metric"])
            relative_lift = improvement(fallback_metric, candidate_metric)
            weighted_candidate_metric += weight * candidate_metric
            weighted_fallback_metric += weight * fallback_metric
            weighted_relative_lift += weight * relative_lift
            total_weight += weight
            cut_details.append(
                {
                    "validation_cut": validation_cut,
                    "weight": weight,
                    "candidate_metric": candidate_metric,
                    "fallback_metric": fallback_metric,
                    "relative_lift": relative_lift,
                    "allowed": item["allowed"],
                    "selected_counts": item["selected_counts"],
                }
            )

        weighted_candidate_metric /= total_weight
        weighted_fallback_metric /= total_weight
        weighted_mean_relative_lift = weighted_relative_lift / total_weight
        weighted_metric_lift = improvement(weighted_fallback_metric, weighted_candidate_metric)
        latest_relative_lift = cut_details[-1]["relative_lift"]
        required_metric = weighted_fallback_metric * (1.0 - min_series_validation_lift)
        gate[series_id] = {
            "validation_cuts": [validation_cut for validation_cut, _cut_gate in per_cut_gates],
            "weighted_candidate_metric": weighted_candidate_metric,
            "weighted_fallback_metric": weighted_fallback_metric,
            "weighted_relative_lift": weighted_metric_lift,
            "weighted_mean_relative_lift": weighted_mean_relative_lift,
            "latest_relative_lift": latest_relative_lift,
            "risk_score": weighted_metric_lift,
            "required_metric_to_allow": required_metric,
            "min_series_validation_lift": min_series_validation_lift,
            "series_risk_decay": series_risk_decay,
            "allowed": weighted_candidate_metric <= required_metric,
            "cut_details": cut_details,
        }

    return gate, validation_reports


def selection_for_cut(
    *,
    cut: int,
    cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    families: list[str],
    learned_configs: list[CandidateConfig],
    metric: MetricName,
    policy: str,
    cold_start_family: str,
    fallback_family: str,
    min_validation_lift: float,
    min_series_validation_lift: float,
    series_risk_decay: float,
    softmax_steps: int,
    veto_k: int = 50,
    veto_regret_threshold: float = 0.0002,
    veto_feature_mode: str = "global",
) -> tuple[dict[str, Any], list[str]]:
    prior_cuts = [prior for prior in cuts if prior < cut]
    eval_rows = cut_rows[cut]
    fallback_config = CandidateConfig(name=f"fixed:{fallback_family}", kind="fixed", family=fallback_family)
    if policy not in {
        "validation_gated",
        "series_guarded",
        "series_multicut_guarded",
        "series_multicut_worst_guarded",
        "series_risk_penalized",
        "fallback_veto",
    }:
        raise ValueError(f"unsupported policy: {policy}")

    if not prior_cuts:
        decision = {
            "mode": "cold_start",
            "selected_config": f"fixed:{cold_start_family}",
            "prior_cuts": prior_cuts,
            "policy": policy,
        }
        return decision, fixed_selection(eval_rows, cold_start_family)

    if len(prior_cuts) == 1:
        decision = {
            "mode": "fallback_no_validation_cut",
            "selected_config": fallback_config.name,
            "prior_cuts": prior_cuts,
            "policy": policy,
        }
        return decision, fixed_selection(eval_rows, fallback_family)

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
    best_learned = min(learned_validation, key=lambda item: float(item["metrics"]["selected_metric"]))
    fallback_metric = float(fallback_validation["metrics"]["selected_metric"])
    best_learned_metric = float(best_learned["metrics"]["selected_metric"])
    required_metric = fallback_metric * (1.0 - min_validation_lift)
    should_route = best_learned_metric <= required_metric
    selected_config = CandidateConfig(**best_learned["config"]) if should_route else fallback_config
    all_prior_rows = [row for prior in prior_cuts for row in cut_rows[prior]]
    selected = select_candidate(
        selected_config,
        all_prior_rows,
        eval_rows,
        families=families,
        metric=metric,
        softmax_steps=softmax_steps,
    )
    series_gate = None
    series_gate_source = None
    series_gate_validation_reports = None
    fallback_veto_report = None
    if policy == "series_guarded" and should_route:
        validation_selected = select_candidate(
            selected_config,
            train_rows,
            validation_rows,
            families=families,
            metric=metric,
            softmax_steps=softmax_steps,
        )
        series_gate = series_validation_gate(
            validation_rows=validation_rows,
            candidate_selected=validation_selected,
            fallback_family=fallback_family,
            metric=metric,
            min_series_validation_lift=min_series_validation_lift,
        )
        series_gate_source = "latest_prior_validation_cut"
    elif policy in {"series_multicut_guarded", "series_multicut_worst_guarded"} and should_route:
        series_gate, series_gate_validation_reports = multicut_series_validation_gate(
            selected_config=selected_config,
            prior_cuts=prior_cuts,
            cut_rows=cut_rows,
            families=families,
            fallback_family=fallback_family,
            metric=metric,
            min_series_validation_lift=min_series_validation_lift,
            softmax_steps=softmax_steps,
            require_each_cut=policy == "series_multicut_worst_guarded",
        )
        if policy == "series_multicut_worst_guarded":
            series_gate_source = "all_prior_chronological_validation_cuts_require_each_cut"
        else:
            series_gate_source = "all_prior_chronological_validation_cuts"
    elif policy == "series_risk_penalized" and should_route:
        series_gate, series_gate_validation_reports = recency_weighted_series_risk_gate(
            selected_config=selected_config,
            prior_cuts=prior_cuts,
            cut_rows=cut_rows,
            families=families,
            fallback_family=fallback_family,
            metric=metric,
            min_series_validation_lift=min_series_validation_lift,
            series_risk_decay=series_risk_decay,
            softmax_steps=softmax_steps,
        )
        series_gate_source = "recency_weighted_prior_validation_cuts"
    elif policy == "fallback_veto" and should_route:
        base_selections: dict[int, dict[str, Any]] = {}
        for prior_cut in prior_cuts:
            base_decision, base_selected = selection_for_cut(
                cut=prior_cut,
                cuts=cuts,
                cut_rows=cut_rows,
                families=families,
                learned_configs=learned_configs,
                metric=metric,
                policy="validation_gated",
                cold_start_family=cold_start_family,
                fallback_family=fallback_family,
                min_validation_lift=min_validation_lift,
                min_series_validation_lift=0.0,
                series_risk_decay=series_risk_decay,
                softmax_steps=softmax_steps,
                veto_k=veto_k,
                veto_regret_threshold=veto_regret_threshold,
                veto_feature_mode=veto_feature_mode,
            )
            base_selections[prior_cut] = {
                "decision": base_decision,
                "selected_families": base_selected,
            }
        examples = historical_veto_examples(
            prior_cuts=prior_cuts,
            cut_rows=cut_rows,
            base_selections=base_selections,
            fallback_family=fallback_family,
            metric=metric,
        )
        selected, fallback_veto_report = apply_neighbor_regret_veto(
            eval_rows=eval_rows,
            selected_families=selected,
            examples=examples,
            families=families,
            fallback_family=fallback_family,
            include_series=veto_feature_mode == "series",
            k=veto_k,
            regret_threshold=veto_regret_threshold,
        )
        fallback_veto_report = {
            **fallback_veto_report,
            "feature_mode": veto_feature_mode,
            "veto_k": veto_k,
            "veto_regret_threshold": veto_regret_threshold,
        }

    if series_gate is not None:
        selected = [
            selected_family if series_gate[str(row["series_id"])]["allowed"] else fallback_family
            for row, selected_family in zip(eval_rows, selected)
        ]

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
        "policy": policy,
    }
    if series_gate is not None:
        allowed = [series_id for series_id, item in series_gate.items() if item["allowed"]]
        blocked = [series_id for series_id, item in series_gate.items() if not item["allowed"]]
        decision["series_gate"] = {
            "source": series_gate_source,
            "min_series_validation_lift": min_series_validation_lift,
            "allowed_series": allowed,
            "blocked_series": blocked,
            "per_series": series_gate,
        }
        if policy == "series_risk_penalized":
            decision["series_gate"]["series_risk_decay"] = series_risk_decay
        if series_gate_validation_reports is not None:
            decision["series_gate"]["validation_reports"] = series_gate_validation_reports
    if fallback_veto_report is not None:
        decision["fallback_veto"] = fallback_veto_report
    return decision, selected


def attribution_records(
    *,
    cut: int,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    fallback_family: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if len(rows) != len(selected_families):
        raise ValueError(f"cut={cut} row/selection length mismatch")

    for row, selected_family in zip(rows, selected_families):
        selected_mae = family_error(row, selected_family, "mae")
        selected_smape = family_error(row, selected_family, "smape")
        zero_mae = family_error(row, "zero-shot", "mae")
        zero_smape = family_error(row, "zero-shot", "smape")
        fallback_mae = family_error(row, fallback_family, "mae")
        fallback_smape = family_error(row, fallback_family, "smape")
        oracle_family = str(row["label"]["best_family_by_mae"])
        oracle_mae = family_error(row, oracle_family, "mae")
        oracle_smape = family_error(row, oracle_family, "smape")
        records.append(
            {
                "cut": cut,
                "row_id": row["row_id"],
                "window_id": row["window_id"],
                "series_id": row["series_id"],
                "selected_family": selected_family,
                "oracle_family": oracle_family,
                "selected_mae": selected_mae,
                "selected_smape": selected_smape,
                "zero_shot_mae": zero_mae,
                "zero_shot_smape": zero_smape,
                "fallback_mae": fallback_mae,
                "fallback_smape": fallback_smape,
                "oracle_mae": oracle_mae,
                "oracle_smape": oracle_smape,
                "delta_vs_zero_mae": zero_mae - selected_mae,
                "delta_vs_zero_smape": zero_smape - selected_smape,
                "delta_vs_fallback_mae": fallback_mae - selected_mae,
                "delta_vs_fallback_smape": fallback_smape - selected_smape,
                "oracle_gap_mae": selected_mae - oracle_mae,
                "oracle_gap_smape": selected_smape - oracle_smape,
            }
        )
    return records


def summarize_records(records: list[dict[str, Any]], *, metric: MetricName) -> dict[str, Any]:
    selected_key = f"selected_{metric}"
    zero_key = f"zero_shot_{metric}"
    fallback_key = f"fallback_{metric}"
    oracle_key = f"oracle_{metric}"
    delta_key = f"delta_vs_fallback_{metric}"
    selected_values = [float(record[selected_key]) for record in records]
    zero_values = [float(record[zero_key]) for record in records]
    fallback_values = [float(record[fallback_key]) for record in records]
    oracle_values = [float(record[oracle_key]) for record in records]
    delta_vs_fallback = [float(record[delta_key]) for record in records]

    return {
        "windows": len(records),
        "selected_counts": dict(sorted(Counter(record["selected_family"] for record in records).items())),
        f"selected_{metric}": mean(selected_values),
        f"zero_shot_{metric}": mean(zero_values),
        f"fallback_{metric}": mean(fallback_values),
        f"oracle_{metric}": mean(oracle_values),
        f"selected_{metric}_improvement_vs_zero_shot": improvement(mean(zero_values), mean(selected_values)),
        f"selected_{metric}_delta_vs_fallback": mean(fallback_values) - mean(selected_values),
        f"selected_{metric}_relative_lift_vs_fallback": improvement(
            mean(fallback_values), mean(selected_values)
        ),
        f"delta_vs_fallback_{metric}_sum": sum(delta_vs_fallback),
        "positive_delta_windows": sum(1 for value in delta_vs_fallback if value > 0),
        "negative_delta_windows": sum(1 for value in delta_vs_fallback if value < 0),
    }


def summarize_by_key(records: list[dict[str, Any]], *, key: str, metric: MetricName) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record[key])].append(record)
    return {
        group_key: summarize_records(group_records, metric=metric)
        for group_key, group_records in sorted(grouped.items())
    }


def ranked_series_contributions(
    per_series: dict[str, dict[str, Any]],
    *,
    metric: MetricName,
    total_delta_sum: float,
) -> list[dict[str, Any]]:
    ranked = []
    delta_sum_key = f"delta_vs_fallback_{metric}_sum"
    for series_id, summary in per_series.items():
        delta_sum = float(summary[delta_sum_key])
        contribution_fraction = delta_sum / total_delta_sum if abs(total_delta_sum) > 1e-12 else 0.0
        ranked.append(
            {
                "series_id": series_id,
                "windows": summary["windows"],
                delta_sum_key: delta_sum,
                "contribution_fraction_of_total_delta": contribution_fraction,
                f"selected_{metric}_delta_vs_fallback": summary[f"selected_{metric}_delta_vs_fallback"],
                f"selected_{metric}_relative_lift_vs_fallback": summary[
                    f"selected_{metric}_relative_lift_vs_fallback"
                ],
                "selected_counts": summary["selected_counts"],
            }
        )
    return sorted(ranked, key=lambda item: item[delta_sum_key], reverse=True)


def report_verdict(policy: str) -> str:
    if policy == "series_risk_penalized":
        return (
            "Recency-weighted series-risk gating balances recent failures "
            "against older evidence; promotion still requires broad stability."
        )
    if policy == "fallback_veto":
        return (
            "Fallback-veto routing rejects historically risky overrides; promotion "
            "still requires validation on a later archive or second target."
        )
    if policy == "series_multicut_worst_guarded":
        return (
            "Worst-cut series gating blocks any series with a prior cut-level "
            "regression; promotion still requires broader positive coverage."
        )
    if policy == "series_multicut_guarded":
        return (
            "Multi-cut series gating tests broader prior evidence, but promotion "
            "still requires stable gains across cuts and series."
        )
    if policy == "series_guarded":
        return (
            "Series-aware gating improves the validation-gated router, but "
            "promotion remains blocked until gains are broad and stable."
        )
    return "Router lift over fallback is concentrated and remains too small for promotion."


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
    learned_configs = learned_candidate_configs(args.candidate_set)
    cut_reports: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for cut in cuts:
        decision, selected_families = selection_for_cut(
            cut=cut,
            cuts=cuts,
            cut_rows=cut_rows,
            families=families,
            learned_configs=learned_configs,
            metric=args.metric,
            policy=args.policy,
            cold_start_family=args.cold_start_family,
            fallback_family=args.fallback_family,
            min_validation_lift=args.min_validation_lift,
            min_series_validation_lift=args.min_series_validation_lift,
            series_risk_decay=args.series_risk_decay,
            softmax_steps=args.softmax_steps,
            veto_k=args.veto_k,
            veto_regret_threshold=args.veto_regret_threshold,
            veto_feature_mode=args.veto_feature_mode,
        )
        cut_records = attribution_records(
            cut=cut,
            rows=cut_rows[cut],
            selected_families=selected_families,
            fallback_family=args.fallback_family,
        )
        records.extend(cut_records)
        cut_reports.append(
            {
                "cut": cut,
                "decision": decision,
                "metrics": summarize_records(cut_records, metric=args.metric),
                "per_series": summarize_by_key(cut_records, key="series_id", metric=args.metric),
            }
        )

    routed_records = [
        record
        for record in records
        if next(report for report in cut_reports if report["cut"] == record["cut"])["decision"]["mode"] != "cold_start"
    ]
    all_per_series = summarize_by_key(records, key="series_id", metric=args.metric)
    routed_per_series = summarize_by_key(routed_records, key="series_id", metric=args.metric)
    routed_summary = summarize_records(routed_records, metric=args.metric)
    delta_sum_key = f"delta_vs_fallback_{args.metric}_sum"
    total_delta_sum = float(routed_summary[delta_sum_key])
    ranked_routed_series = ranked_series_contributions(
        routed_per_series,
        metric=args.metric,
        total_delta_sum=total_delta_sum,
    )
    positive_series = [item for item in ranked_routed_series if item[delta_sum_key] > 0]
    negative_series = [item for item in ranked_routed_series if item[delta_sum_key] < 0]

    return {
        "method": f"{args.policy}_router_per_series_attribution",
        "input": str(input_path),
        "selection_metric": args.metric,
        "policy": args.policy,
        "cold_start_family": args.cold_start_family,
        "fallback_family": args.fallback_family,
        "candidate_set": args.candidate_set,
        "min_validation_lift": args.min_validation_lift,
        "min_series_validation_lift": args.min_series_validation_lift,
        "series_risk_decay": args.series_risk_decay,
        "veto_k": args.veto_k,
        "veto_regret_threshold": args.veto_regret_threshold,
        "veto_feature_mode": args.veto_feature_mode,
        "cuts": cuts,
        "families": families,
        "rows": len(records),
        "guardrail": (
            "Attribution recomputes routing using prior cuts only. Actual "
            "errors are used only after selection to score series-level outcomes."
        ),
        "summary": {
            "all_cuts": summarize_records(records, metric=args.metric),
            "routed_cuts_only": routed_summary,
            "positive_routed_series_count": len(positive_series),
            "negative_routed_series_count": len(negative_series),
            "top_positive_series": positive_series[:3],
            "top_negative_series": list(reversed(negative_series[-3:])),
            "verdict": report_verdict(args.policy),
        },
        "per_series": {
            "all_cuts": all_per_series,
            "routed_cuts_only": routed_per_series,
            "ranked_routed_contributions": ranked_routed_series,
        },
        "per_cut": cut_reports,
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    compact = {
        "output": str(output_path),
        "rows": report["rows"],
        "summary": report["summary"],
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
