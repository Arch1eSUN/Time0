from __future__ import annotations

import argparse
import json
from typing import Any

from diagnose_router_override_failures import (
    counterfactual_summary,
    reconstruct_policy_reports,
    routed_rows_and_selection,
    selected_policy,
)
from evaluate_prediction_router import (
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
        "--diagnosis-report",
        default=(
            "reports/router-override-failure-diagnosis-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "reports/router-target-fallback-frozen-validation-alignment-normalized-"
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
    parser.add_argument("--freeze-after-cut", type=int)
    return parser.parse_args()


def relative_lift(reference: float, candidate: float) -> float:
    return (reference - candidate) / reference


def fallback_metric(rows: list[dict[str, Any]], families: list[str], fallback_family: str, metric: MetricName) -> float:
    return float(
        selection_metrics(
            rows=rows,
            selected_families=fixed_selection(rows, fallback_family),
            families=families,
            metric=metric,
        )["selected_metric"]
    )


def selected_metric(rows: list[dict[str, Any]], selected_families: list[str], families: list[str], metric: MetricName) -> float:
    return float(
        selection_metrics(
            rows=rows,
            selected_families=selected_families,
            families=families,
            metric=metric,
        )["selected_metric"]
    )


def subset_by_cut(
    rows: list[dict[str, Any]],
    selected_families: list[str],
    *,
    min_cut_exclusive: int | None = None,
    max_cut_inclusive: int | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    filtered_rows: list[dict[str, Any]] = []
    filtered_selected: list[str] = []
    for row, selected_family in zip(rows, selected_families):
        cut = int(row["cut"])
        if min_cut_exclusive is not None and cut <= min_cut_exclusive:
            continue
        if max_cut_inclusive is not None and cut > max_cut_inclusive:
            continue
        filtered_rows.append(row)
        filtered_selected.append(selected_family)
    return filtered_rows, filtered_selected


def target_series_from_diagnosis(diagnosis: dict[str, Any]) -> list[str]:
    return list(diagnosis["target_series"])


def infer_freeze_after_cut(diagnosis: dict[str, Any]) -> int:
    cuts: list[int] = []
    for series in diagnosis["target_series"].values():
        cuts.extend(int(cut) for cut in series["override_by_cut"])
    if not cuts:
        raise ValueError("cannot infer freeze cut without target override cuts")
    return max(cuts)


def apply_target_fallback(
    *,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    target_series: list[str],
    fallback_family: str,
) -> tuple[list[str], int]:
    target_set = set(target_series)
    changed = 0
    next_selected: list[str] = []
    for row, selected_family in zip(rows, selected_families):
        if str(row["series_id"]) in target_set and selected_family != fallback_family:
            next_selected.append(fallback_family)
            changed += 1
        else:
            next_selected.append(selected_family)
    return next_selected, changed


def split_report(
    *,
    name: str,
    rows: list[dict[str, Any]],
    selected_families: list[str],
    target_series: list[str],
    families: list[str],
    fallback_family: str,
    metric: MetricName,
) -> dict[str, Any]:
    if not rows:
        return {
            "name": name,
            "windows": 0,
            "changed_windows": 0,
            "original": None,
            "target_fallback": None,
            "verdict": "no_windows",
        }

    reference = fallback_metric(rows, families, fallback_family, metric)
    original_metric = selected_metric(rows, selected_families, families, metric)
    target_selected, changed_windows = apply_target_fallback(
        rows=rows,
        selected_families=selected_families,
        target_series=target_series,
        fallback_family=fallback_family,
    )
    target_metric = selected_metric(rows, target_selected, families, metric)
    target_series_summary = series_delta_summary(
        rows=rows,
        selected_families=target_selected,
        fallback_family=fallback_family,
        metric=metric,
    )
    if changed_windows == 0:
        verdict = "no_rule_exposure"
    elif target_metric < original_metric:
        verdict = "rule_improves_split"
    elif target_metric == original_metric:
        verdict = "rule_no_metric_change"
    else:
        verdict = "rule_hurts_split"

    return {
        "name": name,
        "windows": len(rows),
        "changed_windows": changed_windows,
        "original": {
            "selected_metric": original_metric,
            "relative_lift_vs_fallback": relative_lift(reference, original_metric),
            "series_summary": series_delta_summary(
                rows=rows,
                selected_families=selected_families,
                fallback_family=fallback_family,
                metric=metric,
            ),
        },
        "target_fallback": {
            "selected_metric": target_metric,
            "relative_lift_vs_fallback": relative_lift(reference, target_metric),
            "series_summary": target_series_summary,
        },
        "verdict": verdict,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    router_rows = load_router_rows(experiment_path(args.input))
    router_report = json.loads(experiment_path(args.router_report).read_text())
    diagnosis = json.loads(experiment_path(args.diagnosis_report).read_text())
    policy = selected_policy(router_report, args.policy_summary)
    rows = list(router_rows["data"])
    cuts = [int(cut) for cut in router_rows["cuts"]]
    families = list(router_rows["families"])
    cut_rows = rows_by_cut(rows)
    target_series = args.target_series or target_series_from_diagnosis(diagnosis)
    freeze_after_cut = args.freeze_after_cut if args.freeze_after_cut is not None else infer_freeze_after_cut(diagnosis)

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

    pre_rows, pre_selected = subset_by_cut(
        routed_rows,
        routed_selected,
        max_cut_inclusive=freeze_after_cut,
    )
    future_rows, future_selected = subset_by_cut(
        routed_rows,
        routed_selected,
        min_cut_exclusive=freeze_after_cut,
    )

    all_counterfactual = counterfactual_summary(
        rows=routed_rows,
        selected_families=routed_selected,
        target_series=target_series,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    validation_split = split_report(
        name="future_after_freeze_cut",
        rows=future_rows,
        selected_families=future_selected,
        target_series=target_series,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    discovery_split = split_report(
        name="through_freeze_cut",
        rows=pre_rows,
        selected_families=pre_selected,
        target_series=target_series,
        families=families,
        fallback_family=args.fallback_family,
        metric=args.metric,
    )
    if validation_split["verdict"] == "rule_improves_split":
        verdict = "future_validated_positive"
    elif validation_split["verdict"] == "no_rule_exposure":
        verdict = "not_validated_no_future_exposure"
    else:
        verdict = "not_promotable"

    return {
        "method": "target_fallback_frozen_validation",
        "input": args.input,
        "router_report": args.router_report,
        "diagnosis_report": args.diagnosis_report,
        "policy_summary": args.policy_summary,
        "policy": compact_policy_summary(policy),
        "metric": args.metric,
        "fallback_family": args.fallback_family,
        "target_series": target_series,
        "freeze_after_cut": freeze_after_cut,
        "cuts": cuts,
        "routed_rows": len(routed_rows),
        "posthoc_all_rows_counterfactual": all_counterfactual,
        "discovery_split": discovery_split,
        "validation_split": validation_split,
        "verdict": verdict,
        "guardrail": (
            "The target-series list comes from a completed diagnosis. Only the "
            "future_after_freeze_cut split can validate the frozen rule without "
            "using those future labels for selection."
        ),
    }


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    validation = report["validation_split"]
    print(
        json.dumps(
            {
                "output": str(output_path),
                "verdict": report["verdict"],
                "target_series": report["target_series"],
                "freeze_after_cut": report["freeze_after_cut"],
                "posthoc_changed_windows": report["posthoc_all_rows_counterfactual"]["changed_windows"],
                "posthoc_negative_series": report["posthoc_all_rows_counterfactual"]["series_summary"][
                    "negative_routed_series_count"
                ],
                "validation_windows": validation["windows"],
                "validation_changed_windows": validation["changed_windows"],
                "validation_verdict": validation["verdict"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
