# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.1729467670002123`
- latest reference runtime: `55.408404453`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: ran additional local optimisation experiments on mixed-radix traversal and branch-specialised compare paths, benchmarked each via local wheel installs, then reverted non-improving core-loop variants to preserve the faster baseline implementation.
- next bottleneck to attack: tinyexpr evaluation cost remains dominant; next attempts should focus on reducing expression-evaluation overhead while keeping API/behaviour unchanged.
