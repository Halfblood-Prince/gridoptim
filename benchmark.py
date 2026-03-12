#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "benchmark_logs.json"
REPORT_PATH = ROOT / "benchmark_report.md"
HISTORY_PATH = ROOT / "benchmark_history.json"
BEST_PATH = ROOT / "benchmark_best.json"


@dataclass
class RunResult:
    name: str
    status: str
    elapsed_seconds: float | None
    best_point: list[float] | None
    best_value: float | None
    error: str | None
    traceback: str | None


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def install_scipy_from_pip() -> None:
    try:
        import scipy  # noqa: F401
        return
    except Exception:
        pass

    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_cmd([sys.executable, "-m", "pip", "install", "scipy"])


def install_local_package() -> None:
    """
    Install the package from the current repository checkout.
    This must never install gridoptim from PyPI.
    """
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_cmd(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            str(ROOT),
        ]
    )
    importlib.invalidate_caches()


def objective_values(x: float, y: float, z: float, w: float) -> float:
    return (
        x * x + y * y + z * z + w * w
        + 0.10 * x * y - 0.20 * z * w
        + 0.05 * x * z + 0.03 * y * w
        + 3.0 * x - 2.0 * y + 1.0 * z - 0.5 * w
    )


def objective_vector(v: Any) -> float:
    x, y, z, w = v
    return objective_values(float(x), float(y), float(z), float(w))


