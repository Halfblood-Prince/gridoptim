# CODEX OPERATING INSTRUCTIONS

You are an autonomous coding agent working inside this repository.

Your objective is to improve the performance of the grid search optimizer
implemented in this repository.

## Core rules

1. 
2. Always install `gridoptim` from pip.
3. SciPy must be installed from pip and used as the reference benchmark.
4. Before making any code changes, read `benchmark_state.json`.
5. After making changes, rebuild the package and run `benchmark.py`.
6. After benchmarking, update `benchmark_state.json`.

## Install rules

Use this workflow:

```bash
python -m pip install --upgrade pip
python -m pip install scipy
python -m pip install --no-deps --force-reinstall
```
## Benchmark target rules

Read benchmark_state.json first.

If competitor_beaten is false:

optimize until candidate_seconds < reference_seconds

If competitor_beaten is true:

optimize until candidate_seconds < best.candidate_seconds

the goal is to beat the previous best run of this repository

## Operating loop

- Read benchmark_state.json

- Install SciPy from pip

- Install the local repo package

- Run benchmark.py

Inspect:

- benchmark_state.json

- benchmark_logs.json

- benchmark_report.md

- Improve the optimizer

- Reinstall the local package

- Run benchmark.py again

- Stop

The next Codex run continues the loop.

## Allowed changes

You may:

- refactor the optimizer

- improve algorithms

- remove Python overhead

- add vectorization

- add parallelism

- add native acceleration

- improve memory layout

- improve build configuration
- replace tinyexpr with a faster library as long as the function to be optimised can be defined in the python file in a user-friendly way like normal mathematical espression

You must not:

- hardcode the optimum

- remove the benchmark comparison

- install gridoptim from pip

## Success rules

While the competitor is not yet beaten:

success means beating SciPy

After the competitor has been beaten:

success means improving on the previous best candidate benchmarck
