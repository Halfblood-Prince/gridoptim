from __future__ import annotations
from typing import Dict, Tuple
from . import _core


class GridSearchOptimiser:
    def __init__(self):
        self._expr: str | None = None
        self._ranges: Dict[str, Tuple[float, float, float]] = {}

    def function(self, expr: str) -> "GridSearchOptimiser":
        self._expr = expr
        return self

    def set_range(self, var: str, min_val: float, max_val: float, step: float) -> "GridSearchOptimiser":
        if step <= 0:
            raise ValueError("Step must be positive")
        if max_val <= min_val:
            raise ValueError("max_val must be greater than min_val")

        self._ranges[var] = (min_val, max_val, step)
        return self

    def _prepare(self):
        if self._expr is None:
            raise RuntimeError("Function expression not set")

        if not self._ranges:
            raise RuntimeError("No variable ranges defined")

        names = list(self._ranges.keys())
        mins = []
        maxs = []
        steps = []

        for v in names:
            mn, mx, st = self._ranges[v]
            mins.append(mn)
            maxs.append(mx)
            steps.append(st)

        return names, mins, maxs, steps

    def optimise(self, mode: str, optimiser: str = "brute_force"):
        if mode not in ("min", "max"):
            raise ValueError("mode must be 'min' or 'max'")

        names, mins, maxs, steps = self._prepare()

        if optimiser == "brute_force":
            return _core.optimise(self._expr, names, mins, maxs, steps, mode)

        elif optimiser == "adaptive":
            return self._adaptive_search(mode, names, mins, maxs, steps)

        else:
            raise ValueError("Unknown optimiser: " + optimiser)

    def _adaptive_search(self, mode, names, mins, maxs, steps):
        levels = 4

        cur_mins = mins[:]
        cur_maxs = maxs[:]

        best_val = None
        best_point = None

        for level in range(levels):
            scale = 10 ** (levels - level - 1)
            cur_steps = [s * scale for s in steps]

            val, point = _core.optimise(
                self._expr,
                names,
                cur_mins,
                cur_maxs,
                cur_steps,
                mode,
            )

            best_val = val
            best_point = point

            if level == levels - 1:
                break

            new_mins = []
            new_maxs = []

            for i in range(len(names)):
                half_window = cur_steps[i] * 5
                mn = max(mins[i], best_point[i] - half_window)
                mx = min(maxs[i], best_point[i] + half_window)

                new_mins.append(mn)
                new_maxs.append(mx)

            cur_mins = new_mins
            cur_maxs = new_maxs

        return best_val, best_point
