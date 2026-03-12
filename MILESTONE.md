# MILESTONE.md

## Project status
This repository now has:
- a benchmark script at `benchmark.py`
- a CI workflow at `.github/workflows/benchmark.yml`
- benchmark artifacts written to:
  - `benchmark_logs.json`
  - `benchmark_report.md`
- an execution guide for Codex in `AGENTS.md`

## Current checkpoint
Initial checkpoint created.
The immediate goal is to establish a trustworthy benchmark baseline on CI and locally.

## Definition of done
`gridoptim` is considered performance-ready when:
1. the package builds successfully in CI
2. `benchmark.py` completes successfully
3. benchmark artifacts are produced and uploaded by GitHub Actions
4. `gridoptim` finds the same optimum as the reference package within tolerance
5. `gridoptim` is faster than the reference package

## Next actions for Codex
1. Build and run `python benchmark.py`.
2. Inspect whether `gridoptim` is functionally correct.
3. If there is any API or binding bug preventing the benchmark from running, fix that first.
4. Compare `gridoptim` runtime against the reference runtime.
5. If `gridoptim` is slower, optimize the hottest compiled-code path first.
6. Update this file with:
   - latest runtimes
   - winner
   - correctness status
   - next bottleneck to address

## Update template
When Codex finishes a run, replace this section with concrete numbers.

### Latest benchmark result
- timestamp: not yet run
- gridoptim runtime: not yet run
- reference runtime: not yet run
- speed ratio (`reference / gridoptim`): not yet run
- same optimum: not yet run
- winner: not yet run

### Bottleneck hypothesis
- not yet assessed

### Next change to attempt
- fix correctness and benchmark execution first, then optimize the C++ inner loop
