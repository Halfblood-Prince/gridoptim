You are an autonomous coding agent working inside this repository.

Your job is to improve this package by building and benchmarking the local repository version of `gridoptim` inside your own environment.

Never use the PyPI release of `gridoptim` for benchmarking. If the current benchmark flow downloads `gridoptim` via pip from an index, that is a bug and must be fixed.

------------------------------------------------
PRIMARY FILES
------------------------------------------------
Read these first:

- AGENTS.md
- MILESTONE.md
- benchmark.py
- benchmark_report.md if present
- benchmark_logs.json if present
- benchmark_history.json if present
- benchmark_best.json if present

------------------------------------------------
OPERATING LOOP
------------------------------------------------
1. Inspect the current repository state.
2. Read the latest benchmark artifacts.
3. Build and install `gridoptim` from this repository checkout.
4. Run `python benchmark.py` in your environment.
5. Check whether the latest result is correct and faster.
6. Modify the repository to improve the package.
7. Run the benchmark again.
8. Update `MILESTONE.md`.
9. Stop.

The next Codex run repeats this loop.

------------------------------------------------
REQUIRED BENCHMARK BEHAVIOR
------------------------------------------------
`benchmark.py` must:
- build the package from the current repository
- install that local build into the current Codex environment
- benchmark the local build of `gridoptim`
- benchmark the reference implementation on the same equation and grid
- write `benchmark_logs.json`
- write `benchmark_report.md`
- append to `benchmark_history.json`
- update `benchmark_best.json` with the fastest correct local result so far

The benchmark must not depend on GitHub Actions.

------------------------------------------------
DECISION LOGIC
------------------------------------------------
A) BUILD OR INSTALL FAILURE
If the local package cannot be built or installed from this repo:
- fix packaging or extension build issues first
- rerun the benchmark

B) CANDIDATE FAILURE
If the local package builds but fails at runtime:
- fix correctness or runtime errors first
- rerun the benchmark

C) REFERENCE FAILURE
If the reference benchmark fails:
- fix the benchmark harness or environment
- rerun the benchmark

D) CANDIDATE SLOWER
If the benchmark succeeds but the local package is slower than the reference or slower than its own best recorded result:
- optimise further
- rerun the benchmark
- keep iterating until a new best result is obtained

E) CANDIDATE FASTER
If the local package is faster than the reference:
- record the result in `MILESTONE.md`
- look for safe further speedups or larger stress benchmarks

------------------------------------------------
CONSTRAINTS
------------------------------------------------
You may refactor the package, improve packaging, improve the build, change the benchmark harness, and optimise the compiled implementation.

You must not hardcode the benchmark answer.
You must not remove the reference comparison.
You must not benchmark the PyPI package instead of the local checkout.

------------------------------------------------
START
------------------------------------------------
Begin by reading the listed files, then make the repository obey the local-build benchmark loop.
