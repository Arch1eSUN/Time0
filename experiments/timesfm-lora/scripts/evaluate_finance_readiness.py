from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SENSITIVITY_REPORTS = [
    "reports/router-fallback-sensitivity-market-macro-realized-vol-20-"
    "zscore-recent2000-smape-h20-r4.json",
    "reports/router-fallback-sensitivity-market-macro-realized-vol-20-"
    "zscore-all-recent-smape-h20-r4.json",
    "reports/router-fallback-sensitivity-market-macro-realized-vol-20-"
    "zscore-all-recent-mae-h20-r4.json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-json",
        default="reports/finance-readiness-market-macro-realized-vol-20-h20-r4.json",
    )
    parser.add_argument(
        "--output-md",
        default="runs/2026-07-02-market-macro-finance-readiness.md",
    )
    parser.add_argument("--fixed-cut", type=int, action="append")
    parser.add_argument("--fixed-family", default="recent2000")
    parser.add_argument(
        "--zero-shot-template",
        default=(
            "reports/timesfm-zero-shot-market-macro-realized-vol-20-h20-"
            "holdout500-skip{cut}.json"
        ),
    )
    parser.add_argument(
        "--lora-template",
        default=(
            "reports/timesfm-lora-market-macro-realized-vol-20-h20-r4-"
            "step200-recent2000-train{cut}-holdout500-skip{cut}.json"
        ),
    )
    parser.add_argument(
        "--router-report",
        default=(
            "reports/router-fallback-veto-series-risk-objective-alignment-normalized-"
            "market-macro-realized-vol-20-h20-r4.json"
        ),
    )
    parser.add_argument(
        "--sensitivity-report",
        action="append",
    )
    parser.add_argument("--min-fixed-average-lift", type=float, default=0.02)
    parser.add_argument("--min-cut-wins", type=int, default=3)
    parser.add_argument("--min-router-extra-lift", type=float, default=0.002)
    parser.add_argument("--max-negative-router-series", type=int, default=0)
    return parser.parse_args()


