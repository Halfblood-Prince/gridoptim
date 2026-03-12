from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

EQUATION = (
    "x*x + y*y + z*z + w*w "
    "+ 0.10*x*y - 0.20*z*w "
    "+ 0.05*x*z + 0.03*y*w "
    "+ 3.0*x - 2.0*y + 1.0*z - 0.5*w"
)

# 11 points per dimension -> 14,641 total evaluations.
GRID_SPEC = {
    "x": (-5.0, 5.0, 1.0),
    "y": (-5.0, 5.0, 1.0),
    "z": (-5.0, 5.0, 1.0),
    "w": (-5.0, 5.0, 1.0),
}
MODE = "min"
REPEATS = int(os.getenv("GRIDOPTIM_BENCH_REPEATS", "3"))
ABS_TOL = 1e-9
PARAM_TOL = 1e-9

LOG_PATH = PROJECT_ROOT / "benchmark_logs.json"
REPORT_PATH = PROJECT_ROOT / "benchmark_report.md"


@dataclass
class BenchmarkResult:
    name: str
    runtime_seconds: float | None
    best_value: float | None
    best_params: Dict[str, float]
    error: str | None = None
    traceback_text: str | None = None
    status: str = "not_run"


@dataclass
class BenchmarkSummary:
    equation: str
    grid_spec: Dict[str, Tuple[float, float, float]]
    repeats: int
    mode: str
    gridoptim: BenchmarkResult
    reference: BenchmarkResult
    same_optimum: bool
    winner: str
    speed_ratio_reference_over_gridoptim: float | None
    overall_status: str
    next_codex_action: str


def objective_values(x: float, y: float, z: float, w: float) -> float:
    return (
        x * x + y * y + z * z + w * w
        + 0.10 * x * y - 0.20 * z * w
        + 0.05 * x * z + 0.03 * y * w
        + 3.0 * x - 2.0 * y + 1.0 * z - 0.5 * w
    )


def compare_params(a: Dict[str, float], b: Dict[str, float]) -> bool:
    if a.keys() != b.keys():
        return False
    return all(math.isclose(a[k], b[k], abs_tol=PARAM_TOL, rel_tol=0.0) for k in a)


def run_gridoptim() -> BenchmarkResult:
    try:
        from gridoptim import GridSearchOptimiser

        durations: List[float] = []
        best_value: float | None = None
        best_params: Dict[str, float] = {}

        for _ in range(REPEATS):
            optimiser = GridSearchOptimiser()
            optimiser.function(EQUATION)
            for var, (min_v, max_v, step) in GRID_SPEC.items():
                optimiser.set_range(var, min_v, max_v, step)
            t0 = time.perf_counter()
            value, params = optimiser.optimise(MODE)
            durations.append(time.perf_counter() - t0)
            best_value = float(value)
            best_params = {k: float(v) for k, v in params.items()}

        runtime = statistics.median(durations)
        return BenchmarkResult(
            name="gridoptim",
            runtime_seconds=runtime,
            best_value=best_value,
            best_params=best_params,
            status="success",
        )
    except Exception as exc:
        return BenchmarkResult(
            name="gridoptim",
            runtime_seconds=None,
            best_value=None,
            best_params={},
            error=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
            status="failed_candidate",
        )


def run_reference() -> BenchmarkResult:
    try:
        from scipy import optimize

        bounds = [slice(v[0], v[1] + v[2], v[2]) for v in GRID_SPEC.values()]

        def func(point: Tuple[float, float, float, float]) -> float:
            x, y, z, w = point
            return objective_values(float(x), float(y), float(z), float(w))

        durations: List[float] = []
        best_value: float | None = None
        best_params: Dict[str, float] = {}

        for _ in range(REPEATS):
            t0 = time.perf_counter()
            result = optimize.brute(func, bounds, full_output=True, finish=None)
            durations.append(time.perf_counter() - t0)
            best_point, best_value, _, _ = result
            best_params = {key: float(best_point[i]) for i, key in enumerate(GRID_SPEC.keys())}
            best_value = float(best_value)

        runtime = statistics.median(durations)
        return BenchmarkResult(
            name="scipy.optimize.brute",
            runtime_seconds=runtime,
            best_value=best_value,
            best_params=best_params,
            status="success",
        )
    except Exception as exc:
        return BenchmarkResult(
            name="scipy.optimize.brute",
            runtime_seconds=None,
            best_value=None,
            best_params={},
            error=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
            status="failed_reference",
        )


def determine_winner(gridoptim_result: BenchmarkResult, reference_result: BenchmarkResult) -> tuple[str, float | None]:
    if gridoptim_result.error and reference_result.error:
        return "no winner", None
    if gridoptim_result.error:
        return reference_result.name, None
    if reference_result.error:
        return gridoptim_result.name, None

    assert gridoptim_result.runtime_seconds is not None
    assert reference_result.runtime_seconds is not None
    ratio = reference_result.runtime_seconds / gridoptim_result.runtime_seconds
    winner = gridoptim_result.name if gridoptim_result.runtime_seconds < reference_result.runtime_seconds else reference_result.name
    return winner, ratio


