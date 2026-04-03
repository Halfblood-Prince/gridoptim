#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Any
from gridoptim import GridSearchOptimiser


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


def benchmark_gridoptim():
    step = 20.0 / 64.0

    print("\nRunning gridoptim...")

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
        best_value = float(result[0])
        if isinstance(result[1], dict):
            best_point = [float(result[1][k]) for k in ("x", "y", "z", "w")]

    return elapsed, best_point, best_value


def benchmark_scipy_brute():
    from scipy.optimize import brute

    step = 20.0 / 64.0

    print("\nRunning scipy.brute...")

    ranges = (
        slice(-10.0, 10.0, step),
        slice(-10.0, 10.0, step),
        slice(-10.0, 10.0, step),
        slice(-10.0, 10.0, step),
    )

    start = time.perf_counter()
    best_point = brute(
        objective_numpy,
        ranges,
        finish=None,
        workers=-1,  # use all available CPU cores
    )
    elapsed = time.perf_counter() - start

    best_point = [float(v) for v in best_point]
    best_value = objective_numpy(best_point)

    return elapsed, best_point, best_value


def main():
    gridoptim_time, gridoptim_point, gridoptim_value = benchmark_gridoptim()
    scipy_time, scipy_point, scipy_value = benchmark_scipy_brute()

    print("\nBenchmark results")
    print("=================")

    print(f"gridoptim time:    {gridoptim_time:.6f} seconds")
    print(f"gridoptim point:   {gridoptim_point}")
    print(f"gridoptim value:   {gridoptim_value}\n")

    print(f"scipy.brute time:  {scipy_time:.6f} seconds")
    print(f"scipy.brute point: {scipy_point}")
    print(f"scipy.brute value: {scipy_value}\n")

    if gridoptim_value is not None:
        same_result = abs(gridoptim_value - scipy_value) <= 1e-9
        print(f"same optimum value: {same_result}")

    if scipy_time > 0:
        print(f"gridoptim / scipy.brute time ratio: {scipy_time / gridoptim_time:.6f}")


if __name__ == "__main__":
    main()
