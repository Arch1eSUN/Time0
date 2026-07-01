from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


MetricName = str


@dataclass(frozen=True)
class SeriesMetrics:
    windows: int
    mae: float
    smape: float


@dataclass(frozen=True)
class EvalReport:
    family: str
    cut: int
    path: Path
    windows: int
    mae: float
    smape: float
    per_series: dict[str, SeriesMetrics]

    def metric(self, name: MetricName) -> float:
        if name == "mae":
            return self.mae
        if name == "smape":
            return self.smape
        raise ValueError(f"unsupported metric: {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metric", choices=["mae", "smape"], default="mae")
    parser.add_argument("--horizon-len", type=int, default=20)
    parser.add_argument("--cold-start-family", required=True)
    parser.add_argument("--zero-shot", action="append", required=True, help="CUT=report.json")
    parser.add_argument("--candidate", action="append", required=True, help="FAMILY:CUT=report.json")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def experiment_path(path: str) -> Path:
    raw_path = Path(path)
    if raw_path.is_absolute():
        return raw_path
    return Path(__file__).resolve().parents[1] / raw_path


def parse_zero_spec(raw: str) -> tuple[int, Path]:
    cut_text, path_text = raw.split("=", maxsplit=1)
    return int(cut_text), experiment_path(path_text)


def parse_candidate_spec(raw: str) -> tuple[str, int, Path]:
    family_cut, path_text = raw.split("=", maxsplit=1)
    family, cut_text = family_cut.split(":", maxsplit=1)
    return family, int(cut_text), experiment_path(path_text)


def load_report(path: Path, *, family: str, cut: int) -> EvalReport:
    data = json.loads(path.read_text())
    if int(data["skip_windows"]) != cut:
        raise ValueError(f"{path} has skip_windows={data['skip_windows']}, expected {cut}")

    per_series: dict[str, SeriesMetrics] = {}
    for series_id, values in data["per_series"].items():
        per_series[series_id] = SeriesMetrics(
            windows=int(values["windows"]),
            mae=float(values["mae"]),
            smape=float(values["smape"]),
        )

    return EvalReport(
        family=family,
        cut=cut,
        path=path,
        windows=int(data["windows"]),
        mae=float(data["mae"]),
        smape=float(data["smape"]),
        per_series=per_series,
    )


