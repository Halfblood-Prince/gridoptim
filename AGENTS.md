# AGENTS.md

## Objective
Make `gridoptim` faster than the benchmark reference package on the canonical benchmark defined in `benchmark.py`, while preserving correctness and API stability.

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

## Performance strategy
Follow these steps in order.

### Step 1: Establish a working baseline
- Ensure the package builds and imports cleanly.
- Ensure `GridSearchOptimiser.optimise()` returns `(best_value, best_params_dict)`.
- Run `python benchmark.py`.
- Record the outcome in `MILESTONE.md`.

### Step 2: Remove avoidable Python overhead
- Keep all hot-path computation inside compiled code.
- Avoid per-point Python callbacks, Python object allocation, or repeated Python/C++ boundary crossings.
- Precompute anything that does not change during the search.

### Step 3: Optimise the C++ hot loop
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

### Step 4: Reduce expression-evaluation cost
The current engine uses `tinyexpr`.
Investigate whether speed improves by:
- compiling the expression once per thread only
- minimizing variable indirection
- specializing the benchmark equation if a fast path can be added without breaking the general API
- caching parsed expressions when the same optimizer instance is reused

Do not remove the generic expression path unless there is an equally capable replacement.

### Step 5: Improve build configuration safely
Investigate compiler options that are portable in CI:
- keep `-O3`
- add `-ffast-math` only if correctness remains acceptable for benchmark and sanity checks
- keep OpenMP enabled where available
- avoid machine-specific flags that break wheel portability

### Step 6: Benchmark-driven loop
After every meaningful code change:
1. run `python benchmark.py`
2. inspect `benchmark_logs.json`
3. inspect `benchmark_report.md`
4. update `MILESTONE.md`
5. choose the next bottleneck and repeat

## Required success condition
The task is complete only when all of the following are true:
- `benchmark.py` runs successfully in CI
- GitHub Actions uploads benchmark artifacts
- `gridoptim` returns the same optimum as the reference within tolerance
- `gridoptim` is faster than the reference package on the benchmark

## If gridoptim is still slower
On the next Codex run, the instruction is:

> Do whatever code changes are needed to make `gridoptim` faster than the reference package in `benchmark.py`, without breaking correctness or the public API. Start by reading `MILESTONE.md`, then run the benchmark, identify the bottleneck, implement the fastest safe improvement, and update the milestone.
