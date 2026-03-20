# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.8445626069999435`
- latest reference runtime: `100.53563578199999`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: made the extension build portable by default by removing unconditional `-march=native` and keeping it behind an opt-in `GRIDOPTIM_NATIVE` flag, which should avoid Colab/runtime illegal-instruction crashes while preserving local-source benchmark correctness; rebuilt from local source and reran the benchmark workflow.
- next bottleneck to attack: recover the runtime regression from dropping `-march=native` by improving evaluator throughput in the hot path without reintroducing machine-specific build fragility.