def weighted_mean(values: list[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight <= 0:
        raise ValueError("cannot average values without positive weights")
    return sum(value * weight for value, weight in values) / total_weight


def report_weight(report: EvalReport, horizon_len: int) -> int:
    return report.windows * horizon_len


def series_weight(metrics: SeriesMetrics, horizon_len: int) -> int:
    return metrics.windows * horizon_len


def improvement(reference: float, candidate: float) -> float:
    return (reference - candidate) / reference


def aggregate_reports(reports: list[EvalReport], horizon_len: int) -> dict[str, float]:
    return {
        "mae": weighted_mean([(report.mae, report_weight(report, horizon_len)) for report in reports]),
        "smape": weighted_mean([(report.smape, report_weight(report, horizon_len)) for report in reports]),
    }


def aggregate_route_cuts(cuts: list[dict[str, object]]) -> dict[str, float]:
    values = [cut for cut in cuts if int(cut["windows"]) > 0]
    routed_mae = weighted_mean([(float(cut["routed_mae"]), int(cut["windows"])) for cut in values])
    routed_smape = weighted_mean([(float(cut["routed_smape"]), int(cut["windows"])) for cut in values])
    zero_mae = weighted_mean([(float(cut["zero_mae"]), int(cut["windows"])) for cut in values])
    zero_smape = weighted_mean([(float(cut["zero_smape"]), int(cut["windows"])) for cut in values])
    return {
        "zero_mae": zero_mae,
        "routed_mae": routed_mae,
        "mae_improvement": improvement(zero_mae, routed_mae),
        "zero_smape": zero_smape,
        "routed_smape": routed_smape,
        "smape_improvement": improvement(zero_smape, routed_smape),
    }


def select_global_family(
    *,
    families: list[str],
    candidate_reports: dict[str, dict[int, EvalReport]],
    prior_cuts: list[int],
    metric: MetricName,
    horizon_len: int,
    cold_start_family: str,
) -> tuple[str, dict[str, float]]:
    if not prior_cuts:
        return cold_start_family, {}

    scores: dict[str, float] = {}
    for family in families:
        reports = [candidate_reports[family][cut] for cut in prior_cuts]
        scores[family] = weighted_mean(
            [(report.metric(metric), report_weight(report, horizon_len)) for report in reports]
        )
    return min(scores, key=scores.__getitem__), scores


def select_series_family(
    *,
    series_id: str,
    families: list[str],
    candidate_reports: dict[str, dict[int, EvalReport]],
    prior_cuts: list[int],
    metric: MetricName,
    horizon_len: int,
    cold_start_family: str,
) -> tuple[str, dict[str, float]]:
    if not prior_cuts:
        return cold_start_family, {}

    scores: dict[str, float] = {}
    for family in families:
        values: list[tuple[float, int]] = []
        for cut in prior_cuts:
            series_metrics = candidate_reports[family][cut].per_series[series_id]
            values.append((getattr(series_metrics, metric), series_weight(series_metrics, horizon_len)))
        scores[family] = weighted_mean(values)
    return min(scores, key=scores.__getitem__), scores


def evaluate_global_policy(
    *,
    cuts: list[int],
    families: list[str],
    zero_reports: dict[int, EvalReport],
    candidate_reports: dict[str, dict[int, EvalReport]],
    metric: MetricName,
    horizon_len: int,
    cold_start_family: str,
) -> dict[str, object]:
    per_cut: list[dict[str, object]] = []
    for cut in cuts:
        prior_cuts = [prior for prior in cuts if prior < cut]
        selected_family, history_scores = select_global_family(
            families=families,
            candidate_reports=candidate_reports,
            prior_cuts=prior_cuts,
            metric=metric,
            horizon_len=horizon_len,
            cold_start_family=cold_start_family,
        )
        selected_report = candidate_reports[selected_family][cut]
        zero_report = zero_reports[cut]
        per_cut.append(
            {
                "cut": cut,
                "routed": bool(prior_cuts),
                "prior_cuts": prior_cuts,
                "selected_family": selected_family,
                "history_scores": history_scores,
                "windows": report_weight(selected_report, horizon_len),
                "zero_mae": zero_report.mae,
                "routed_mae": selected_report.mae,
                "mae_improvement": improvement(zero_report.mae, selected_report.mae),
                "zero_smape": zero_report.smape,
                "routed_smape": selected_report.smape,
                "smape_improvement": improvement(zero_report.smape, selected_report.smape),
            }
        )

    routed_cuts = [cut for cut in per_cut if bool(cut["routed"])]
    return {
        "per_cut": per_cut,
        "all_cuts": aggregate_route_cuts(per_cut),
        "routed_cuts_only": aggregate_route_cuts(routed_cuts),
    }


def evaluate_per_series_policy(
    *,
    cuts: list[int],
    families: list[str],
    zero_reports: dict[int, EvalReport],
    candidate_reports: dict[str, dict[int, EvalReport]],
    metric: MetricName,
    horizon_len: int,
    cold_start_family: str,
) -> dict[str, object]:
    per_cut: list[dict[str, object]] = []
    for cut in cuts:
        prior_cuts = [prior for prior in cuts if prior < cut]
        zero_report = zero_reports[cut]
        selected_counts = {family: 0 for family in families}
        routed_mae_values: list[tuple[float, int]] = []
        routed_smape_values: list[tuple[float, int]] = []
        series_routes: dict[str, dict[str, object]] = {}

        for series_id in sorted(zero_report.per_series):
            selected_family, history_scores = select_series_family(
                series_id=series_id,
                families=families,
                candidate_reports=candidate_reports,
                prior_cuts=prior_cuts,
                metric=metric,
                horizon_len=horizon_len,
                cold_start_family=cold_start_family,
            )
            selected_counts[selected_family] += 1
            selected_metrics = candidate_reports[selected_family][cut].per_series[series_id]
            weight = series_weight(selected_metrics, horizon_len)
            routed_mae_values.append((selected_metrics.mae, weight))
            routed_smape_values.append((selected_metrics.smape, weight))
            series_routes[series_id] = {
                "selected_family": selected_family,
                "history_scores": history_scores,
                "mae": selected_metrics.mae,
                "smape": selected_metrics.smape,
                "windows": selected_metrics.windows,
            }

        routed_mae = weighted_mean(routed_mae_values)
        routed_smape = weighted_mean(routed_smape_values)
        per_cut.append(
            {
                "cut": cut,
                "routed": bool(prior_cuts),
                "prior_cuts": prior_cuts,
                "selected_counts": selected_counts,
                "windows": report_weight(zero_report, horizon_len),
                "zero_mae": zero_report.mae,
                "routed_mae": routed_mae,
                "mae_improvement": improvement(zero_report.mae, routed_mae),
                "zero_smape": zero_report.smape,
                "routed_smape": routed_smape,
                "smape_improvement": improvement(zero_report.smape, routed_smape),
                "series_routes": series_routes,
            }
        )

    routed_cuts = [cut for cut in per_cut if bool(cut["routed"])]
    return {
        "per_cut": per_cut,
        "all_cuts": aggregate_route_cuts(per_cut),
        "routed_cuts_only": aggregate_route_cuts(routed_cuts),
    }


def evaluate_fixed_families(
    *,
    cuts: list[int],
    families: list[str],
    zero_reports: dict[int, EvalReport],
    candidate_reports: dict[str, dict[int, EvalReport]],
    horizon_len: int,
) -> dict[str, object]:
    zero = aggregate_reports([zero_reports[cut] for cut in cuts], horizon_len)
    fixed: dict[str, object] = {}
    for family in families:
        metrics = aggregate_reports([candidate_reports[family][cut] for cut in cuts], horizon_len)
        fixed[family] = {
            "mae": metrics["mae"],
            "mae_improvement": improvement(zero["mae"], metrics["mae"]),
            "smape": metrics["smape"],
            "smape_improvement": improvement(zero["smape"], metrics["smape"]),
        }
    return fixed


def evaluate_current_cut_oracle(
    *,
    cuts: list[int],
    families: list[str],
    zero_reports: dict[int, EvalReport],
    candidate_reports: dict[str, dict[int, EvalReport]],
    metric: MetricName,
    horizon_len: int,
) -> dict[str, object]:
    per_cut: list[dict[str, object]] = []
    for cut in cuts:
        selected_family = min(families, key=lambda family: candidate_reports[family][cut].metric(metric))
        selected_report = candidate_reports[selected_family][cut]
        zero_report = zero_reports[cut]
        per_cut.append(
            {
                "cut": cut,
                "selected_family": selected_family,
                "windows": report_weight(selected_report, horizon_len),
                "zero_mae": zero_report.mae,
                "routed_mae": selected_report.mae,
                "mae_improvement": improvement(zero_report.mae, selected_report.mae),
                "zero_smape": zero_report.smape,
                "routed_smape": selected_report.smape,
                "smape_improvement": improvement(zero_report.smape, selected_report.smape),
            }
        )
    return {
        "warning": "Leaky upper bound: selects the best family using the same cut being evaluated.",
        "per_cut": per_cut,
        "all_cuts": aggregate_route_cuts(per_cut),
    }


def main() -> None:
    args = parse_args()
    zero_reports = {
        cut: load_report(path, family="zero-shot", cut=cut) for cut, path in map(parse_zero_spec, args.zero_shot)
    }

    candidate_reports: dict[str, dict[int, EvalReport]] = {}
    for family, cut, path in map(parse_candidate_spec, args.candidate):
        candidate_reports.setdefault(family, {})[cut] = load_report(path, family=family, cut=cut)

    families = sorted(candidate_reports)
    cuts = sorted(zero_reports)
    missing = {
        family: [cut for cut in cuts if cut not in reports] for family, reports in candidate_reports.items()
    }
    missing = {family: cuts for family, cuts in missing.items() if cuts}
    if missing:
        raise SystemExit(f"missing candidate reports: {missing}")
    if args.cold_start_family not in candidate_reports:
        raise SystemExit(f"unknown cold-start family: {args.cold_start_family}")

    report = {
        "method": "no_leak_historical_adapter_router",
        "selection_metric": args.metric,
        "horizon_len": args.horizon_len,
        "cold_start_family": args.cold_start_family,
        "guardrail": "For each cut, route selection uses only prior cut reports. The current cut is used only for final evaluation.",
        "cuts": cuts,
        "families": families,
        "zero_shot": aggregate_reports([zero_reports[cut] for cut in cuts], args.horizon_len),
        "fixed_families": evaluate_fixed_families(
            cuts=cuts,
            families=families,
            zero_reports=zero_reports,
            candidate_reports=candidate_reports,
            horizon_len=args.horizon_len,
        ),
        "policies": {
            "global_history_best": evaluate_global_policy(
                cuts=cuts,
                families=families,
                zero_reports=zero_reports,
                candidate_reports=candidate_reports,
                metric=args.metric,
                horizon_len=args.horizon_len,
                cold_start_family=args.cold_start_family,
            ),
            "per_series_history_best": evaluate_per_series_policy(
                cuts=cuts,
                families=families,
                zero_reports=zero_reports,
                candidate_reports=candidate_reports,
                metric=args.metric,
                horizon_len=args.horizon_len,
                cold_start_family=args.cold_start_family,
            ),
            "leaky_current_cut_best_global": evaluate_current_cut_oracle(
                cuts=cuts,
                families=families,
                zero_reports=zero_reports,
                candidate_reports=candidate_reports,
                metric=args.metric,
                horizon_len=args.horizon_len,
            ),
        },
        "report_paths": {
            "zero_shot": {str(cut): str(report.path) for cut, report in sorted(zero_reports.items())},
            "candidates": {
                family: {str(cut): str(report.path) for cut, report in sorted(reports.items())}
                for family, reports in sorted(candidate_reports.items())
            },
        },
    }

    output = experiment_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
