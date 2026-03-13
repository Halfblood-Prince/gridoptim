# MILESTONE.md

- latest status: `success_candidate_faster`
- latest candidate runtime: `1.677763861999665`
- latest reference runtime: `77.79520803499963`
- best recorded candidate runtime: `1.0915504039999178`
- whether correctness matched: `true`
- what changed: tested branch-specialised compare paths plus a dimension-specific (`dim == 4`) mixed-radix increment fast path in the C++ core, and tested non-default native compile flags (`-march=native`, `-fno-math-errno`, `-Ofast`) for the extension build; benchmarked each via local source reinstall and benchmark loop.
- next bottleneck to attack: tinyexpr evaluation still dominates total time; next iteration should focus on reducing expression-evaluation overhead (e.g., fewer indirect loads / tighter evaluator integration) before additional traversal tweaks.
