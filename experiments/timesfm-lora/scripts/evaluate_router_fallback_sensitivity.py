from __future__ import annotations

import argparse
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from evaluate_prediction_router import build_report, experiment_path, load_router_rows

EPSILON = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--candidate-set", choices=["baseline", "loss-aware", "knn-regret"], default="knn-regret")
    parser.add_argument("--fallback-family", action="append")
    parser.add_argument("--min-validation-lift", type=float, default=0.0)
    parser.add_argument("--softmax-steps", type=int, default=2000)
    return parser.parse_args()


def fallback_families(args: argparse.Namespace, source: dict[str, Any]) -> list[str]:
    families = list(source["families"])
    if not args.fallback_family:
        return families
    invalid = sorted(set(args.fallback_family).difference(families))
    if invalid:
        raise ValueError(f"unknown fallback families: {invalid}")
    return [family for family in families if family in args.fallback_family]


def report_for_fallback(args: argparse.Namespace, fallback_family: str) -> dict[str, Any]:
    return build_report(
        Namespace(
            input=args.input,
            metric=args.metric,
            cold_start_family=fallback_family,
            fallback_family=fallback_family,
            min_validation_lift=args.min_validation_lift,
            softmax_steps=args.softmax_steps,
            candidate_set=args.candidate_set,
        )
    )


def fallback_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    return {
        "fallback_family": report["fallback_family"],
        "fallback_metric": summary["fallback_family_routed_metric"],
        "validation_gated_metric": summary["validation_gated_routed_metric"],
        "delta_vs_fallback_metric": summary["validation_gated_delta_vs_fallback_metric"],
        "validation_gated_improvement_vs_zero_shot": summary[
            "validation_gated_routed_improvement_vs_zero_shot"
        ],
        "best_chronological_diagnostic": summary["best_chronological_diagnostic"],
        "best_chronological_diagnostic_metric": summary[
            "best_chronological_diagnostic_routed_metric"
        ],
        "verdict": summary["verdict"],
        "validation_gated_per_cut": report["policies"]["validation_gated"]["per_cut"],
    }


def sensitivity_verdict(deltas: list[float]) -> str:
    positive_count = sum(delta > EPSILON for delta in deltas)
    negative_count = sum(delta < -EPSILON for delta in deltas)
    zero_count = len(deltas) - positive_count - negative_count
    if positive_count == len(deltas):
        return "robust_positive"
    if positive_count and negative_count:
        return "fallback_sensitive"
    if positive_count and zero_count:
        return "partial_positive"
    if zero_count == len(deltas):
        return "fail_closed_all"
    return "not_promotable"


def build_sensitivity_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = experiment_path(args.input)
    source = load_router_rows(input_path)
    fallbacks = fallback_families(args, source)
    reports = [report_for_fallback(args, fallback) for fallback in fallbacks]
    summaries = [fallback_summary(report) for report in reports]
    deltas = [float(summary["delta_vs_fallback_metric"]) for summary in summaries]
    positive = [
        summary["fallback_family"]
        for summary in summaries
        if float(summary["delta_vs_fallback_metric"]) > EPSILON
    ]
    negative = [
        summary["fallback_family"]
        for summary in summaries
        if float(summary["delta_vs_fallback_metric"]) < -EPSILON
    ]
    zero = [
        summary["fallback_family"]
        for summary in summaries
        if abs(float(summary["delta_vs_fallback_metric"])) <= EPSILON
    ]

    return {
        "method": "router_fallback_sensitivity",
        "input": str(input_path),
        "metric": args.metric,
        "candidate_set": args.candidate_set,
        "min_validation_lift": args.min_validation_lift,
        "softmax_steps": args.softmax_steps,
        "families": source["families"],
        "fallback_families": fallbacks,
        "rows": source["rows"],
        "guardrail": (
            "Promotion requires router gains to be robust to fallback choice. "
            "A policy that wins against one fallback but loses against another is "
            "fallback-sensitive and should remain blocked."
        ),
        "summary": {
            "verdict": sensitivity_verdict(deltas),
            "positive_fallbacks": positive,
            "negative_fallbacks": negative,
            "zero_delta_fallbacks": zero,
            "min_delta_vs_fallback_metric": min(deltas),
            "max_delta_vs_fallback_metric": max(deltas),
            "positive_count": len(positive),
            "fallback_count": len(fallbacks),
        },
        "per_fallback": summaries,
    }


def main() -> None:
    args = parse_args()
    report = build_sensitivity_report(args)
    output_path = experiment_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "rows": report["rows"],
                "metric": report["metric"],
                "summary": report["summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
