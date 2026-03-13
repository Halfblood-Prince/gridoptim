# AGENTS.md

## Objective
Make the local source tree of `gridoptim` faster than the reference implementation in `benchmark.py`, while preserving correctness and the public API.

## Non-negotiable rule
Do not benchmark or import `gridoptim` from PyPI.
Every benchmark run must build and use the package from this repository checkout.

## What Codex must read first on every run
1. `CODEX.md`
2. `MILESTONE.md`
3. `benchmark_report.md` if it exists
4. `benchmark_logs.json` if it exists
5. `benchmark_history.json` if it exists
6. `benchmark_best.json` if it exists

## Required workflow
Follow this order every run.

### Step 1: Inspect state
- Read the latest benchmark outputs.
- Classify the latest state from `overall_status`.
- Check whether the latest run improved on the best prior local result.

### Step 2: Handle failures first
- `failed_build`
  - Fix packaging, extension compilation, dependency installation, include paths, compiler flags, or local install issues.
- `failed_candidate`
  - Fix import errors, API mismatches, runtime exceptions, crashes, or incorrect use of the local package.
- `failed_reference`
  - Fix the benchmark harness or environment so the reference implementation runs successfully.
- `failed_both`
  - Fix environment and harness issues first, then fix package problems.
- `failed_correctness`
  - Fix correctness before performance work. The local package must match the reference optimum within tolerance.

### Step 3: Only then optimise
When the benchmark is successful and `gridoptim` is still slower than the reference or slower than its own prior best result:
1. remove avoidable Python overhead
2. optimise the compiled hot path
3. reduce expression-evaluation cost
4. improve algorithmic pruning or traversal
5. improve build configuration safely

### Step 4: Rebuild and rerun locally
After each meaningful code change:
1. rebuild the local package from this repository
2. run `python benchmark.py`
3. inspect `benchmark_logs.json`
4. inspect `benchmark_report.md`
5. inspect `benchmark_best.json`
6. update `MILESTONE.md`

## Benchmark rules
- `benchmark.py` is the source of truth for performance comparisons.
- It must install the local repository version of `gridoptim` before benchmarking.
- It must never rely on `pip install gridoptim` from an index.
- It must store the latest result, the full history, and the best local result seen so far.
- Do not change the mathematical equation or search grid unless `MILESTONE.md` explicitly says to broaden the benchmark.

## Public API that must remain compatible
- `GridSearchOptimiser.function(expr)`
- `GridSearchOptimiser.set_range(var, min_val, max_val, step)`
- `GridSearchOptimiser.optimise(mode)`

## Success condition
The task is successful only when all of the following are true:
- the package builds from the local repository checkout
- `benchmark.py` benchmarks that local build, not PyPI
- correctness matches the reference within tolerance
- `gridoptim` beats the reference on the canonical benchmark
- `benchmark_best.json` records that as the best local result so far

## Next-run instruction rule
Use this exact decision rule:

> Read the latest benchmark artifacts first. If the latest status is a failure status, fix that failure before attempting optimisation. If the latest benchmark succeeds, continue making code changes that improve the speed of the locally built package and rerun `python benchmark.py` until the best recorded local result improves or the reference is beaten.
