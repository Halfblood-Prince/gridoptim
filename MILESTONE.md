# MILESTONE.md

## Project status
This repository now has:
- a benchmark script at `benchmark.py`
- a CI workflow at `.github/workflows/benchmark.yml`
- benchmark artifacts written to:
  - `benchmark_logs.json`
  - `benchmark_report.md`
  - `benchmark_stdout.log`
- an execution guide for Codex in `AGENTS.md`

## Current checkpoint
The benchmark runner now imports the installed `gridoptim` package (instead of a potentially unbuilt in-repo package shadowing site-packages), which fixes local/CI false `failed_candidate` results caused by `gridoptim._core` import errors.

## Decision policy for the next Codex run
Read `benchmark_report.md` and `benchmark_logs.json` first, then follow this rule:

- if `overall_status` is `failed_setup`: fix CI, installation, build, or workflow problems first
- if `overall_status` is `failed_candidate`: fix the package import/build/runtime failure first
- if `overall_status` is `failed_reference`: fix the benchmark harness or environment first
- if `overall_status` is `failed_both`: fix environment and package failures before any optimisation
- if `overall_status` is `failed_correctness`: fix correctness before speed
- if `overall_status` is `success_candidate_slower`: optimise until `gridoptim` is faster than the reference package
- if `overall_status` is `success_candidate_faster`: preserve correctness and optionally broaden benchmark coverage

## Definition of done
`gridoptim` is performance-ready when:
1. the package builds successfully in CI
2. `benchmark.py` completes successfully
3. benchmark artifacts are produced and uploaded by GitHub Actions even if the benchmark fails
4. `gridoptim` finds the same optimum as the reference package within tolerance
5. `gridoptim` is faster than the reference package

## Latest benchmark result
- timestamp: 2026-03-12T23:39:00Z
- overall_status: success_candidate_faster
- gridoptim runtime: 0.0030185630 s
- reference runtime: 0.1034547120 s
- speed ratio (`reference / gridoptim`): 34.27283512107244
- same optimum: true
- winner: gridoptim
- root cause fixed this run: reduced C++ hot-loop per-iteration arithmetic by replacing repeated index division/modulus decoding with incremental mixed-radix coordinate updates

## What changed this run
- Updated `cpp/gridoptim_core.cpp` hot loop to assign each thread a contiguous static range and iterate coordinates incrementally, removing repeated `(idx / stride) % count` decoding in the innermost loop.
- Kept thread-local expression compilation and global reduction semantics unchanged to preserve API and result behavior.
- Re-ran `python benchmark.py` and confirmed `success_candidate_faster` with matching optimum.
- Ran an additional 2D sanity check against `scipy.optimize.brute` and confirmed exact optimum/value match.

## Next change to attempt
- Benchmark larger grids to verify the incremental-index loop scales better as total evaluations increase.
- If stable, investigate reducing OpenMP reduction overhead further (e.g., a lock-free final reduction strategy).
