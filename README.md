# gridoptim

Fast multivariate grid search optimizer for Python with a high-performance backend.

gridoptim is a lightweight optimization library designed to efficiently evaluate parameter spaces using deterministic grid search. It is useful for machine learning hyperparameter tuning, scientific parameter sweeps, simulation calibration, brute-force optimization problems, and reproducible experiments.

The library provides a simple Python interface while delegating performance-critical operations to a compiled backend for speed.

---

# Table of Contents

- What is gridoptim
- Features
- Installation
- Quick Start
- Core Concepts
- Basic Usage
- Optimization Examples
- Machine Learning Example
- Scientific Computing Example
- API Reference
- Result Object
- Performance Notes
- Best Practices
- Common Use Cases
- Comparison With Other Libraries
- Project Structure
- Development
- FAQ
- Keywords
- Citation
- Author
- License

---

# What is gridoptim

gridoptim is a deterministic optimization library that performs grid search across multiple parameters.

The optimizer evaluates every point in a parameter grid and returns the best performing combination according to an objective function.

Grid search is commonly used when:

- the search space is relatively small
- reproducibility is important
- deterministic exploration is preferred
- the objective function is stable
- brute-force evaluation is acceptable

gridoptim aims to provide a faster and cleaner implementation of this approach.

---

# Features

- simple Python API
- fast grid iteration
- multi-dimensional parameter support
- deterministic optimization
- minimal dependencies
- suitable for research workflows
- works with arbitrary Python objective functions

---

# Installation

Install using pip:

```bash
pip install gridoptim
```

Requirements:
Python ≥ 3.10

---

# Quick Start

Minimal working example.