def determine_overall_status(
    gridoptim_result: BenchmarkResult,
    reference_result: BenchmarkResult,
    same_optimum: bool,
    winner: str,
) -> tuple[str, str]:
    if gridoptim_result.status == "failed_candidate" and reference_result.status == "failed_reference":
        return (
            "failed_both",
            "Read benchmark_logs.json first. Fix both the candidate package and the reference benchmark environment before doing any optimisation work.",
        )
    if gridoptim_result.status == "failed_candidate":
        return (
            "failed_candidate",
            "Read benchmark_logs.json first. Fix the gridoptim build, import, API, or runtime failure. Do not start performance work until the benchmark completes successfully.",
        )
    if reference_result.status == "failed_reference":
        return (
            "failed_reference",
            "Read benchmark_logs.json first. Fix the benchmark harness or CI environment so scipy.optimize.brute runs successfully. Do not compare performance until both sides complete.",
        )
    if not same_optimum:
        return (
            "failed_correctness",
            "Read benchmark_logs.json and benchmark_report.md first. Fix correctness so gridoptim matches the reference optimum before attempting speed improvements.",
        )
    if winner == "gridoptim":
        return (
            "success_candidate_faster",
            "Gridoptim is currently faster and correct on this benchmark. Preserve correctness, then look for further safe speedups or broaden benchmark coverage.",
        )
    return (
        "success_candidate_slower",
        "Read benchmark_report.md first, then make whatever code, algorithm, build, or API changes are needed to make gridoptim faster than the reference package without breaking correctness.",
    )


def fmt_number(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.10f}"


def fmt_value(value: float | None) -> str:
    return "n/a" if value is None else str(value)


def write_outputs(summary: BenchmarkSummary) -> None:
    LOG_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

    lines = [
        "# Benchmark report",
        "",
        f"- Overall status: `{summary.overall_status}`",
        f"- Mode: `{summary.mode}`",
        f"- Repeats: `{summary.repeats}`",
        f"- Equation: `{summary.equation}`",
        "- Grid:",
    ]
    for key, (min_v, max_v, step) in summary.grid_spec.items():
        lines.append(f"  - `{key}`: min={min_v}, max={max_v}, step={step}")

    lines.extend([
        "",
        "## Results",
        "",
        f"### {summary.gridoptim.name}",
        f"- Status: `{summary.gridoptim.status}`",
        f"- Runtime (median seconds): `{fmt_number(summary.gridoptim.runtime_seconds)}`",
        f"- Best value: `{fmt_value(summary.gridoptim.best_value)}`",
        f"- Best params: `{summary.gridoptim.best_params}`",
        f"- Error: `{summary.gridoptim.error}`",
        "",
        f"### {summary.reference.name}",
        f"- Status: `{summary.reference.status}`",
        f"- Runtime (median seconds): `{fmt_number(summary.reference.runtime_seconds)}`",
        f"- Best value: `{fmt_value(summary.reference.best_value)}`",
        f"- Best params: `{summary.reference.best_params}`",
        f"- Error: `{summary.reference.error}`",
        "",
        "## Comparison",
        "",
        f"- Same optimum: `{summary.same_optimum}`",
        f"- Winner: `{summary.winner}`",
        f"- Speed ratio (`reference / gridoptim`): `{summary.speed_ratio_reference_over_gridoptim}`",
        "",
        "## Next Codex instruction",
        "",
        summary.next_codex_action,
    ])

    if summary.gridoptim.traceback_text:
        lines.extend([
            "",
            "## gridoptim traceback",
            "",
            "```text",
            summary.gridoptim.traceback_text.rstrip(),
            "```",
        ])

    if summary.reference.traceback_text:
        lines.extend([
            "",
            "## reference traceback",
            "",
            "```text",
            summary.reference.traceback_text.rstrip(),
            "```",
        ])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    gridoptim_result = run_gridoptim()
    reference_result = run_reference()

    same_optimum = (
        not gridoptim_result.error
        and not reference_result.error
        and gridoptim_result.best_value is not None
        and reference_result.best_value is not None
        and math.isclose(gridoptim_result.best_value, reference_result.best_value, abs_tol=ABS_TOL, rel_tol=0.0)
        and compare_params(gridoptim_result.best_params, reference_result.best_params)
    )

    winner, ratio = determine_winner(gridoptim_result, reference_result)
    overall_status, next_codex_action = determine_overall_status(
        gridoptim_result, reference_result, same_optimum, winner
    )

    summary = BenchmarkSummary(
        equation=EQUATION,
        grid_spec=GRID_SPEC,
        repeats=REPEATS,
        mode=MODE,
        gridoptim=gridoptim_result,
        reference=reference_result,
        same_optimum=same_optimum,
        winner=winner,
        speed_ratio_reference_over_gridoptim=ratio,
        overall_status=overall_status,
        next_codex_action=next_codex_action,
    )
    write_outputs(summary)

    print(REPORT_PATH.read_text(encoding="utf-8"))

    if overall_status.startswith("success"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
