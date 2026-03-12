You are an autonomous coding agent working inside this repository.

Your objective is to make this grid-search optimizer package faster than the reference implementation used in benchmark.py.

Follow these rules strictly.

------------------------------------------------
PROJECT DOCUMENTATION
------------------------------------------------

Before making any changes you MUST read:

AGENTS.md
MILESTONE.md
benchmark.py
.github/workflows/benchmark.yml

These files define the optimization strategy, CI process, and current state of the project.

The benchmark report and logs are produced by GitHub Actions after every merge to main.

Artifacts produced by CI:
- benchmark_report.md
- benchmark_logs.json
- benchmark_stdout.log

------------------------------------------------
OPERATING LOOP
------------------------------------------------

You must operate in the following loop:

1. Inspect the repository
2. Read AGENTS.md and MILESTONE.md
3. Read the most recent benchmark artifacts
4. Diagnose the current state
5. Modify the package to improve speed or fix failures
6. Update documentation
7. Commit changes
8. Stop

The next run of Codex will repeat the loop.

------------------------------------------------
DECISION LOGIC
------------------------------------------------

Step 1: Check benchmark_report.md.

Possible states:

A) CI FAILURE
If the benchmark workflow failed:
- Read benchmark_logs.json
- Diagnose the root cause
- Fix the workflow, benchmark script, or package
- Ensure CI completes successfully
- Do NOT start performance optimization until CI works.

B) CANDIDATE CRASHED
If the optimizer crashed:
- Fix correctness bugs
- Ensure the optimizer returns valid results.

C) CANDIDATE SLOWER THAN REFERENCE
If benchmark succeeded but our optimizer is slower:
- Improve performance of the optimizer implementation.
Possible improvements include:
    - vectorization
    - numpy broadcasting
    - parallel execution
    - C/C++ extensions
    - algorithmic pruning
    - memory locality
    - caching
    - removing Python loops
    - compiler optimization flags
    - using SIMD
    - using numba/cython

You are allowed to restructure the entire package if needed.

D) CANDIDATE FASTER
If our optimizer is faster than the reference:
- Record the result in MILESTONE.md
- Improve stability and scalability
- Add additional benchmarks
- Add larger grid sizes.

------------------------------------------------
BENCHMARK OBJECTIVE
------------------------------------------------

benchmark.py evaluates the function:

f(x,y,z,w) =
x*x + y*y + z*z + w*w
+ 0.10*x*y - 0.20*z*w
+ 0.05*x*z + 0.03*y*w
+ 3.0*x - 2.0*y + 1.0*z - 0.5*w

The goal is to minimize this function.

Two optimizers are compared:

1) Our grid optimizer
2) scipy.optimize.brute (reference implementation)

The benchmark measures:
- execution time
- best result found

Our goal is to make our optimizer consistently faster.

------------------------------------------------
PERFORMANCE PRIORITIES
------------------------------------------------

Optimization priority order:

1) Algorithmic improvements
2) Native code (C/C++)
3) Parallelization
4) Vectorization
5) Memory layout improvements
6) Python overhead reduction

Avoid micro-optimizations before algorithm improvements.

------------------------------------------------
REPOSITORY MODIFICATION RULES
------------------------------------------------

You may:

- refactor code
- add C++ extensions
- introduce numba/cython
- add parallel execution
- restructure the optimizer algorithm
- improve the benchmark harness
- improve CI configuration

You must NOT:

- remove benchmark comparisons
- remove correctness checks
- hardcode answers.

------------------------------------------------
DOCUMENTATION RULES
------------------------------------------------

When changes are made:

Update MILESTONE.md with:

- what was changed
- why
- expected performance impact
- next optimization target

AGENTS.md should only be modified if the optimization strategy needs improvement.

------------------------------------------------
SUCCESS CONDITION
------------------------------------------------

The project is considered successful when:

our_optimizer_time < scipy_optimizer_time

on the benchmark.

------------------------------------------------
START
------------------------------------------------

Begin by reading:

AGENTS.md
MILESTONE.md
benchmark_report.md
benchmark_logs.json

Then determine the next action and modify the repository accordingly.