def experiment_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else EXPERIMENT_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def relative_improvement(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        raise ValueError(f"baseline metric must be positive: {baseline}")
    return (baseline - candidate) / baseline


def evaluate_fixed_adapter(args: argparse.Namespace) -> dict[str, Any]:
    cuts: list[dict[str, Any]] = []
    fixed_cuts = args.fixed_cut or [4000, 5000, 5500]
    for cut in fixed_cuts:
        zero_path = experiment_path(args.zero_shot_template.format(cut=cut))
        lora_path = experiment_path(args.lora_template.format(cut=cut))
        zero = load_json(zero_path)
        lora = load_json(lora_path)
        zero_mae = float(zero["mae"])
        lora_mae = float(lora["mae"])
        zero_smape = float(zero["smape"])
        lora_smape = float(lora["smape"])
        series_wins = 0
        series_total = 0
        for series_id, zero_series in zero["per_series"].items():
            lora_series = lora["per_series"][series_id]
            series_total += 1
            if float(lora_series["mae"]) < float(zero_series["mae"]):
                series_wins += 1
        cuts.append(
            {
                "cut": cut,
                "zero_shot_mae": zero_mae,
                "lora_mae": lora_mae,
                "mae_relative_lift": relative_improvement(zero_mae, lora_mae),
                "zero_shot_smape": zero_smape,
                "lora_smape": lora_smape,
                "smape_relative_lift": relative_improvement(zero_smape, lora_smape),
                "series_mae_wins": series_wins,
                "series_count": series_total,
            }
        )

    average_mae_lift = sum(float(cut["mae_relative_lift"]) for cut in cuts) / len(cuts)
    average_smape_lift = sum(float(cut["smape_relative_lift"]) for cut in cuts) / len(cuts)
    positive_cut_count = sum(float(cut["mae_relative_lift"]) > 0.0 for cut in cuts)
    return {
        "family": args.fixed_family,
        "target": "realized_vol_20",
        "cuts": cuts,
        "average_mae_relative_lift": average_mae_lift,
        "average_smape_relative_lift": average_smape_lift,
        "positive_mae_cut_count": positive_cut_count,
        "cut_count": len(cuts),
        "min_series_mae_wins": min(int(cut["series_mae_wins"]) for cut in cuts),
    }


def evaluate_router(args: argparse.Namespace) -> dict[str, Any]:
    report = load_json(experiment_path(args.router_report))
    best = report["summary"]["best_veto_by_delta"]
    spread = report["summary"]["best_veto_by_series_spread"]
    return {
        "source": args.router_report,
        "method": report["method"],
        "metric": report["metric"],
        "rows": report["rows"],
        "cuts": report["cuts"],
        "fallback_family": report["fallback_family"],
        "best_by_delta": {
            "delta_vs_fallback": best["delta_vs_fallback"],
            "relative_lift_vs_fallback": best["relative_lift_vs_fallback"],
            "positive_routed_series_count": best["positive_routed_series_count"],
            "negative_routed_series_count": best["negative_routed_series_count"],
            "vetoed_windows": best["vetoed_windows"],
            "top_negative_series": best["top_negative_series"],
        },
        "best_by_series_spread": {
            "delta_vs_fallback": spread["delta_vs_fallback"],
            "relative_lift_vs_fallback": spread["relative_lift_vs_fallback"],
            "positive_routed_series_count": spread["positive_routed_series_count"],
            "negative_routed_series_count": spread["negative_routed_series_count"],
            "vetoed_windows": spread["vetoed_windows"],
            "top_negative_series": spread["top_negative_series"],
        },
    }


def evaluate_sensitivity(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sensitivity_reports = args.sensitivity_report or DEFAULT_SENSITIVITY_REPORTS
    for report_path in sensitivity_reports:
        report = load_json(experiment_path(report_path))
        rows.append(
            {
                "source": report_path,
                "metric": report["metric"],
                "families": report["families"],
                "fallback_families": report["fallback_families"],
                "verdict": report["summary"]["verdict"],
                "positive_count": report["summary"]["positive_count"],
                "fallback_count": report["summary"]["fallback_count"],
                "negative_fallbacks": report["summary"]["negative_fallbacks"],
                "min_delta_vs_fallback_metric": report["summary"]["min_delta_vs_fallback_metric"],
                "max_delta_vs_fallback_metric": report["summary"]["max_delta_vs_fallback_metric"],
            }
        )
    return rows


def build_readiness_report(args: argparse.Namespace) -> dict[str, Any]:
    fixed = evaluate_fixed_adapter(args)
    router = evaluate_router(args)
    sensitivity = evaluate_sensitivity(args)
    best_router = router["best_by_delta"]

    gates = {
        "fixed_average_mae_lift": {
            "required": args.min_fixed_average_lift,
            "actual": fixed["average_mae_relative_lift"],
            "passed": fixed["average_mae_relative_lift"] >= args.min_fixed_average_lift,
        },
        "fixed_positive_cut_count": {
            "required": args.min_cut_wins,
            "actual": fixed["positive_mae_cut_count"],
            "passed": fixed["positive_mae_cut_count"] >= args.min_cut_wins,
        },
        "router_extra_lift_vs_fallback": {
            "required": args.min_router_extra_lift,
            "actual": best_router["relative_lift_vs_fallback"],
            "passed": best_router["relative_lift_vs_fallback"] >= args.min_router_extra_lift,
        },
        "router_negative_series": {
            "required": args.max_negative_router_series,
            "actual": best_router["negative_routed_series_count"],
            "passed": best_router["negative_routed_series_count"] <= args.max_negative_router_series,
        },
        "zscore_fallback_sensitivity": {
            "required": "no fallback_sensitive verdicts in checked zscore reports",
            "actual": [row["verdict"] for row in sensitivity],
            "passed": all(row["verdict"] != "fallback_sensitive" for row in sensitivity),
        },
    }
    release_ready = all(gate["passed"] for gate in gates.values())
    negative_stop_ready = (
        fixed["average_mae_relative_lift"] <= 0.0
        and best_router["delta_vs_fallback"] <= 0.0
        and all(row["verdict"] == "not_promotable" for row in sensitivity)
    )
    if release_ready:
        verdict = "release_stop_ready"
        recommendation = "prepare public LoRA adapter release and enter maintenance mode"
    elif negative_stop_ready:
        verdict = "negative_stop_ready"
        recommendation = "stop the finance line and publish the negative result"
    else:
        verdict = "continue_research"
        recommendation = (
            "do not publish yet; continue only on router downside control or a clearly scoped "
            "new target/rank test"
        )

    return {
        "method": "finance_readiness_gate",
        "target_domain": "public market and macro risk forecasting",
        "target_field": "realized_vol_20",
        "intended_effect": (
            "specialize TimesFM 2.5 for 20-step market/macro realized-volatility "
            "forecasting as a risk input, not as financial advice or a trading signal"
        ),
        "fixed_adapter": fixed,
        "router": router,
        "sensitivity": sensitivity,
        "release_gates": gates,
        "verdict": verdict,
        "recommendation": recommendation,
    }


def percent(value: float) -> str:
    return f"{value * 100:.3f}%"


def write_markdown(report: dict[str, Any], output_path: Path) -> None:
    fixed = report["fixed_adapter"]
    router = report["router"]
    best_router = router["best_by_delta"]
    gates = report["release_gates"]
    lines = [
        "# Market Macro Finance Readiness Gate",
        "",
        "Date: 2026-07-02",
        "",
        "## Goal",
        "",
        "Answer when the finance LoRA direction can stop and what final effect it should deliver.",
        "",
        "## Current Verdict",
        "",
        f"Verdict: `{report['verdict']}`",
        "",
        f"Recommendation: {report['recommendation']}.",
        "",
        "## Intended Final Effect",
        "",
        report["intended_effect"],
        "",
        "## Gate Results",
        "",
        "| Gate | Required | Actual | Pass |",
        "|---|---:|---:|---|",
    ]
    for name, gate in gates.items():
        required = gate["required"]
        actual = gate["actual"]
        if isinstance(required, float):
            required_text = percent(required)
        else:
            required_text = str(required)
        if isinstance(actual, float):
            actual_text = percent(actual)
        elif isinstance(actual, list):
            actual_text = ", ".join(str(item) for item in actual)
        else:
            actual_text = str(actual)
        lines.append(f"| `{name}` | {required_text} | {actual_text} | {gate['passed']} |")

    lines.extend(
        [
            "",
            "## Fixed Adapter Evidence",
            "",
            f"Family: `{fixed['family']}`",
            "",
            "| Cut | MAE lift vs zero-shot | SMAPE lift vs zero-shot | Series MAE wins |",
            "|---:|---:|---:|---:|",
        ]
    )
    for cut in fixed["cuts"]:
        lines.append(
            "| {cut} | {mae} | {smape} | {wins}/{total} |".format(
                cut=cut["cut"],
                mae=percent(cut["mae_relative_lift"]),
                smape=percent(cut["smape_relative_lift"]),
                wins=cut["series_mae_wins"],
                total=cut["series_count"],
            )
        )

    lines.extend(
        [
            "",
            f"Average MAE lift: {percent(fixed['average_mae_relative_lift'])}",
            "",
            "## Router Evidence",
            "",
            f"Rows: {router['rows']}",
            "",
            f"Cuts: {router['cuts']}",
            "",
            f"Fallback family: `{router['fallback_family']}`",
            "",
            "| Router checkpoint | Value |",
            "|---|---:|",
            f"| extra lift vs fallback | {percent(best_router['relative_lift_vs_fallback'])} |",
            f"| delta vs fallback | {best_router['delta_vs_fallback']:.10f} |",
            (
                "| positive / negative series | "
                f"{best_router['positive_routed_series_count']} / "
                f"{best_router['negative_routed_series_count']} |"
            ),
            f"| vetoed windows | {best_router['vetoed_windows']} |",
            "",
            "## Sensitivity Evidence",
            "",
            "| Report | Metric | Verdict | Negative fallbacks |",
            "|---|---|---|---|",
        ]
    )
    for row in report["sensitivity"]:
        lines.append(
            "| `{source}` | {metric} | `{verdict}` | {negative} |".format(
                source=row["source"],
                metric=row["metric"],
                verdict=row["verdict"],
                negative=", ".join(row["negative_fallbacks"]) or "none",
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Fact: the current fixed `recent2000` adapter improves all three checked "
                "MAE cut-points but averages below the 2% release threshold."
            ),
            "",
            (
                "Fact: the current best router adds a small lift over fixed `recent2000` "
                "but still has negative routed series."
            ),
            "",
            (
                "Fact: the zscore all-recent branch remains fallback-sensitive and cannot "
                "be used as release evidence."
            ),
            "",
            (
                "Inference: the finance direction has a real signal, but it has not reached "
                "a clean stopping point."
            ),
            "",
            (
                "Recommendation: keep the finance line open, but only for targeted downside "
                "control or one scoped rank/target comparison. Do not keep training without "
                "a gate-moving hypothesis."
            ),
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    report = build_readiness_report(args)
    output_json = experiment_path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2) + "\n")
    output_md = experiment_path(args.output_md)
    write_markdown(report, output_md)
    print(
        json.dumps(
            {
                "output_json": str(output_json),
                "output_md": str(output_md),
                "verdict": report["verdict"],
                "fixed_average_mae_lift": report["fixed_adapter"]["average_mae_relative_lift"],
                "router_extra_lift": report["router"]["best_by_delta"][
                    "relative_lift_vs_fallback"
                ],
                "negative_router_series": report["router"]["best_by_delta"][
                    "negative_routed_series_count"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
