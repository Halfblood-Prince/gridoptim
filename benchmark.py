#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any
import importlib

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "benchmark_state.json"
LOG_PATH = ROOT / "benchmark_logs.json"
REPORT_PATH = ROOT / "benchmark_report.md"
HISTORY_PATH = ROOT / "benchmark_history.json"
BEST_PATH = ROOT / "benchmark_best.json"


def run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def install_scipy_from_pip() -> None:
    try:
        import scipy  # noqa: F401
        return
    except Exception:
        run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        run_cmd([sys.executable, "-m", "pip", "install", "scipy"])


def install_local_package() -> None:
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_cmd([sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", str(ROOT)])


def objective_expr() -> str:
    return (
        "x*x + y*y + z*z + w*w "
        "+ 0.10*x*y - 0.20*z*w "
        "+ 0.05*x*z + 0.03*y*w "
        "+ 3.0*x - 2.0*y + 1.0*z - 0.5*w"
    )


def objective_numpy(v: Any) -> float:
    x, y, z, w = v
    return (
        x * x
        + y * y
        + z * z
        + w * w
        + 0.10 * x * y
        - 0.20 * z * w
        + 0.05 * x * z
        + 0.03 * y * w
        + 3.0 * x
        - 2.0 * y
        + 1.0 * z
        - 0.5 * w
    )


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def benchmark_candidate() -> dict[str, Any]:
    try:
        # Ensure we import the installed local wheel, not the in-tree package directory.
        root_str = str(ROOT)
        sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != ROOT]
        importlib.invalidate_caches()
        from gridoptim import GridSearchOptimiser

        step = 20.0 / 64.0
        optimiser = GridSearchOptimiser().function(objective_expr())
        optimiser.set_range("x", -10.0, 10.0, step)
        optimiser.set_range("y", -10.0, 10.0, step)
        optimiser.set_range("z", -10.0, 10.0, step)
        optimiser.set_range("w", -10.0, 10.0, step)

        start = time.perf_counter()
        result = optimiser.optimise("min")
        elapsed = time.perf_counter() - start

        best_point = None
        best_value = None
        if isinstance(result, tuple) and len(result) == 2:
            best_value = safe_float(result[0])
            if isinstance(result[1], dict):
                best_point = [float(result[1][k]) for k in ("x", "y", "z", "w")]
        elif isinstance(result, dict):
            maybe = result.get("best_point")
            if isinstance(maybe, (list, tuple)):
                best_point = [float(v) for v in maybe]
            best_value = safe_float(result.get("best_value"))

        if best_value is None and best_point is not None:
            best_value = objective_numpy(best_point)

        return {
            "name": "candidate",
            "status": "success",
            "elapsed_seconds": elapsed,
            "best_point": best_point,
            "best_value": best_value,
            "error": None,
            "traceback": None,
        }
    except Exception as exc:
        return {
            "name": "candidate",
            "status": "error",
            "elapsed_seconds": None,
            "best_point": None,
            "best_value": None,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def benchmark_reference() -> dict[str, Any]:
    try:
        from scipy.optimize import brute

        step = 20.0 / 64.0
        ranges = (
            slice(-10.0, 10.0, step),
            slice(-10.0, 10.0, step),
            slice(-10.0, 10.0, step),
            slice(-10.0, 10.0, step),
        )

        start = time.perf_counter()
        best_point = brute(objective_numpy, ranges, finish=None)
        elapsed = time.perf_counter() - start

        best_point = [float(v) for v in best_point]
        best_value = objective_numpy(best_point)

        return {
            "name": "reference_scipy_brute",
            "status": "success",
            "elapsed_seconds": elapsed,
            "best_point": best_point,
            "best_value": best_value,
            "error": None,
            "traceback": None,
        }
    except Exception as exc:
        return {
            "name": "reference_scipy_brute",
            "status": "error",
            "elapsed_seconds": None,
            "best_point": None,
            "best_value": None,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def derive_state(candidate: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    old_state = load_json(STATE_PATH, {})
    ratio = None
    if candidate.get("elapsed_seconds") and reference.get("elapsed_seconds"):
        ratio = candidate["elapsed_seconds"] / reference["elapsed_seconds"]

    correctness_ok = False
    c_val = candidate.get("best_value")
    r_val = reference.get("best_value")
    if c_val is not None and r_val is not None:
        correctness_ok = abs(float(c_val) - float(r_val)) <= 1e-9

    if candidate["status"] != "success":
        overall_status = "failed_candidate"
    elif reference["status"] != "success":
        overall_status = "failed_reference"
    elif not correctness_ok:
        overall_status = "failed_correctness"
    elif ratio is not None and ratio < 1.0:
        overall_status = "success_candidate_faster"
    else:
        overall_status = "success_candidate_slower"

    best = old_state.get("best", {"candidate_seconds": None, "reference_seconds": None, "ratio_vs_reference": None})
    if overall_status.startswith("success"):
        best_candidate = best.get("candidate_seconds")
        if best_candidate is None or candidate["elapsed_seconds"] < best_candidate:
            best = {
                "candidate_seconds": candidate["elapsed_seconds"],
                "reference_seconds": reference["elapsed_seconds"],
                "ratio_vs_reference": ratio,
            }

    return {
        "overall_status": overall_status,
        "latest": {
            "candidate_seconds": candidate.get("elapsed_seconds"),
            "reference_seconds": reference.get("elapsed_seconds"),
            "ratio_vs_reference": ratio,
            "correctness_ok": correctness_ok,
        },
        "best": best,
        "competitor_beaten": bool(ratio is not None and ratio < 1.0),
        "history_count": int(old_state.get("history_count", 0)) + 1,
        "next_action": "Fix failures first" if overall_status.startswith("failed") else "Optimise candidate runtime",
    }


def update_history(entry: dict[str, Any]) -> None:
    history = load_json(HISTORY_PATH, [])
    if not isinstance(history, list):
        history = []
    history.append(entry)
    save_json(HISTORY_PATH, history)


def update_best(entry: dict[str, Any]) -> None:
    state = entry["state"]
    if not state["overall_status"].startswith("success"):
        return
    best = load_json(BEST_PATH, {})
    current_best = best.get("candidate_seconds")
    candidate_seconds = state["latest"]["candidate_seconds"]
    if current_best is None or candidate_seconds < current_best:
        save_json(
            BEST_PATH,
            {
                "candidate_seconds": candidate_seconds,
                "reference_seconds": state["latest"]["reference_seconds"],
                "ratio_vs_reference": state["latest"]["ratio_vs_reference"],
                "correctness_ok": state["latest"]["correctness_ok"],
            },
        )


def write_report(entry: dict[str, Any]) -> None:
    s = entry["state"]
    c = entry["candidate"]
    r = entry["reference"]
    lines = [
        "# Benchmark Report",
        "",
        f"overall_status: `{s['overall_status']}`",
        f"candidate_seconds: `{s['latest']['candidate_seconds']}`",
        f"reference_seconds: `{s['latest']['reference_seconds']}`",
        f"ratio_vs_reference: `{s['latest']['ratio_vs_reference']}`",
        f"correctness_ok: `{s['latest']['correctness_ok']}`",
        "",
        "## Candidate",
        f"- status: `{c['status']}`",
        f"- best_point: `{c['best_point']}`",
        f"- best_value: `{c['best_value']}`",
        "",
        "## Reference",
        f"- status: `{r['status']}`",
        f"- best_point: `{r['best_point']}`",
        f"- best_value: `{r['best_value']}`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    install_scipy_from_pip()
    install_local_package()
    candidate = benchmark_candidate()
    reference = benchmark_reference()
    state = derive_state(candidate, reference)
    entry = {"state": state, "candidate": candidate, "reference": reference}
    save_json(STATE_PATH, state)
    save_json(LOG_PATH, entry)
    update_history(entry)
    update_best(entry)
    write_report(entry)
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
