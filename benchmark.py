```python
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


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "benchmark_state.json"
LOG_PATH = ROOT / "benchmark_logs.json"
REPORT_PATH = ROOT / "benchmark_report.md"
HISTORY_PATH = ROOT / "benchmark_history.json"


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
        x * x + y * y + z * z + w * w
        + 0.10 * x * y - 0.20 * z * w
        + 0.05 * x * z + 0.03 * y * w
        + 3.0 * x - 2.0 * y + 1.0 * z - 0.5 * w
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
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def to_float_list(value: Any) -> list[float] | None:
    try:
        return [float(v) for v in value]
    except Exception:
        return None


def benchmark_candidate() -> dict[str, Any]:
    try:
        from gridoptim import GridSearchOptimiser

        optimiser = GridSearchOptimiser(objective_expr())
        optimiser.set_range("x", -10.0, 10.0, 64)
        optimiser.set_range("y", -10.0, 10.0, 64)
        optimiser.set_range("z", -10.0, 10.0, 64)
        optimiser.set_range("w", -10.0, 10.0, 64)

        start = time.perf_counter()
        result = optimiser.optimise("min")
        elapsed = time.perf_counter() - start

        best_point = None
        best_value = None

        if isinstance(result, dict):
            best_point = (
                to_float_list(result.get("best_point"))
                or to_float_list(result.get("point"))
                or to_float_list(result.get("x"))
            )
            best_value = (
                safe_float(result.get("best_value"))
                or safe_float(result.get("value"))
                or safe_float(result.get("fun"))
            )
        elif isinstance(result, (list, tuple)):
            if len(result) >= 1:
                best_point = to_float_list(result[0])
            if len(result) >= 2:
                best_value = safe_float(result[1])

        if best_point is None and hasattr(optimiser, "best_values"):
            maybe = getattr(optimiser, "best_values")
            if isinstance(maybe, dict):
                try:
                    best_point = [
                        float(maybe["x"]),
                        float(maybe["y"]),
                        float(maybe["z"]),
                        float(maybe["w"]),
                    ]
                except Exception:
                    pass

        if best_value is None and best_point is not None and len(best_point) == 4:
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

        best_point = to_float_list(best_point)
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


def update_state(candidate: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    old_state = load_json(
        STATE_PATH,
        {
            "status": "not_run_yet",
            "latest": {
                "candidate_seconds": None,
                "reference_seconds": None,
                "ratio_vs_reference": None,
            },
            "best": {
                "candidate_seconds": None,
                "reference_seconds": None,
                "ratio_vs_reference": None,
            },
            "competitor_beaten": False,
            "target": {
                "type": "beat_reference",
                "goal_ratio_below": 1.0,
                "goal_candidate_seconds_below": None,
            },
            "history_count": 0,
            "next_action": "Run benchmark.py, then optimize the repository package.",
        },
    )

    candidate_time = candidate.get("elapsed_seconds")
    reference_time = reference.get("elapsed_seconds")

    ratio = None
    if candidate_time is not None and reference_time not in (None, 0):
        ratio = candidate_time / reference_time

    best = old_state.get("best", {})
    best_candidate = best.get("candidate_seconds")

    if candidate["status"] != "success":
        status = "candidate_failed"
        competitor_beaten = bool(old_state.get("competitor_beaten", False))
        target = {
            "type": "fix_candidate",
            "goal_ratio_below": None,
            "goal_candidate_seconds_below": None,
        }
        next_action = "Fix the local package so benchmark.py can run the candidate benchmark successfully."
    elif reference["status"] != "success":
        status = "reference_failed"
        competitor_beaten = bool(old_state.get("competitor_beaten", False))
        target = {
            "type": "fix_reference",
            "goal_ratio_below": None,
            "goal_candidate_seconds_below": None,
        }
        next_action = "Fix the SciPy reference benchmark or the benchmark harness."
    else:
        competitor_beaten = candidate_time < reference_time

        if best_candidate is None or candidate_time < best_candidate:
            best_candidate = candidate_time
            best_reference = reference_time
            best_ratio = ratio
        else:
            best_reference = best.get("reference_seconds")
            best_ratio = best.get("ratio_vs_reference")

        if competitor_beaten:
            status = "candidate_faster"
            target = {
                "type": "beat_previous_best",
                "goal_ratio_below": best_ratio,
                "goal_candidate_seconds_below": best_candidate,
            }
            next_action = (
                "Competitor already beaten. Make the next iteration faster than the previous best candidate run."
            )
        else:
            status = "candidate_slower"
            target = {
                "type": "beat_reference",
                "goal_ratio_below": 1.0,
                "goal_candidate_seconds_below": reference_time,
            }
            next_action = "Optimize the package until it beats the SciPy reference benchmark."

        best = {
            "candidate_seconds": best_candidate,
            "reference_seconds": best_reference,
            "ratio_vs_reference": best_ratio,
        }

        state = {
            "status": status,
            "latest": {
                "candidate_seconds": candidate_time,
                "reference_seconds": reference_time,
                "ratio_vs_reference": ratio,
            },
            "best": best,
            "competitor_beaten": competitor_beaten
            or bool(old_state.get("competitor_beaten", False)),
            "target": target,
            "history_count": int(old_state.get("history_count", 0)) + 1,
            "next_action": next_action,
        }
        return state

    state = {
        "status": status,
        "latest": {
            "candidate_seconds": candidate_time,
            "reference_seconds": reference_time,
            "ratio_vs_reference": ratio,
        },
        "best": old_state.get("best", {}),
        "competitor_beaten": competitor_beaten,
        "target": target,
        "history_count": int(old_state.get("history_count", 0)) + 1,
        "next_action": next_action,
    }
    return state


def update_history(entry: dict[str, Any]) -> None:
    history = load_json(HISTORY_PATH, [])
    if not isinstance(history, list):
        history = []
    history.append(entry)
    save_json(HISTORY_PATH, history)


def write_report(state: dict[str, Any], candidate: dict[str, Any], reference: dict[str, Any]) -> None:
    lines = [
        "# Benchmark Report",
        "",
        f"Status: `{state['status']}`",
        "",
        "## Latest",
        f"- candidate_seconds: `{state['latest']['candidate_seconds']}`",
        f"- reference_seconds: `{state['latest']['reference_seconds']}`",
        f"- ratio_vs_reference: `{state['latest']['ratio_vs_reference']}`",
        "",
        "## Best",
        f"- best_candidate_seconds: `{state['best'].get('candidate_seconds')}`",
        f"- best_reference_seconds: `{state['best'].get('reference_seconds')}`",
        f"- best_ratio_vs_reference: `{state['best'].get('ratio_vs_reference')}`",
        "",
        f"competitor_beaten: `{state['competitor_beaten']}`",
        "",
        "## Target",
        f"- type: `{state['target']['type']}`",
        f"- goal_ratio_below: `{state['target']['goal_ratio_below']}`",
        f"- goal_candidate_seconds_below: `{state['target']['goal_candidate_seconds_below']}`",
        "",
        "## Next action",
        state["next_action"],
        "",
        "## Candidate result",
        f"- status: `{candidate['status']}`",
        f"- elapsed_seconds: `{candidate['elapsed_seconds']}`",
        f"- best_point: `{candidate['best_point']}`",
        f"- best_value: `{candidate['best_value']}`",
        "",
        "## Reference result",
        f"- status: `{reference['status']}`",
        f"- elapsed_seconds: `{reference['elapsed_seconds']}`",
        f"- best_point: `{reference['best_point']}`",
        f"- best_value: `{reference['best_value']}`",
    ]

    if candidate.get("traceback"):
        lines.extend(["", "## Candidate traceback", "```text", candidate["traceback"], "```"])

    if reference.get("traceback"):
        lines.extend(["", "## Reference traceback", "```text", reference["traceback"], "```"])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    install_scipy_from_pip()
    install_local_package()

    candidate = benchmark_candidate()
    reference = benchmark_reference()

    state = update_state(candidate, reference)

    log_entry = {
        "state": state,
        "candidate": candidate,
        "reference": reference,
    }

    save_json(STATE_PATH, state)
    save_json(LOG_PATH, log_entry)
    update_history(log_entry)
    write_report(state, candidate, reference)

    print(json.dumps(log_entry, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
