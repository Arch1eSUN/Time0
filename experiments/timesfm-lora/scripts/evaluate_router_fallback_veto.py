from __future__ import annotations

import argparse
import json
from typing import Any

from evaluate_prediction_router import (
    experiment_path,
    family_error,
    fixed_selection,
    learned_candidate_configs,
    load_router_rows,
    rows_by_cut,
    selection_metrics,
)
from router_fallback_veto import apply_neighbor_regret_veto, historical_veto_examples
from summarize_router_attribution import selection_for_cut


MetricName = str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="reports/router-rows-early-regime-ablate-alignment-normalized-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument(
        "--output",
        default="reports/router-fallback-veto-knn-regret-alignment-normalized-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--candidate-set", choices=["baseline", "loss-aware", "knn-regret"], default="knn-regret")
    parser.add_argument("--cold-start-family", default="recent2000")
    parser.add_argument("--fallback-family", default="recent2000")
    parser.add_argument("--min-validation-lift", type=float, default=0.005)
    parser.add_argument("--softmax-steps", type=int, default=2000)
    parser.add_argument("--veto-k", type=int, action="append")
    parser.add_argument("--regret-threshold", type=float, action="append")
    parser.add_argument("--feature-mode", choices=["global", "series"], action="append")
    return parser.parse_args()


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty values")
    return sum(values) / len(values)


def improvement(reference: float, candidate: float) -> float:
    return (reference - candidate) / reference


def base_selection_by_cut(
    *,
    cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    families: list[str],
    learned_configs: list[Any],
    metric: MetricName,
    cold_start_family: str,
    fallback_family: str,
    min_validation_lift: float,
    softmax_steps: int,
) -> dict[int, dict[str, Any]]:
    selections: dict[int, dict[str, Any]] = {}
    for cut in cuts:
        decision, selected = selection_for_cut(
            cut=cut,
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
            series_risk_decay=0.1,
            softmax_steps=softmax_steps,
        )
        selections[cut] = {"decision": decision, "selected_families": selected}
    return selections


def aggregate_reports(cut_reports: list[dict[str, Any]], metric: MetricName) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    selected: list[str] = []
    families = list(cut_reports[0]["families"])
    for report in cut_reports:
        rows.extend(report["rows"])
        selected.extend(report["selected_families"])
    return selection_metrics(rows=rows, selected_families=selected, families=families, metric=metric)


