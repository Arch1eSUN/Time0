from __future__ import annotations

import argparse
import json
from collections import Counter
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
from evaluate_router_fallback_veto import (
    apply_policy_history_series_constraint,
    base_selection_by_cut,
    compact_policy_summary,
    policy_history_series_delta_summary,
    series_delta_summary,
)
from router_fallback_veto import (
    apply_neighbor_regret_veto,
    apply_series_downside_veto,
    apply_series_family_downside_veto,
    historical_series_delta_summary,
    historical_series_family_delta_summary,
    historical_veto_examples,
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
            "reports/router-override-failure-diagnosis-alignment-normalized-"
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
    parser.add_argument("--target-series", action="append")
    return parser.parse_args()


def selected_policy(router_report: dict[str, Any], summary_key: str) -> dict[str, Any]:
    policy = router_report["summary"][summary_key]
    if policy is None:
        raise ValueError(f"router summary is null: {summary_key}")
    return policy


def reconstruct_policy_reports(
    *,
    cuts: list[int],
    cut_rows: dict[int, list[dict[str, Any]]],
    base_selections: dict[int, dict[str, Any]],
    families: list[str],
    policy: dict[str, Any],
    metric: MetricName,
    fallback_family: str,
) -> list[dict[str, Any]]:
    include_series = policy["feature_mode"] == "series"
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
        selected, neighbor_report = apply_neighbor_regret_veto(
            eval_rows=eval_rows,
            selected_families=base_selected,
            examples=examples,
            families=families,
            fallback_family=fallback_family,
            include_series=include_series,
            k=int(policy["k"]),
            regret_threshold=float(policy["regret_threshold"]),
        )

        series_downside_report = None
        if policy.get("series_downside_threshold") is not None:
            series_summary = historical_series_delta_summary(
                prior_cuts=prior_cuts,
                cut_rows=cut_rows,
                base_selections=base_selections,
                fallback_family=fallback_family,
                metric=metric,
            )
            selected, series_downside_report = apply_series_downside_veto(
                eval_rows=eval_rows,
                selected_families=selected,
                series_summary=series_summary,
                fallback_family=fallback_family,
                min_series_delta=float(policy["series_downside_threshold"]),
            )

        series_family_downside_report = None
        if policy.get("series_family_downside_threshold") is not None:
            series_family_summary = historical_series_family_delta_summary(
                prior_cuts=prior_cuts,
                cut_rows=cut_rows,
                base_selections=base_selections,
                fallback_family=fallback_family,
                metric=metric,
            )
            selected, series_family_downside_report = apply_series_family_downside_veto(
                eval_rows=eval_rows,
                selected_families=selected,
                series_family_summary=series_family_summary,
                fallback_family=fallback_family,
                min_series_family_delta=float(policy["series_family_downside_threshold"]),
            )

        policy_history_series_report = None
        if policy.get("policy_history_series_threshold") is not None:
            policy_history_summary = policy_history_series_delta_summary(
                prior_reports=per_cut,
                fallback_family=fallback_family,
                metric=metric,
            )
            selected, policy_history_series_report = apply_policy_history_series_constraint(
                eval_rows=eval_rows,
                selected_families=selected,
                series_summary=policy_history_summary,
                fallback_family=fallback_family,
                min_series_delta=float(policy["policy_history_series_threshold"]),
                min_windows=int(policy["policy_history_min_windows"]),
            )

        per_cut.append(
            {
                "cut": cut,
                "rows": eval_rows,
                "selected_families": selected,
                "decision": {
                    "base_decision": base_selections[cut]["decision"],
                    "veto": {
                        "neighbor": neighbor_report,
                        "series_downside": series_downside_report,
                        "series_family_downside": series_family_downside_report,
                        "policy_history_series": policy_history_series_report,
                    },
                },
            }
        )
    return per_cut


def routed_rows_and_selection(per_cut: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    routed = [report for report in per_cut if report["decision"]["base_decision"]["mode"] != "cold_start"]
    rows = [row for report in routed for row in report["rows"]]
    selected = [family for report in routed for family in report["selected_families"]]
    return rows, selected


def counterfactual_summary(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    target_series: list[str],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    target_set = set(target_series)
    counterfactual = [
        fallback_family if str(row["series_id"]) in target_set else selected_family
        for row, selected_family in zip(rows, selected_families)
    ]
    changed_windows = sum(
        1
        for row, original, changed in zip(rows, selected_families, counterfactual)
        if str(row["series_id"]) in target_set and original != changed
    )
    metrics = selection_metrics(rows=rows, selected_families=counterfactual, families=families, metric=metric)
    return {
        "target_series": target_series,
        "changed_windows": changed_windows,
        "metrics": metrics,
        "series_summary": series_delta_summary(
            rows=rows,
            selected_families=counterfactual,
            fallback_family=fallback_family,
            metric=metric,
        ),
    }


def family_counter(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def family_delta_summary(rows: list[dict[str, Any]], selected_families: list[str], fallback_family: str, metric: MetricName) -> dict[str, Any]:
    selected_counts: Counter[str] = Counter()
    selected_delta_sum: Counter[str] = Counter()
    selected_harm_count: Counter[str] = Counter()
    for row, selected_family in zip(rows, selected_families):
        selected_counts[selected_family] += 1
        delta = family_error(row, fallback_family, metric) - family_error(row, selected_family, metric)
        selected_delta_sum[selected_family] += delta
        if delta < 0.0:
            selected_harm_count[selected_family] += 1
    return {
        family: {
            "windows": int(selected_counts[family]),
            "delta_vs_fallback_sum": float(selected_delta_sum[family]),
            "harm_count": int(selected_harm_count[family]),
        }
        for family in sorted(selected_counts)
    }


def target_series_summary(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    target_series: str,
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    target_rows: list[dict[str, Any]] = []
    target_selected: list[str] = []
    override_rows: list[dict[str, Any]] = []
    override_selected: list[str] = []
    top_harmful: list[dict[str, Any]] = []
    top_beneficial: list[dict[str, Any]] = []
    by_cut: dict[int, list[float]] = {}
    best_family_counts: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    selected_was_best = 0
    fallback_would_win = 0

    for row, selected_family in zip(rows, selected_families):
        if str(row["series_id"]) != target_series:
            continue
        target_rows.append(row)
        target_selected.append(selected_family)
        selected_counts[selected_family] += 1
        if selected_family == fallback_family:
            continue

        selected_error = family_error(row, selected_family, metric)
        fallback_error = family_error(row, fallback_family, metric)
        delta = fallback_error - selected_error
        best_family = str(row["label"][f"best_family_by_{metric}"])
        best_family_counts[best_family] += 1
        if selected_family == best_family:
            selected_was_best += 1
        if fallback_error < selected_error:
            fallback_would_win += 1
        by_cut.setdefault(int(row["cut"]), []).append(delta)
        item = {
            "row_id": row["row_id"],
            "cut": row["cut"],
            "start_index": row["start_index"],
            "selected_family": selected_family,
            "best_family": best_family,
            "selected_error": selected_error,
            "fallback_error": fallback_error,
            "delta_vs_fallback": delta,
            "best_margin": row["label"][f"best_margin_{metric}"],
            "context": row["runtime_features"]["context"],
            "prediction_disagreement_normalized": row["runtime_features"]["prediction_disagreement_normalized"],
        }
        override_rows.append(row)
        override_selected.append(selected_family)
        if delta < 0.0:
            top_harmful.append(item)
        elif delta > 0.0:
            top_beneficial.append(item)

    target_series_delta = series_delta_summary(
        rows=target_rows,
        selected_families=target_selected,
        fallback_family=fallback_family,
        metric=metric,
    )
    override_deltas = [
        family_error(row, fallback_family, metric) - family_error(row, selected_family, metric)
        for row, selected_family in zip(override_rows, override_selected)
    ]
    harmful_override_count = sum(delta < 0.0 for delta in override_deltas)
    beneficial_override_count = sum(delta > 0.0 for delta in override_deltas)

    return {
        "series_id": target_series,
        "all_selected_counts": family_counter(selected_counts),
        "series_delta": target_series_delta,
        "override_windows": len(override_rows),
        "override_delta_sum": sum(override_deltas),
        "override_delta_mean": sum(override_deltas) / len(override_deltas) if override_deltas else 0.0,
        "harmful_override_count": harmful_override_count,
        "beneficial_override_count": beneficial_override_count,
        "fallback_would_win_count": fallback_would_win,
        "selected_was_best_count": selected_was_best,
        "best_family_counts_on_override_windows": family_counter(best_family_counts),
        "override_by_selected_family": family_delta_summary(
            override_rows,
            override_selected,
            fallback_family,
            metric,
        ),
        "override_by_cut": {
            str(cut): {
                "windows": len(deltas),
                "delta_vs_fallback_sum": sum(deltas),
                "harm_count": sum(delta < 0.0 for delta in deltas),
            }
            for cut, deltas in sorted(by_cut.items())
        },
        "top_harmful_overrides": sorted(top_harmful, key=lambda item: float(item["delta_vs_fallback"]))[:10],
        "top_beneficial_overrides": sorted(
            top_beneficial,
            key=lambda item: float(item["delta_vs_fallback"]),
            reverse=True,
        )[:10],
    }


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
    fallback_metric = selection_metrics(
        rows=routed_rows,
        selected_families=fixed_selection(routed_rows, args.fallback_family),
        families=families,
        metric=args.metric,
    )["selected_metric"]
    original_metrics = selection_metrics(
        rows=routed_rows,
        selected_families=routed_selected,
        families=families,
        metric=args.metric,
    )
    default_targets = [
        str(item["series_id"])
        for item in policy.get("top_negative_series", [])
    ]
    target_series = args.target_series or default_targets
    if not target_series:
        raise ValueError("no target series provided and policy has no negative series")

    target_summaries = {
        series_id: target_series_summary(
            rows=routed_rows,
            selected_families=routed_selected,
            target_series=series_id,
            families=families,
            fallback_family=args.fallback_family,
            metric=args.metric,
        )
        for series_id in target_series
    }

    target_counterfactuals = {
        series_id: counterfactual_summary(
            rows=routed_rows,
            selected_families=routed_selected,
            target_series=[series_id],
            families=families,
            fallback_family=args.fallback_family,
            metric=args.metric,
        )
        for series_id in target_series
    }
    combined_counterfactual = counterfactual_summary(
        rows=routed_rows,
        selected_families=routed_selected,
        target_series=target_series,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )

    return {
        "method": "router_override_failure_diagnosis",
        "input": args.input,
        "router_report": args.router_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "families": families,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "fallback_routed_metric": fallback_metric,
        "original": {
            "metrics": original_metrics,
            "series_summary": series_delta_summary(
                rows=routed_rows,
                selected_families=routed_selected,
                fallback_family=args.fallback_family,
                metric=args.metric,
            ),
        },
        "target_series": target_summaries,
        "target_counterfactuals": target_counterfactuals,
        "combined_target_fallback_counterfactual": combined_counterfactual,
        "guardrail": (
            "Target-series fallback counterfactuals are diagnostic only. They use "
            "series identified by the completed backtest and are not a deployable "
            "no-leak rule without a future validation split."
        ),
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    combined = report["combined_target_fallback_counterfactual"]
    print(
        json.dumps(
            {
                "output": str(output_path),
                "policy": report["policy"],
                "target_series": list(report["target_series"]),
                "original_relative_lift": (
                    (report["fallback_routed_metric"] - report["original"]["metrics"]["selected_metric"])
                    / report["fallback_routed_metric"]
                ),
                "combined_counterfactual_relative_lift": (
                    (report["fallback_routed_metric"] - combined["metrics"]["selected_metric"])
                    / report["fallback_routed_metric"]
                ),
                "combined_counterfactual_negative_series": combined["series_summary"][
                    "negative_routed_series_count"
                ],
                "combined_counterfactual_changed_windows": combined["changed_windows"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
