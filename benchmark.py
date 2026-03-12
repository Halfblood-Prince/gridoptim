from __future__ import annotations

import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
EQUATION = (
    "x*x + y*y + z*z + w*w "
    "+ 0.10*x*y - 0.20*z*w "
    "+ 0.05*x*z + 0.03*y*w "
    "+ 3.0*x - 2.0*y + 1.0*z - 0.5*w"
)
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
LOCAL_DIST_DIR = PROJECT_ROOT / ".benchmark_dist"
LOG_PATH = PROJECT_ROOT / "benchmark_logs.json"
REPORT_PATH = PROJECT_ROOT / "benchmark_report.md"
HISTORY_PATH = PROJECT_ROOT / "benchmark_history.json"
BEST_PATH = PROJECT_ROOT / "benchmark_best.json"


@dataclass
class BenchmarkResult:
    name: str
    runtime_seconds: float | None
    best_value: float | None
    best_params: Dict[str, float]
    status: str = "not_run"
    error: str | None = None
    traceback_text: str | None = None
    install_source: str | None = None


@dataclass
class BenchmarkSummary:
    timestamp_utc: str
    equation: str
    grid_spec: Dict[str, Tuple[float, float, float]]
    repeats: int
    mode: str
    local_install_source: str
    gridoptim: BenchmarkResult
    reference: BenchmarkResult
    same_optimum: bool
    winner: str
    speed_ratio_reference_over_gridoptim: float | None
    overall_status: str
    next_codex_action: str
    improved_best: bool
    best_candidate_runtime_seconds: float | None


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


def _run_subprocess_json(code: str, cwd: Path, env: Dict[str, str]) -> Dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Subprocess failed with exit code "
            f"{proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