def series_delta_summary(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    selected_counts: dict[str, dict[str, int]] = {}
    for row, selected_family in zip(rows, selected_families):
        series_id = str(row["series_id"])
        selected_error = family_error(row, selected_family, metric)
        fallback_error = family_error(row, fallback_family, metric)
        grouped.setdefault(series_id, []).append(fallback_error - selected_error)
        selected_counts.setdefault(series_id, {})
        selected_counts[series_id][selected_family] = selected_counts[series_id].get(selected_family, 0) + 1

    summaries = []
    for series_id, deltas in sorted(grouped.items()):
        summaries.append(
            {
                "series_id": series_id,
                "windows": len(deltas),
                "delta_vs_fallback_sum": sum(deltas),
                "delta_vs_fallback_mean": mean(deltas),
                "selected_counts": dict(sorted(selected_counts[series_id].items())),
            }
        )
    positive = [item for item in summaries if item["delta_vs_fallback_sum"] > 0.0]
    negative = [item for item in summaries if item["delta_vs_fallback_sum"] < 0.0]
    return {
        "positive_routed_series_count": len(positive),
        "negative_routed_series_count": len(negative),
        "top_positive_series": sorted(
            positive,
            key=lambda item: float(item["delta_vs_fallback_sum"]),
            reverse=True,
        )[:3],
        "top_negative_series": sorted(negative, key=lambda item: float(item["delta_vs_fallback_sum"]))[:3],
    }


def evaluate_veto_config(
    *,
    cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    base_selections: dict[int, dict[str, Any]],
    families: list[str],
    metric: MetricName,
    fallback_family: str,
    include_series: bool,
    k: int,
    regret_threshold: float,
) -> dict[str, Any]:
    per_cut: list[dict[str, Any]] = []
    for cut in cuts:
        prior_cuts = [prior for prior in cuts if prior < cut]
        eval_rows = cut_rows[cut]
        base_selected = list(base_selections[cut]["selected_families"])
        examples = historical_veto_examples(
            prior_cuts=prior_cuts,
            cut_rows=cut_rows,
            base_selections=base_selections,
            fallback_family=fallback_family,
            metric=metric,
        )
        selected, veto_report = apply_neighbor_regret_veto(
            eval_rows=eval_rows,
            selected_families=base_selected,
            examples=examples,
            families=families,
            fallback_family=fallback_family,
            include_series=include_series,
            k=k,
            regret_threshold=regret_threshold,
        )
        metrics = selection_metrics(rows=eval_rows, selected_families=selected, families=families, metric=metric)
        per_cut.append(
            {
                "cut": cut,
                "families": families,
                "rows": eval_rows,
                "selected_families": selected,
                "decision": {
                    "base_decision": base_selections[cut]["decision"],
                    "veto": veto_report,
                },
                "metrics": metrics,
            }
        )

    routed = [report for report in per_cut if report["decision"]["base_decision"]["mode"] != "cold_start"]
    routed_rows = [row for report in routed for row in report["rows"]]
    routed_selected = [family for report in routed for family in report["selected_families"]]
    all_metrics = aggregate_reports(per_cut, metric)
    routed_metrics = aggregate_reports(routed, metric) if routed else None
    series_summary = (
        series_delta_summary(
            rows=routed_rows,
            selected_families=routed_selected,
            fallback_family=fallback_family,
            metric=metric,
        )
        if routed
        else None
    )
    return {
        "feature_mode": "series" if include_series else "global",
        "k": k,
        "regret_threshold": regret_threshold,
        "all_cuts": all_metrics,
        "routed_cuts_only": routed_metrics,
        "series_summary": series_summary,
        "vetoed_windows": sum(int(report["decision"]["veto"]["vetoed_windows"]) for report in per_cut),
        "per_cut": [
            {
                "cut": report["cut"],
                "decision": report["decision"],
                "metrics": report["metrics"],
            }
            for report in per_cut
        ],
    }


def base_report(
    *,
    cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    base_selections: dict[int, dict[str, Any]],
    families: list[str],
    metric: MetricName,
    fallback_family: str,
) -> dict[str, Any]:
    per_cut: list[dict[str, Any]] = []
    for cut in cuts:
        rows = cut_rows[cut]
        selected = base_selections[cut]["selected_families"]
        per_cut.append(
            {
                "cut": cut,
                "families": families,
                "rows": rows,
                "selected_families": selected,
                "decision": base_selections[cut]["decision"],
                "metrics": selection_metrics(rows=rows, selected_families=selected, families=families, metric=metric),
            }
        )
    routed = [report for report in per_cut if report["decision"]["mode"] != "cold_start"]
    routed_rows = [row for report in routed for row in report["rows"]]
    routed_selected = [family for report in routed for family in report["selected_families"]]
    return {
        "policy": "validation_gated",
        "all_cuts": aggregate_reports(per_cut, metric),
        "routed_cuts_only": aggregate_reports(routed, metric),
        "series_summary": series_delta_summary(
            rows=routed_rows,
            selected_families=routed_selected,
            fallback_family=fallback_family,
            metric=metric,
        ),
        "per_cut": [
            {
                "cut": report["cut"],
                "decision": report["decision"],
                "metrics": report["metrics"],
            }
            for report in per_cut
        ],
    }


def with_delta(policy: dict[str, Any], fallback_metric: float) -> dict[str, Any]:
    routed = policy["routed_cuts_only"]
    selected_metric = float(routed["selected_metric"])
    series_summary = policy["series_summary"]
    return {
        "feature_mode": policy.get("feature_mode", "none"),
        "k": policy.get("k"),
        "regret_threshold": policy.get("regret_threshold"),
        "selected_metric": selected_metric,
        "delta_vs_fallback": fallback_metric - selected_metric,
        "relative_lift_vs_fallback": improvement(fallback_metric, selected_metric),
        "selected_counts": routed["selected_counts"],
        "vetoed_windows": policy.get("vetoed_windows", 0),
        "positive_routed_series_count": series_summary["positive_routed_series_count"],
        "negative_routed_series_count": series_summary["negative_routed_series_count"],
        "top_positive_series": series_summary["top_positive_series"],
        "top_negative_series": series_summary["top_negative_series"],
    }


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
    veto_ks = args.veto_k or [25, 50, 100]
    regret_thresholds = (
        args.regret_threshold if args.regret_threshold is not None else [-0.0001, 0.0, 0.00005, 0.0001]
    )
    feature_modes = args.feature_mode or ["global", "series"]

    base_selections = base_selection_by_cut(
        cuts=cuts,
        cut_rows=cut_rows,
        families=families,
        learned_configs=learned_configs,
        metric=args.metric,
        cold_start_family=args.cold_start_family,
        fallback_family=args.fallback_family,
        min_validation_lift=args.min_validation_lift,
        softmax_steps=args.softmax_steps,
    )
    base = base_report(
        cuts=cuts,
        cut_rows=cut_rows,
        base_selections=base_selections,
        families=families,
        metric=args.metric,
        fallback_family=args.fallback_family,
    )

    routed_rows = [row for cut in cuts[1:] for row in cut_rows[cut]]
    fallback_metric = selection_metrics(
        rows=routed_rows,
        selected_families=fixed_selection(routed_rows, args.fallback_family),
        families=families,
        metric=args.metric,
    )["selected_metric"]

    veto_policies = []
    for feature_mode in feature_modes:
        for k in veto_ks:
            for regret_threshold in regret_thresholds:
                veto_policies.append(
                    evaluate_veto_config(
                        cuts=cuts,
                        cut_rows=cut_rows,
                        base_selections=base_selections,
                        families=families,
                        metric=args.metric,
                        fallback_family=args.fallback_family,
                        include_series=feature_mode == "series",
                        k=k,
                        regret_threshold=regret_threshold,
                    )
                )

    base_summary = with_delta(base, float(fallback_metric))
    veto_summaries = [with_delta(policy, float(fallback_metric)) for policy in veto_policies]
    best_by_delta = max(veto_summaries, key=lambda item: float(item["delta_vs_fallback"]))
    best_by_series_spread = max(
        veto_summaries,
        key=lambda item: (
            int(item["positive_routed_series_count"]) - int(item["negative_routed_series_count"]),
            float(item["delta_vs_fallback"]),
        ),
    )

    return {
        "method": "no_leak_router_fallback_veto",
        "input": str(input_path),
        "metric": args.metric,
        "candidate_set": args.candidate_set,
        "cold_start_family": args.cold_start_family,
        "fallback_family": args.fallback_family,
        "min_validation_lift": args.min_validation_lift,
        "cuts": cuts,
        "families": families,
        "rows": len(rows),
        "guardrail": (
            "The fallback-veto classifier trains only on completed prior cuts. "
            "Current-cut errors are used only for final offline scoring."
        ),
        "baseline": base,
        "veto_policies": veto_policies,
        "summary": {
            "fallback_routed_metric": fallback_metric,
            "baseline": base_summary,
            "best_veto_by_delta": best_by_delta,
            "best_veto_by_series_spread": best_by_series_spread,
            "top_veto_rows": sorted(
                veto_summaries,
                key=lambda item: float(item["delta_vs_fallback"]),
                reverse=True,
            )[:10],
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
                "baseline": report["summary"]["baseline"],
                "best_veto_by_delta": report["summary"]["best_veto_by_delta"],
                "best_veto_by_series_spread": report["summary"]["best_veto_by_series_spread"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
