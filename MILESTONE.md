# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.919122322000021`
- latest reference runtime: `97.29119190899996`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: raised the build-isolation minimum to `pybind11>=3.0.0`, the official release line that adds Python 3.14 support, so the configured `cp314-*` cibuildwheel target can resolve to a compatible pybind11 during wheel builds; rebuilt from local source, produced a wheel with `python -m build --wheel`, and reran the benchmark workflow.
- next bottleneck to attack: recover the runtime regression from the earlier portability work by improving evaluator throughput in the hot path without depending on machine-specific build flags.
