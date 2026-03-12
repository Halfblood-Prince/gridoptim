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
The repo is now set up so benchmark failures are part of the recorded state instead of a dead end.

The workflow should now:
- preserve benchmark artifacts even when the run fails
- upload stdout and pip install logs for debugging
- mark failures explicitly so the next Codex run knows whether to fix CI, fix correctness, or continue performance work

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

## Latest known state
This checkpoint was created before a fresh CI rerun in this environment, so concrete timings are not yet available.

### Expected status categories
- `failed_setup`
- `failed_candidate`
- `failed_reference`
- `failed_both`
- `failed_correctness`
- `success_candidate_slower`
- `success_candidate_faster`

## Next action
Trigger or inspect the next benchmark run on `main`, then update this file with:
- timestamp
- `overall_status`
- gridoptim runtime
- reference runtime
- same optimum
- winner
- root cause if failed
- next bottleneck or next fix

## Update template
### Latest benchmark result
- timestamp: not yet run after failure-handling update
- overall_status: not yet run
- gridoptim runtime: not yet run
- reference runtime: not yet run
- speed ratio (`reference / gridoptim`): not yet run
- same optimum: not yet run
- winner: not yet run
- root cause: not yet run

### Next change to attempt
- inspect the next benchmark artifacts and follow the decision policy above
