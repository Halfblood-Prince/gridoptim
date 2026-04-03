# gridoptim
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/gridoptim?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=Downloads)](https://pepy.tech/projects/gridoptim)

`gridoptim` is a deterministic multivariate grid-search optimizer for Python with a compiled C++ backend.

It evaluates a mathematical expression across every point in a user-defined parameter grid and returns the best result for either minimization or maximization.

## Features

- Deterministic brute-force optimization
- Fast native C++ core exposed through Python
- Simple string-based expression interface
- Support for multi-variable parameter sweeps
- Reproducible results across runs
- Small public API with minimal setup

## Installation

Install from PyPI:

```bash
pip install gridoptim
```

Requirements:

- Python 3.10+
- A supported build environment if installing from source

## Quick Start

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()

value, params = (
    opt
    .function("x^2 + y^2")
    .set_range("x", -10, 10, 0.5)
    .set_range("y", -10, 10, 0.5)
    .optimise("min")
)

print("Best value:", value)
print("Best parameters:", params)
```

Expected output:

```text
Best value: 0.0
Best parameters: {'x': 0.0, 'y': 0.0}
```

## How It Works

`gridoptim` performs an exhaustive search over all combinations of values produced by the ranges you define.

For example, if you search:

- `x` from `-10` to `10` with step `1`
- `y` from `-10` to `10` with step `1`

the optimizer evaluates `21 x 21 = 441` points.

This guarantees the best result within the grid you specified, unlike probabilistic or heuristic optimizers that may trade certainty for speed.

## Basic Usage

Optimization follows three steps:

1. Create an optimizer.
2. Define the expression to evaluate.
3. Define a range for each variable, then run `optimise("min")` or `optimise("max")`.

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()
opt.function("sin(x) + cos(y) + x^2")
opt.set_range("x", -3.14, 3.14, 0.1)
opt.set_range("y", -3.14, 3.14, 0.1)

value, params = opt.optimise("min")
```

## API

### `GridSearchOptimiser`

Main optimization class.

#### `GridSearchOptimiser(expr: str | None = None)`

Creates a new optimizer. You may optionally provide the expression at construction time.

#### `function(expr: str) -> GridSearchOptimiser`

Sets the mathematical expression to optimize.

```python
opt.function("x^2 + y^2")
```

#### `set_range(var: str, min_val: float, max_val: float, step: float) -> GridSearchOptimiser`

Defines the search range for a variable.

```python
opt.set_range("x", -10, 10, 0.1)
```

Arguments:

- `var`: variable name used in the expression
- `min_val`: lower bound
- `max_val`: upper bound
- `step`: step size, must be greater than `0`

#### `optimise(mode: str = "min") -> tuple[float, dict[str, float]]`

Runs the grid search and returns:

- `best_value`
- `best_parameter_dict`

```python
value, params = opt.optimise("max")
```

Valid modes:

- `"min"` for minimization
- `"max"` for maximization

## Expression Syntax

Expressions are passed as strings and evaluated by the native backend using a lightweight mathematical expression parser.

Supported operators include:

- `+`
- `-`
- `*`
- `/`
- `^`

Common mathematical functions such as `sin`, `cos`, `tan`, `log`, `sqrt`, `exp`, and `abs` are supported.

Example:

```python
opt.function("sin(x) * cos(y) + x^2")
```

## Examples

### Minimize a quadratic

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()

value, params = (
    opt
    .function("x^2 + y^2")
    .set_range("x", -5, 5, 0.1)
    .set_range("y", -5, 5, 0.1)
    .optimise("min")
)

print(value)
print(params)
```

### Maximize a trigonometric expression

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()

value, params = (
    opt
    .function("sin(x) * cos(y)")
    .set_range("x", -3.14, 3.14, 0.01)
    .set_range("y", -3.14, 3.14, 0.01)
    .optimise("max")
)

print(value)
print(params)
```

### Search across three variables

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()

value, params = (
    opt
    .function("x^2 + y^2 + z^2")
    .set_range("x", -10, 10, 1)
    .set_range("y", -10, 10, 1)
    .set_range("z", -10, 10, 1)
    .optimise("min")
)

print(value)
print(params)
```

## Performance Notes

Grid search grows exponentially with the number of variables and the number of steps per variable.

For example:

- 3 variables
- 100 steps per variable

results in `100 x 100 x 100 = 1,000,000` evaluations.

Because the heavy computation is performed in C++, `gridoptim` can handle much larger search spaces than a pure Python implementation, but exhaustive search still becomes expensive as the grid grows.

## Benchmark

Benchmark problem: 4D grid search optimization.

| Optimizer | Time |
|-----------|------|
| gridoptim | **0.821 s** |
| scipy.brute | 89.167 s |

Result:

- Same optimum value
- Same optimum point
- **~108× speedup**

Hardware:
- CPU: Intel i5-12500H
- Python 3.14

## License

See the `LICENSE` file included in this repository for licensing terms.

## Author

Akhil Shimna Kumar
