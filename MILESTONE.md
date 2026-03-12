# MILESTONE.md

## Current objective
The repository must benchmark the locally built checkout of `gridoptim`, not a version downloaded from PyPI.

## Current expected operating model
- Codex builds and installs `gridoptim` from this repository.
- `benchmark.py` runs in Codex's environment.
- The benchmark compares the locally built package against the reference implementation.
- Benchmark outputs are stored in the repository as:
  - `benchmark_logs.json`
  - `benchmark_report.md`
  - `benchmark_history.json`
  - `benchmark_best.json`
- Codex reads those files on the next run and continues optimising.

## Definition of done for this phase
1. `benchmark.py` rebuilds and reinstalls the local package automatically.
2. The candidate benchmark uses the local repo build and never the PyPI package.
3. Benchmark history is persisted across runs.
4. The best correct local result is recorded separately.
5. Codex can use the stored results to decide what to do next.

## Immediate next actions for Codex
1. Verify that `benchmark.py` installs from the local repository path.
2. Verify that local benchmarking does not depend on GitHub Actions.
3. Run the benchmark locally.
4. If the package is slower than the reference, optimise and rerun.
5. Update this file with each material improvement.

## Update template
After each meaningful run, replace this section with:
- latest status
- latest candidate runtime
- latest reference runtime
- best recorded candidate runtime
- whether correctness matched
- what changed
- next bottleneck to attack