def build_and_install_local_package() -> tuple[bool, str, str | None]:
    try:
        LOCAL_DIST_DIR.mkdir(exist_ok=True)
        for child in LOCAL_DIST_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                shutil.rmtree(child)

        build_cmd = [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(LOCAL_DIST_DIR),
            str(PROJECT_ROOT),
        ]
        build_proc = subprocess.run(build_cmd, cwd=str(PROJECT_ROOT), text=True, capture_output=True)
        if build_proc.returncode != 0:
            return False, "", (
                "Local wheel build failed.\n"
                f"STDOUT:\n{build_proc.stdout}\nSTDERR:\n{build_proc.stderr}"
            )

        wheels = sorted(LOCAL_DIST_DIR.glob("gridoptim-*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not wheels:
            return False, "", "Local wheel build succeeded but no gridoptim wheel was produced."

        wheel_path = wheels[0]
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            str(wheel_path),
        ]
        install_proc = subprocess.run(install_cmd, cwd=str(PROJECT_ROOT), text=True, capture_output=True)
        if install_proc.returncode != 0:
            return False, str(wheel_path), (
                "Local wheel install failed.\n"
                f"STDOUT:\n{install_proc.stdout}\nSTDERR:\n{install_proc.stderr}"
            )

        return True, str(wheel_path), None
    except Exception as exc:
        return False, "", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"


def run_gridoptim(local_install_source: str) -> BenchmarkResult:
    code = f"""
import json, statistics, time, traceback
EQUATION = {EQUATION!r}
GRID_SPEC = {GRID_SPEC!r}
MODE = {MODE!r}
REPEATS = {REPEATS!r}
try:
    from gridoptim import GridSearchOptimiser
    durations = []
    best_value = None
    best_params = {{}}
    for _ in range(REPEATS):
        optimiser = GridSearchOptimiser()
        optimiser.function(EQUATION)
        for var, (min_v, max_v, step) in GRID_SPEC.items():
            optimiser.set_range(var, min_v, max_v, step)
        t0 = time.perf_counter()
        value, params = optimiser.optimise(MODE)
        durations.append(time.perf_counter() - t0)
        best_value = float(value)
        best_params = {{k: float(v) for k, v in params.items()}}
    payload = {{
        "name": "gridoptim",
        "runtime_seconds": statistics.median(durations),
        "best_value": best_value,
        "best_params": best_params,
        "status": "success",
    }}
except Exception as exc:
    payload = {{
        "name": "gridoptim",
        "runtime_seconds": None,
        "best_value": None,
        "best_params": {{}},
        "status": "failed_candidate",
        "error": f"{{type(exc).__name__}}: {{exc}}",
        "traceback_text": traceback.format_exc(),
    }}
print(json.dumps(payload))
"""
    try:
        with tempfile.TemporaryDirectory(prefix="gridoptim-bench-") as tmp:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            payload = _run_subprocess_json(code, Path(tmp), env)
        return BenchmarkResult(install_source=local_install_source, **payload)
    except Exception as exc:
        return BenchmarkResult(
            name="gridoptim",
            runtime_seconds=None,
            best_value=None,
            best_params={},
            status="failed_candidate",
            error=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
            install_source=local_install_source,
        )


def run_reference() -> BenchmarkResult:
    code = f"""
import json, statistics, time, traceback
from scipy import optimize
GRID_SPEC = {GRID_SPEC!r}
REPEATS = {REPEATS!r}
def objective_values(x, y, z, w):
    return (
        x*x + y*y + z*z + w*w
        + 0.10*x*y - 0.20*z*w
        + 0.05*x*z + 0.03*y*w
        + 3.0*x - 2.0*y + 1.0*z - 0.5*w
    )
try:
    bounds = [slice(v[0], v[1] + v[2], v[2]) for v in GRID_SPEC.values()]
    durations = []
    best_value = None
    best_params = {{}}
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        result = optimize.brute(lambda point: objective_values(*point), bounds, full_output=True, finish=None)
        durations.append(time.perf_counter() - t0)
        best_point, best_value, _, _ = result
        best_params = {{key: float(best_point[i]) for i, key in enumerate(GRID_SPEC.keys())}}
        best_value = float(best_value)
    payload = {{
        "name": "scipy.optimize.brute",
        "runtime_seconds": statistics.median(durations),
        "best_value": best_value,
        "best_params": best_params,
        "status": "success",
    }}
except Exception as exc:
    payload = {{
        "name": "scipy.optimize.brute",
        "runtime_seconds": None,
        "best_value": None,
        "best_params": {{}},
        "status": "failed_reference",
        "error": f"{{type(exc).__name__}}: {{exc}}",
        "traceback_text": traceback.format_exc(),
    }}
print(json.dumps(payload))
"""
    try:
        with tempfile.TemporaryDirectory(prefix="reference-bench-") as tmp:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            payload = _run_subprocess_json(code, Path(tmp), env)
        return BenchmarkResult(**payload)
    except Exception as exc:
        return BenchmarkResult(
            name="scipy.optimize.brute",
            runtime_seconds=None,
            best_value=None,
            best_params={},
            status="failed_reference",
            error=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
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
    build_ok: bool,
    gridoptim_result: BenchmarkResult,
    reference_result: BenchmarkResult,
    same_optimum: bool,
    winner: str,
) -> tuple[str, str]:
    if not build_ok:
        return (
            "failed_build",
            "Read benchmark_logs.json first. Fix local packaging, wheel build, or local install issues so this repository can be benchmarked from source before doing optimisation work.",
        )
    if gridoptim_result.status == "failed_candidate" and reference_result.status == "failed_reference":
        return (
            "failed_both",
            "Read benchmark_logs.json first. Fix both the local candidate package and the reference benchmark environment before doing optimisation work.",
        )
    if gridoptim_result.status == "failed_candidate":
        return (
            "failed_candidate",
            "Read benchmark_logs.json first. Fix the locally built gridoptim package, import path, API, or runtime failure. Do not start performance work until the benchmark completes successfully.",
        )
    if reference_result.status == "failed_reference":
        return (
            "failed_reference",
            "Read benchmark_logs.json first. Fix the benchmark harness or environment so scipy.optimize.brute runs successfully. Do not compare performance until both sides complete.",
        )
    if not same_optimum:
        return (
            "failed_correctness",
            "Read benchmark_logs.json and benchmark_report.md first. Fix correctness so the local gridoptim build matches the reference optimum before attempting speed improvements.",
        )
    if winner == "gridoptim":
        return (
            "success_candidate_faster",
            "Gridoptim is currently faster and correct on this benchmark. Preserve correctness, then look for further safe speedups or broader local benchmarks.",
        )
    return (
        "success_candidate_slower",
        "Read benchmark_report.md first, then make whatever code, algorithm, build, or API changes are needed to make the locally built gridoptim package faster than the reference without breaking correctness.",
    )


def load_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def update_history_and_best(summary: BenchmarkSummary) -> tuple[bool, float | None]:
    history = load_json_file(HISTORY_PATH, [])
    history.append(asdict(summary))
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")

    previous_best = load_json_file(BEST_PATH, None)
    latest_runtime = summary.gridoptim.runtime_seconds
    improved_best = False
    best_runtime = None

    is_valid_best = (
        summary.overall_status in {"success_candidate_faster", "success_candidate_slower"}
        and summary.same_optimum
        and latest_runtime is not None
    )

    if previous_best and isinstance(previous_best, dict):
        best_runtime = previous_best.get("gridoptim", {}).get("runtime_seconds")

    if is_valid_best and (best_runtime is None or latest_runtime < best_runtime):
        BEST_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        improved_best = True
        best_runtime = latest_runtime
    elif previous_best is None and is_valid_best:
        BEST_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        improved_best = True
        best_runtime = latest_runtime

    return improved_best, best_runtime


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
        f"- Timestamp (UTC): `{summary.timestamp_utc}`",
        f"- Overall status: `{summary.overall_status}`",
        f"- Mode: `{summary.mode}`",
        f"- Repeats: `{summary.repeats}`",
        f"- Local install source: `{summary.local_install_source}`",
        f"- Improved best result: `{summary.improved_best}`",
        f"- Best candidate runtime so far (seconds): `{fmt_number(summary.best_candidate_runtime_seconds)}`",
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
        f"- Install source: `{summary.gridoptim.install_source}`",
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
    build_ok, local_install_source, build_error = build_and_install_local_package()

    if not build_ok:
        gridoptim_result = BenchmarkResult(
            name="gridoptim",
            runtime_seconds=None,
            best_value=None,
            best_params={},
            status="failed_build",
            error=build_error,
            install_source=local_install_source or str(PROJECT_ROOT),
        )
        reference_result = run_reference()
        same_optimum = False
        winner, ratio = determine_winner(gridoptim_result, reference_result)
    else:
        gridoptim_result = run_gridoptim(local_install_source)
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
        build_ok,
        gridoptim_result,
        reference_result,
        same_optimum,
        winner,
    )

    summary = BenchmarkSummary(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        equation=EQUATION,
        grid_spec=GRID_SPEC,
        repeats=REPEATS,
        mode=MODE,
        local_install_source=local_install_source or str(PROJECT_ROOT),
        gridoptim=gridoptim_result,
        reference=reference_result,
        same_optimum=same_optimum,
        winner=winner,
        speed_ratio_reference_over_gridoptim=ratio,
        overall_status=overall_status,
        next_codex_action=next_codex_action,
        improved_best=False,
        best_candidate_runtime_seconds=None,
    )

    improved_best, best_runtime = update_history_and_best(summary)
    summary.improved_best = improved_best
    summary.best_candidate_runtime_seconds = best_runtime
    write_outputs(summary)

    print(REPORT_PATH.read_text(encoding="utf-8"))
    return 0 if overall_status.startswith("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
