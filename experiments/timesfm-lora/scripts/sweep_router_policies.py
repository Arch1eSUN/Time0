from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from typing import Any

from summarize_router_attribution import build_report, experiment_path


POLICIES = (
    "validation_gated",
    "series_guarded",
    "series_multicut_guarded",
    "series_multicut_worst_guarded",
    "series_risk_penalized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--policy", action="append", choices=POLICIES)
    parser.add_argument("--cold-start-family", default="recent2000")
    parser.add_argument("--fallback-family", default="recent2000")
    parser.add_argument(
        "--candidate-set",
        choices=["baseline", "loss-aware", "knn-regret"],
        default="baseline",
    )
    parser.add_argument("--min-validation-lift", action="append", type=float)
    parser.add_argument("--min-series-validation-lift", action="append", type=float)
    parser.add_argument("--series-risk-decay", action="append", type=float)
    parser.add_argument("--softmax-steps", type=int, default=2000)
    return parser.parse_args()


def values_or_default(values: list[float] | None, default: tuple[float, ...]) -> list[float]:
    return values if values else list(default)


def sweep_args(args: argparse.Namespace) -> list[SimpleNamespace]:
    policies = args.policy or ["validation_gated", "series_guarded", "series_risk_penalized"]
    validation_lifts = values_or_default(args.min_validation_lift, (0.0, 0.005, 0.01, 0.02))
    series_lifts = values_or_default(args.min_series_validation_lift, (0.0, 0.001, 0.0025, 0.005))
    risk_decays = values_or_default(args.series_risk_decay, (0.05, 0.1, 0.25, 0.5, 0.75, 1.0))

    runs: list[SimpleNamespace] = []
    for policy in policies:
        for validation_lift in validation_lifts:
            if policy == "validation_gated":
                runs.append(run_args(args, policy, validation_lift, 0.0, 0.1))
            elif policy == "series_risk_penalized":
                for series_lift in series_lifts:
                    for decay in risk_decays:
                        runs.append(run_args(args, policy, validation_lift, series_lift, decay))
            else:
                for series_lift in series_lifts:
                    runs.append(run_args(args, policy, validation_lift, series_lift, 0.1))
    return runs


def run_args(
    args: argparse.Namespace,
    policy: str,
    min_validation_lift: float,
    min_series_validation_lift: float,
    series_risk_decay: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        input=args.input,
        output=args.output,
        metric=args.metric,
        policy=policy,
        cold_start_family=args.cold_start_family,
        fallback_family=args.fallback_family,
        candidate_set=args.candidate_set,
        min_validation_lift=min_validation_lift,
        min_series_validation_lift=min_series_validation_lift,
        series_risk_decay=series_risk_decay,
        softmax_steps=args.softmax_steps,
    )


def extract_row(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    routed = summary["routed_cuts_only"]
    policy = str(report["policy"])
    metric = str(report["selection_metric"])
    metric_key = f"selected_{metric}"
    delta_key = f"selected_{metric}_delta_vs_fallback"
    relative_lift_key = f"selected_{metric}_relative_lift_vs_fallback"
    return {
        "policy": policy,
        "metric": metric,
        "min_validation_lift": float(report["min_validation_lift"]),
        "min_series_validation_lift": float(report["min_series_validation_lift"]),
        "series_risk_decay": float(report["series_risk_decay"]),
        "routed_windows": int(routed["windows"]),
        "selected_metric": float(routed[metric_key]),
        "delta_vs_fallback": float(routed[delta_key]),
        "relative_lift_vs_fallback": float(routed[relative_lift_key]),
        "improvement_vs_zero_shot": float(routed[f"selected_{metric}_improvement_vs_zero_shot"]),
        "positive_routed_series_count": int(summary["positive_routed_series_count"]),
        "negative_routed_series_count": int(summary["negative_routed_series_count"]),
        "selected_counts": routed["selected_counts"],
        "top_positive_series": summary["top_positive_series"],
        "top_negative_series": summary["top_negative_series"],
    }


def ranking_key(row: dict[str, Any]) -> tuple[float, int, float]:
    return (
        float(row["delta_vs_fallback"]),
        int(row["positive_routed_series_count"]) - int(row["negative_routed_series_count"]),
        -float(row["selected_metric"]),
    )


def main() -> None:
    args = parse_args()
    rows = []
    for current_args in sweep_args(args):
        report = build_report(current_args)
        rows.append(extract_row(report))

    ranked = sorted(rows, key=ranking_key, reverse=True)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "method": "router_policy_sweep",
        "input": str(experiment_path(args.input)),
        "metric": args.metric,
        "candidate_set": args.candidate_set,
        "rows": len(rows),
        "best_by_delta": ranked[0],
        "top_rows": ranked[:10],
        "all_rows": ranked,
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "rows": result["rows"],
                "best_by_delta": result["best_by_delta"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
