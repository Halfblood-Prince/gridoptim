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
- timestamp: 2026-03-12T23:18:24Z
- overall_status: success_candidate_faster
- gridoptim runtime: 0.0009835620 s
- reference runtime: 0.0520154000 s
- speed ratio (`reference / gridoptim`): 52.884719011786906
- same optimum: true
- winner: gridoptim
- root cause fixed this run: local source-tree import shadowed installed wheel and hid compiled extension (`gridoptim._core`)

## What changed this run
- Updated `benchmark.py` to import `gridoptim` with `PROJECT_ROOT` temporarily removed from `sys.path`, ensuring the benchmark executes the installed package and compiled extension.
- Re-ran benchmark and verified both implementations succeed, optimum matches, and candidate is faster.

## Next change to attempt
- Preserve current correctness/performance behavior.
- If future CI runs regress, inspect packaging/install path handling first before tuning hot loops.
