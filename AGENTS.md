# AGENTS.md

## Objective
Make `gridoptim` faster than the benchmark reference package on the canonical benchmark defined in `benchmark.py`, while preserving correctness and API stability.

## First rule
Before making any code changes, read the latest `benchmark_report.md` and `benchmark_logs.json` from GitHub Actions.

- If the latest status is `failed_setup`, `failed_candidate`, `failed_reference`, `failed_both`, or `failed_correctness`, fix that failure first.
- Do **not** start performance work until the benchmark completes successfully for both implementations and the optimum matches.
- Only when status is `success_candidate_slower` should you focus purely on speed.

## Ground rules for Codex
1. Treat `benchmark.py` as the source of truth for performance comparisons.
2. Do not change the mathematical equation, the benchmark search ranges, or the reporting format unless `MILESTONE.md` explicitly says to do so.
3. Keep public Python API compatibility for:
   - `GridSearchOptimiser.function(expr)`
   - `GridSearchOptimiser.set_range(var, min_val, max_val, step)`
   - `GridSearchOptimiser.optimise(mode)`
4. Prefer changes that improve actual runtime over cosmetic refactors.
5. Every optimisation change must keep numerical correctness on the benchmark and on at least one smaller sanity-check problem.
6. After each change, run `python benchmark.py` and update `MILESTONE.md` with the newest result.

## Mandatory execution order
Follow this order every run.

### Step 1: Inspect state
1. Read `benchmark_report.md`.
2. Read `benchmark_logs.json`.
3. Classify the latest state using `overall_status`.

### Step 2: Handle failure states first
- `failed_setup`
  - Fix CI, build flags, compiler availability, package installation, Python version issues, missing dependencies, path problems, or benchmark invocation errors.
- `failed_candidate`
  - Fix `gridoptim` import errors, extension build failures, API mismatches, crashes, or runtime exceptions.
- `failed_reference`
  - Fix benchmark harness or environment issues so `scipy.optimize.brute` runs successfully.
- `failed_both`
  - Fix the environment and benchmark harness first, then fix package/runtime issues.
- `failed_correctness`
  - Fix correctness before speed. `gridoptim` must match the reference optimum within tolerance.

### Step 3: Only then optimise
When `overall_status` is `success_candidate_slower`, improve speed in this order:
1. remove avoidable Python overhead
2. optimise the C++ hot loop
3. reduce expression-evaluation cost
4. improve build configuration safely

### Step 4: Record the outcome
After each meaningful change:
1. run `python benchmark.py`
2. inspect `benchmark_logs.json`
3. inspect `benchmark_report.md`
4. update `MILESTONE.md`
5. choose the next bottleneck and repeat

## Performance strategy

### Remove avoidable Python overhead
- Keep all hot-path computation inside compiled code.
- Avoid per-point Python callbacks, Python object allocation, or repeated Python/C++ boundary crossings.
- Precompute anything that does not change during the search.

### Optimise the C++ hot loop
Focus on these first:
- reduce work inside the innermost evaluation loop
- avoid repeated allocations and copies
- avoid rebuilding data structures per point
- reduce branching where possible
- keep thread-local state local
- minimise synchronization in OpenMP regions

Concrete ideas to try:
- return C++ tuples/lists directly instead of Python dict-heavy structures in the hot path
- avoid copying `vars` into `best_point` unnecessarily
- store best index and reconstruct coordinates once at the end
- precompute counts and strides for index decoding
- use `size_t`/`int64_t` consistently to avoid conversions
- use static scheduling in OpenMP when it improves throughput
- reduce critical-section work to a final thread-local reduction

### Reduce expression-evaluation cost
The current engine uses `tinyexpr`.
Investigate whether speed improves by:
- compiling the expression once per thread only
- minimizing variable indirection
- specializing the benchmark equation if a fast path can be added without breaking the general API
- caching parsed expressions when the same optimizer instance is reused

Do not remove the generic expression path unless there is an equally capable replacement.

### Improve build configuration safely
Investigate compiler options that are portable in CI:
- keep `-O3`
- add `-ffast-math` only if correctness remains acceptable for benchmark and sanity checks
- keep OpenMP enabled where available
- avoid machine-specific flags that break wheel portability

## Required success condition
The task is complete only when all of the following are true:
- `benchmark.py` runs successfully in CI
- GitHub Actions uploads benchmark artifacts even on failure
- `gridoptim` returns the same optimum as the reference within tolerance
- `gridoptim` is faster than the reference package on the benchmark

## Next-run instruction template
Use this exact decision rule:

> Read `benchmark_report.md` and `benchmark_logs.json` first. If the latest status is a failure status, fix that failure before attempting optimisation. If the latest status is `success_candidate_slower`, do whatever code changes are needed to make `gridoptim` faster than the reference package in `benchmark.py`, without breaking correctness or the public API.
