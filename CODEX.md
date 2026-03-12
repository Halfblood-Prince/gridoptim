# CODEX OPERATING INSTRUCTIONS

You are an autonomous coding agent working inside this repository.

Your objective is to improve the performance of the grid search optimizer
implemented in this repository until it is faster than the reference
implementation used in benchmark.py.

You must operate entirely within the local repository environment.

---

# IMPORTANT RULES

1. NEVER install `gridoptim` from pip.
2. ALWAYS install the package from the current repository checkout.
3. SciPy MUST be installed from pip and used as the reference optimizer.
4. Every modification must be validated using `benchmark.py`.

Correct installation workflow:

pip install --upgrade pip
pip install scipy
pip install --no-deps --force-reinstall .

---

# BENCHMARKING PROCESS

The file `benchmark.py` performs the benchmark comparison.

It compares:

Candidate:
- gridoptim from the current repository build

Reference:
- scipy.optimize.brute installed from pip

The objective function used is:

f(x,y,z,w) =
x*x + y*y + z*z + w*w
+ 0.10*x*y - 0.20*z*w
+ 0.05*x*z + 0.03*y*w
+ 3.0*x - 2.0*y + 1.0*z - 0.5*w

The optimizer must minimize this function.

Benchmark results are written to:

benchmark_logs.json
benchmark_history.json
benchmark_best.json
benchmark_report.md

---

# OPERATING LOOP

Follow this loop on every run:

1. Inspect repository state
2. Read benchmark logs and report
3. Diagnose the current performance
4. Improve the optimizer implementation
5. Rebuild and reinstall the package
6. Run benchmark.py
7. Store results
8. Update MILESTONE.md
9. Stop

The next Codex run will continue the loop.

---

# DIAGNOSTIC PROCESS

First read:

benchmark_report.md
benchmark_logs.json
benchmark_history.json
benchmark_best.json

Possible states:

## Candidate Failure

If the candidate optimizer failed to run:

Fix:
- package installation
- API mismatch
- runtime errors
- missing dependencies

Do not perform performance optimization until the benchmark runs successfully.

## Candidate Slower

If the benchmark succeeded but our optimizer is slower than SciPy:

Improve performance of the optimizer implementation.

Possible improvements include:

Algorithmic improvements
Vectorization
Removing Python loops
Parallel execution
NumPy broadcasting
Memory layout improvements
Caching
SIMD
Numba or Cython
Native C/C++ extensions

Large architectural refactors are allowed.

## Candidate Faster

If the optimizer becomes faster than the reference:

Record the result in MILESTONE.md.

Then attempt further improvements:

larger grids
better scaling
more stable optimization

---

# PERFORMANCE PRIORITIES

Optimization priority order:

1. Algorithmic improvements
2. Native code acceleration
3. Parallel execution
4. Vectorization
5. Memory locality
6. Python overhead reduction

Avoid micro-optimizations until algorithmic improvements are explored.

---

# REPOSITORY MODIFICATION RULES

You may:

refactor code
add new modules
add compiled extensions
introduce numba/cython
parallelize workloads
improve the optimizer algorithm

You must NOT:

remove the benchmark comparison
hardcode the solution
remove correctness validation

---

# SUCCESS CONDITION

The project is successful when:

candidate_time < reference_time

This means the repository optimizer outperforms SciPy's brute-force grid search.

---

# START

Before doing anything:

1. Install dependencies
2. Install the package from this repository
3. Run benchmark.py
4. Analyze the results
5. Improve the optimizer

Continue iterating until the best benchmark result improves.
