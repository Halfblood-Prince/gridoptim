from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, Tuple

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
    runtime_seconds: float
    best_value: float
    best_params: Dict[str, float]
    error: str | None = None


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
    start = time.perf_counter()
    try:
        from gridoptim import GridSearchOptimiser

        durations: List[float] = []
        best_value = math.nan
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
        )
    except Exception as exc:
        return BenchmarkResult(
            name="gridoptim",
            runtime_seconds=time.perf_counter() - start,
            best_value=math.nan,
            best_params={},
            error=f"{type(exc).__name__}: {exc}",
        )


def run_reference() -> BenchmarkResult:
    start = time.perf_counter()
    try:
        from scipy import optimize

        bounds = [slice(v[0], v[1] + v[2], v[2]) for v in GRID_SPEC.values()]

        def func(point: Tuple[float, float, float, float]) -> float:
            x, y, z, w = point
            return objective_values(float(x), float(y), float(z), float(w))

        durations: List[float] = []
        best_value = math.nan
        best_params: Dict[str, float] = {}

        for _ in range(REPEATS):
            t0 = time.perf_counter()
            result = optimize.brute(func, bounds, full_output=True, finish=None)
            durations.append(time.perf_counter() - t0)
            best_point, best_value, _, _ = result
            best_params = {
                key: float(best_point[i])
                for i, key in enumerate(GRID_SPEC.keys())
            }
            best_value = float(best_value)

        runtime = statistics.median(durations)
        return BenchmarkResult(
            name="scipy.optimize.brute",
            runtime_seconds=runtime,
            best_value=best_value,
            best_params=best_params,
        )
    except Exception as exc:
        return BenchmarkResult(
            name="scipy.optimize.brute",
            runtime_seconds=time.perf_counter() - start,
            best_value=math.nan,
            best_params={},
            error=f"{type(exc).__name__}: {exc}",
        )


def determine_winner(gridoptim_result: BenchmarkResult, reference_result: BenchmarkResult) -> tuple[str, float | None]:
    if gridoptim_result.error and reference_result.error:
        return "no winner", None
    if gridoptim_result.error:
        return reference_result.name, None
    if reference_result.error:
        return gridoptim_result.name, None

    ratio = reference_result.runtime_seconds / gridoptim_result.runtime_seconds
    winner = gridoptim_result.name if gridoptim_result.runtime_seconds < reference_result.runtime_seconds else reference_result.name
    return winner, ratio


def write_outputs(summary: BenchmarkSummary) -> None:
    LOG_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

    lines = [
        "# Benchmark report",
        "",
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
        f"- Runtime (median seconds): `{summary.gridoptim.runtime_seconds:.10f}`",
        f"- Best value: `{summary.gridoptim.best_value}`",
        f"- Best params: `{summary.gridoptim.best_params}`",
        f"- Error: `{summary.gridoptim.error}`",
        "",
        f"### {summary.reference.name}",
        f"- Runtime (median seconds): `{summary.reference.runtime_seconds:.10f}`",
        f"- Best value: `{summary.reference.best_value}`",
        f"- Best params: `{summary.reference.best_params}`",
        f"- Error: `{summary.reference.error}`",
        "",
        "## Comparison",
        "",
        f"- Same optimum: `{summary.same_optimum}`",
        f"- Winner: `{summary.winner}`",
        f"- Speed ratio (`reference / gridoptim`): `{summary.speed_ratio_reference_over_gridoptim}`",
    ])

    if summary.winner != "gridoptim":
        lines.extend([
            "",
            "## Next Codex instruction",
            "",
            "Do whatever modifications are needed to this package repo to make `gridoptim` faster than the reference package in `benchmark.py`, without breaking correctness or the public API.",
        ])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    gridoptim_result = run_gridoptim()
    reference_result = run_reference()

    same_optimum = (
        not gridoptim_result.error
        and not reference_result.error
        and math.isclose(gridoptim_result.best_value, reference_result.best_value, abs_tol=ABS_TOL, rel_tol=0.0)
        and compare_params(gridoptim_result.best_params, reference_result.best_params)
    )

    winner, ratio = determine_winner(gridoptim_result, reference_result)

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
    )
    write_outputs(summary)

    print(REPORT_PATH.read_text(encoding="utf-8"))

    if gridoptim_result.error or reference_result.error or not same_optimum:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
