# gridoptim

Fast multivariate grid search optimizer for Python with a C++ backend.

gridoptim performs deterministic brute-force optimization of mathematical expressions across multi-dimensional parameter spaces.

The optimizer evaluates every point in a parameter grid and returns the best result according to the chosen optimization mode.

It is designed for:

- mathematical optimization
- parameter sweeps
- research experiments
- simulation calibration
- deterministic hyperparameter exploration

The computation is executed in a compiled C++ core for performance while providing a clean Python API.

# Table of Contents

- Overview
- Features
- Installation
- Quick Start
- Basic Usage
- Expression Syntax
- Optimization Modes
- Examples
- API Reference
- How It Works
- Performance
- Use Cases
- Project Structure
- Development
- FAQ
- Keywords
- Citation
- Author
- License


# Overview

gridoptim is a deterministic optimization library that evaluates a mathematical expression across a grid of parameter values.

The optimizer searches the parameter space by evaluating every possible combination of variable values defined by user-provided ranges.

Unlike probabilistic optimizers, gridoptim guarantees that the global optimum within the defined grid will be found.

# Features

- fast C++ optimization engine
- deterministic brute-force search
- simple Python API
- string-based mathematical expressions
- multi-variable support
- minimal dependencies
- reproducible results

# Installation

Install using pip:

```bash
pip install gridoptim
```

Requirements:
Python 3.10+


# Quick Start

Example optimization problem.

Find the minimum of:

x^2 + y^2

```python
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()

opt.function("x^2 + y^2")
opt.set_range("x", -10, 10, 0.5)
opt.set_range("y", -10, 10, 0.5)
value, params = opt.optimise("min")

print("Best value:", value)
print("Best parameters:", params)
```

Example output:
```
Best value: 0.0
Best parameters: {'x': 0.0, 'y': 0.0}
Basic Usage
```

Optimization in gridoptim follows three steps.

1. Create optimizer
from gridoptim import GridSearchOptimiser

opt = GridSearchOptimiser()
2. Define function

Functions are defined as string expressions.

opt.function("x^2 + y^2")
3. Define parameter ranges

Each variable requires:

minimum value

maximum value

step size
```
opt.set_range("x", -10, 10, 0.5)
opt.set_range("y", -10, 10, 0.5)
```

4. Run optimization
value, params = opt.optimise("min")

or

value, params = opt.optimise("max")
Expression Syntax

Expressions are parsed by the embedded tinyexpr mathematical parser.

Supported operations include:

+  -  *  /  ^

Supported functions include common math operations such as:

sin
cos
tan
log
sqrt
exp
abs

Example:

sin(x) + cos(y) + x^2
Optimization Modes

gridoptim supports two optimization modes.

Minimize
optimise("min")

Finds the smallest value of the expression.

Maximize
optimise("max")

Finds the largest value of the expression.

Examples
Example 1 — Quadratic Minimum
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
Example 2 — Maximum of a Function
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
Example 3 — 3-Variable Optimization
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
API Reference
GridSearchOptimiser

Main optimization class.

Create optimizer
opt = GridSearchOptimiser()
function(expr)

Sets the mathematical expression to optimize.

Parameters:

expr : str

Example:

opt.function("x^2 + y^2")
set_range(var, min_val, max_val, step)

Defines the search range for a variable.

Parameters:

var : variable name
min_val : minimum value
max_val : maximum value
step : step size

Example:

opt.set_range("x", -10, 10, 0.1)
optimise(mode)

Runs the grid search.

Parameters:

mode : "min" or "max"

Returns:

(best_value, best_parameter_dict)

Example:

value, params = opt.optimise("min")
How It Works

gridoptim evaluates the expression at every point in the grid defined by parameter ranges.

Example grid:

x: -10 → 10 step 1
y: -10 → 10 step 1

Total evaluations:

21 × 21 = 441

The C++ backend performs the iteration and expression evaluation.

This significantly reduces Python overhead.

Performance

Grid search complexity grows exponentially with variables.

Example:

3 variables
100 steps each

Total evaluations:

100 × 100 × 100 = 1,000,000

Because the heavy computation runs in C++, gridoptim can handle large evaluation counts efficiently.

Use Cases

gridoptim can be used for:

mathematical optimization

parameter sweeps

research experiments

simulation calibration

brute-force optimization

algorithm benchmarking

Project Structure
src/gridoptim/
    __init__.py
    gridoptim.py

cpp/
    gridoptim_core.cpp
    tinyexpr.c
    tinyexpr.h

pyproject.toml
setup.py
Development

Clone repository:

git clone https://github.com/Halfblood-Prince/gridoptim.git

Install locally:

pip install -e .

---
# FAQ
What is gridoptim?

gridoptim is a Python library for deterministic grid search optimization of mathematical expressions.

Does gridoptim support multiple variables?

Yes. You can define ranges for any number of variables.

Can it maximize functions?

Yes. Use:

optimise("max")
Does gridoptim support arbitrary Python functions?

No. It evaluates string expressions using a mathematical expression parser.

Why use string expressions?

String expressions allow the C++ backend to evaluate functions directly without Python overhead.

# Keywords

grid search optimization
python grid search library
mathematical optimization python
parameter sweep python
deterministic optimization
multivariate grid search
scientific parameter optimization

# Citation

If you use gridoptim in research please cite:

gridoptim: Fast multivariate grid search optimizer
https://github.com/Halfblood-Prince/gridoptim

---

# Author

Akhil Shimna Kumar

---

# License

See LICENSE file for details.
