# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.5312948060000053`
- latest reference runtime: `80.03053087999979`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: refactored the `dim == 4` C++ traversal to use OpenMP `for` over the outer dimension with tightly nested loops and contiguous `x` stepping, reducing mixed-radix carry/update overhead in the hot path; rebuilt from local source and reran the benchmark workflow.
- next bottleneck to attack: tinyexpr evaluation still dominates; target evaluator overhead next (e.g., lower-indirection variable access and expression-path simplification for this fixed-size variable set).