def _to_float_list(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    try:
        return [float(v) for v in list(value)]
    except Exception:
        return None


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def benchmark_candidate() -> RunResult:
    try:
        module = importlib.import_module("gridoptim")

        # Adapt this block if your package exposes a different API.
        # Preferred expected shape:
        #   gridoptim.optimize(func, bounds=[...], grid_size=..., minimize=True)
        start = time.perf_counter()

        result = module.optimise(
            objective_values,
            bounds=[(-10.0, 10.0)] * 4,
            grid_size=64,
            minimize=True,
        )

        elapsed = time.perf_counter() - start

        best_point = None
        best_value = None

        if isinstance(result, dict):
            best_point = _to_float_list(
                result.get("best_point")
                or result.get("x")
                or result.get("point")
                or result.get("argmin")
            )
            best_value = _safe_float(
                result.get("best_value")
                or result.get("fun")
                or result.get("value")
                or result.get("minimum")
            )
        else:
            best_point = _to_float_list(getattr(result, "best_point", None))
            if best_point is None:
                best_point = _to_float_list(getattr(result, "x", None))
            if best_point is None and isinstance(result, (list, tuple)) and len(result) >= 1:
                best_point = _to_float_list(result[0])

            best_value = _safe_float(getattr(result, "best_value", None))
            if best_value is None:
                best_value = _safe_float(getattr(result, "fun", None))
            if best_value is None and isinstance(result, (list, tuple)) and len(result) >= 2:
                best_value = _safe_float(result[1])

        if best_value is None and best_point is not None and len(best_point) == 4:
            best_value = objective_values(*best_point)

        if best_point is None or best_value is None:
            raise RuntimeError(
                "Could not extract best_point/best_value from gridoptim.optimize(...) result. "
                "Update benchmark_candidate() to match the package API."
            )

        return RunResult(
            name="candidate",
            status="success",
            elapsed_seconds=elapsed,
            best_point=best_point,
            best_value=best_value,
            error=None,
            traceback=None,
        )
    except Exception as exc:
        return RunResult(
            name="candidate",
            status="error",
            elapsed_seconds=None,
            best_point=None,
            best_value=None,
            error=str(exc),
            traceback=traceback.format_exc(),
        )


def benchmark_reference() -> RunResult:
    try:
        from scipy.optimize import brute

        ranges = (
            slice(-10.0, 10.0, 20.0 / 64.0),
            slice(-10.0, 10.0, 20.0 / 64.0),
            slice(-10.0, 10.0, 20.0 / 64.0),
            slice(-10.0, 10.0, 20.0 / 64.0),
        )

        start = time.perf_counter()
        best_point = brute(objective_vector, ranges, finish=None)
        elapsed = time.perf_counter() - start

        best_point_list = _to_float_list(best_point)
        if best_point_list is None or len(best_point_list) != 4:
            raise RuntimeError("SciPy brute returned an unexpected result.")

        best_value = objective_values(*best_point_list)

        return RunResult(
            name="reference_scipy_brute",
            status="success",
            elapsed_seconds=elapsed,
            best_point=best_point_list,
            best_value=best_value,
            error=None,
            traceback=None,
        )
    except Exception as exc:
        return RunResult(
            name="reference_scipy_brute",
            status="error",
            elapsed_seconds=None,
            best_point=None,
            best_value=None,
            error=str(exc),
            traceback=traceback.format_exc(),
        )


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def compare_results(candidate: RunResult, reference: RunResult) -> str:
    if candidate.status != "success":
        return "failed_candidate"
    if reference.status != "success":
        return "failed_reference"

    assert candidate.elapsed_seconds is not None
    assert reference.elapsed_seconds is not None

    if candidate.elapsed_seconds < reference.elapsed_seconds:
        return "success_candidate_faster"
    return "success_candidate_slower"


def update_history(payload: dict[str, Any]) -> None:
    history = load_json_file(HISTORY_PATH, default=[])
    if not isinstance(history, list):
        history = []
    history.append(payload)
    save_json_file(HISTORY_PATH, history)


def update_best(payload: dict[str, Any]) -> None:
    status = payload.get("status")
    candidate = payload.get("candidate", {})
    reference = payload.get("reference", {})

    if status != "success_candidate_faster":
        if not BEST_PATH.exists():
            save_json_file(
                BEST_PATH,
                {
                    "status": "no_winning_run_yet",
                    "best_candidate_seconds": None,
                    "best_reference_seconds": None,
                    "speedup_vs_reference": None,
                    "run": None,
                },
            )
        return

    cand_t = candidate.get("elapsed_seconds")
    ref_t = reference.get("elapsed_seconds")
    if cand_t is None or ref_t is None:
        return

    current_speedup = ref_t / cand_t if cand_t > 0 else None
    best = load_json_file(BEST_PATH, default=None)

    should_replace = False
    if not isinstance(best, dict):
        should_replace = True
    elif best.get("speedup_vs_reference") is None:
        should_replace = True
    elif current_speedup is not None and current_speedup > float(best["speedup_vs_reference"]):
        should_replace = True

    if should_replace:
        save_json_file(
            BEST_PATH,
            {
                "status": "winning_run",
                "best_candidate_seconds": cand_t,
                "best_reference_seconds": ref_t,
                "speedup_vs_reference": current_speedup,
                "run": payload,
            },
        )


def write_report(payload: dict[str, Any]) -> None:
    candidate = payload["candidate"]
    reference = payload["reference"]
    status = payload["status"]

    lines = [
        "# Benchmark Report",
        "",
        f"## Overall status: `{status}`",
        "",
        "## Candidate (local repo build)",
        "",
        f"- status: `{candidate['status']}`",
        f"- elapsed_seconds: `{candidate['elapsed_seconds']}`",
        f"- best_point: `{candidate['best_point']}`",
        f"- best_value: `{candidate['best_value']}`",
    ]

    if candidate["error"]:
        lines.extend(
            [
                f"- error: `{candidate['error']}`",
                "",
                "```text",
                candidate["traceback"] or "",
                "```",
            ]
        )

    lines.extend(
        [
            "",
            "## Reference (SciPy from pip)",
            "",
            f"- status: `{reference['status']}`",
            f"- elapsed_seconds: `{reference['elapsed_seconds']}`",
            f"- best_point: `{reference['best_point']}`",
            f"- best_value: `{reference['best_value']}`",
        ]
    )

    if reference["error"]:
        lines.extend(
            [
                f"- error: `{reference['error']}`",
                "",
                "```text",
                reference["traceback"] or "",
                "```",
            ]
        )

    lines.extend(["", "## Next action", ""])

    if status == "failed_candidate":
        lines.append(
            "- Fix the local package build/runtime/API so benchmark.py can import and run the repo version successfully."
        )
    elif status == "failed_reference":
        lines.append(
            "- Fix the SciPy reference setup or benchmark harness so the external baseline runs successfully."
        )
    elif status == "success_candidate_slower":
        lines.append(
            "- Optimize the repo package further. Keep benchmarking the local repo build and compare against SciPy."
        )
    elif status == "success_candidate_faster":
        lines.append(
            "- Record this as the current best run, then try larger grids or further stability/performance improvements."
        )
    else:
        lines.append("- Inspect benchmark_logs.json and continue from the latest state.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    install_scipy_from_pip()
    install_local_package()

    candidate = benchmark_candidate()
    reference = benchmark_reference()
    status = compare_results(candidate, reference)

    payload = {
        "status": status,
        "candidate": asdict(candidate),
        "reference": asdict(reference),
        "environment": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
            "cwd": os.getcwd(),
        },
    }

    save_json_file(LOG_PATH, payload)
    update_history(payload)
    update_best(payload)
    write_report(payload)

    print(json.dumps(payload, indent=2, sort_keys=True))

    return 1 if candidate.status != "success" else 0


if __name__ == "__main__":
    raise SystemExit(main())
