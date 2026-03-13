# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.0915504039999178`
- latest reference runtime: `58.17105120899987`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: fixed benchmark harness execution/import issues, ensured local wheel install is benchmarked, restored API compatibility for `GridSearchOptimiser(expr)` construction, and optimized C++ hot-path grid traversal with mixed-radix increment to reduce per-iteration division/modulo overhead.
- next bottleneck to attack: tinyexpr evaluation cost itself (expression interpreter overhead dominates once index-to-coordinate mapping was optimized).
