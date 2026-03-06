from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    from . import _core
except Exception:
    _core = None


@dataclass(frozen=True)
class RangeSpec:
    min_val: float
    max_val: float
    step: float


class GridSearchOptimiser:
    """
    Brute-force grid optimiser:
      - function(expr: str)
      - set_range(var: str, min_val: float, max_val: float, step: float)
      - optimise("min" | "max") -> (best_value, {var: best_var_value})
    """

    def __init__(self):
        self._expr: Optional[str] = None
        self._ranges: Dict[str, RangeSpec] = {}
        self._native = _core.GridOptimCore() if _core is not None else None
        self._dirty = True

    def function(self, expr: str) -> "GridSearchOptimiser":
        if not isinstance(expr, str) or not expr.strip():
            raise ValueError("expr must be a non-empty string")
        self._expr = expr.strip()
        self._dirty = True
        return self

    def set_range(self, var: str, min_val: float, max_val: float, step: float) -> "GridSearchOptimiser":
        if not isinstance(var, str) or not var.strip():
            raise ValueError("var must be a non-empty string")
        min_val = float(min_val)
        max_val = float(max_val)
        step = float(step)

        if step <= 0:
            raise ValueError("step must be > 0")
        if max_val < min_val:
            raise ValueError("max_val must be >= min_val")

        self._ranges[var.strip()] = RangeSpec(min_val, max_val, step)
        self._dirty = True
        return self

    def _sync_native(self) -> Tuple[list[str], list[float], list[float], list[float]]:
        if self._expr is None:
            raise ValueError("No function set. Call function(expr) first.")
        if not self._ranges:
            raise ValueError("No ranges set. Call set_range(...) for variables.")
        if self._native is None:
            raise RuntimeError(
                "C++ core extension not available. Install from source or a wheel with native extension."
            )

        var_names = sorted(self._ranges.keys())
        mins = [self._ranges[v].min_val for v in var_names]
        maxs = [self._ranges[v].max_val for v in var_names]
        steps = [self._ranges[v].step for v in var_names]

        if self._dirty:
            self._native.configure(self._expr, var_names, mins, maxs, steps)
            self._dirty = False

        return var_names, mins, maxs, steps

    def optimise(self, mode: str = "min") -> Tuple[float, Dict[str, float]]:
        mode = mode.lower().strip()
        if mode not in ("min", "max"):
            raise ValueError("mode must be 'min' or 'max'")

        var_names, _, _, _ = self._sync_native()
        best_val, best_point = self._native.optimise(mode)
        best_vars = {v: float(best_point[i]) for i, v in enumerate(var_names)}
        return float(best_val), best_vars
