#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "tinyexpr.h"
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

namespace {

struct ProgramDeleter {
    void operator()(te_program* p) const {
        te_free_program(p);
    }
};

inline std::int64_t compute_count(double min_v, double max_v, double step) {
    const double width = max_v - min_v;
    const double raw = width / step;
    const double nearest = std::round(raw);
    const double tol = 1e-12 * std::max(1.0, std::fabs(raw));
    const double adjusted = (std::fabs(raw - nearest) <= tol) ? nearest : std::floor(raw + tol);
    const auto count = static_cast<std::int64_t>(adjusted) + 1;
    if (count <= 0) {
        throw std::runtime_error("computed grid count must be positive");
    }
    return count;
}

inline void checked_mul_total(std::int64_t& total, std::int64_t factor) {
    if (factor <= 0) {
        throw std::runtime_error("computed grid count must be positive");
    }
    if (total > std::numeric_limits<std::int64_t>::max() / factor) {
        throw std::runtime_error("grid is too large: total point count overflows int64");
    }
    total *= factor;
}

inline bool better(double candidate, double best, bool maximise) {
    return maximise ? (candidate > best) : (candidate < best);
}

inline double eval_program(const te_program* program, const std::vector<double>& vars) {
    return te_eval_program(program, vars.data());
}

} // namespace

std::pair<double, std::vector<double>> optimise(
    const std::string& expr,
    const std::vector<std::string>& names,
    const std::vector<double>& mins,
    const std::vector<double>& maxs,
    const std::vector<double>& steps,
    bool maximise)
{
    const std::size_t dim = names.size();
    if (mins.size() != dim || maxs.size() != dim || steps.size() != dim) {
        throw std::runtime_error("names, mins, maxs, and steps must have the same length");
    }
    if (dim == 0) {
        throw std::runtime_error("at least one variable is required");
    }

    std::vector<std::int64_t> counts(dim);
    std::vector<std::int64_t> strides(dim);
    std::int64_t total = 1;

    for (std::size_t i = 0; i < dim; ++i) {
        if (steps[i] <= 0.0) {
            throw std::runtime_error("all step values must be > 0");
        }
        if (maxs[i] < mins[i]) {
            throw std::runtime_error("all max values must be >= min values");
        }
        counts[i] = compute_count(mins[i], maxs[i], steps[i]);
        strides[i] = total;
        checked_mul_total(total, counts[i]);
    }

    std::vector<double> compile_vars(dim, 0.0);
    std::vector<te_variable> compile_te_vars(dim);
    for (std::size_t i = 0; i < dim; ++i) {
        compile_te_vars[i] = te_variable{names[i].c_str(), &compile_vars[i], TE_VARIABLE, nullptr};
    }

    int err = 0;
    te_expr* compiled_expr = te_compile(expr.c_str(), compile_te_vars.data(), static_cast<int>(dim), &err);
    if (compiled_expr == nullptr) {
        throw std::runtime_error(
            err > 0 ? ("Failed to compile expression with tinyexpr near character " + std::to_string(err))
                    : "Failed to compile expression with tinyexpr");
    }

    std::unique_ptr<te_expr, decltype(&te_free)> compiled_guard(compiled_expr, &te_free);
    std::unique_ptr<te_program, ProgramDeleter> program(
        te_compile_program(compiled_expr, compile_te_vars.data(), static_cast<int>(dim)));
    if (!program) {
        throw std::runtime_error("Failed to compile tinyexpr program");
    }

#ifdef _OPENMP
    const int thread_count = omp_get_max_threads();
#else
    const int thread_count = 1;
#endif

    std::vector<double> thread_best_values(
        thread_count,
        maximise ? -std::numeric_limits<double>::infinity() : std::numeric_limits<double>::infinity());
    std::vector<std::int64_t> thread_best_indices(thread_count, 0);

#ifdef _OPENMP
#pragma omp parallel
#endif
    {
#ifdef _OPENMP
        const int thread_id = omp_get_thread_num();
        const int active_threads = omp_get_num_threads();
#else
        const int thread_id = 0;
        const int active_threads = 1;
#endif

        std::vector<double> vars(dim);
        double local_best = maximise ? -std::numeric_limits<double>::infinity()
                                     : std::numeric_limits<double>::infinity();
        std::int64_t local_best_idx = 0;

        auto update_best = [&](double val, std::int64_t idx) {
            if (better(val, local_best, maximise)) {
                local_best = val;
                local_best_idx = idx;
            }
        };

        if (dim == 1) {
            const std::int64_t c0 = counts[0];
            const double min0 = mins[0];
            const double step0 = steps[0];
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
            for (std::int64_t p0 = 0; p0 < c0; ++p0) {
                vars[0] = min0 + static_cast<double>(p0) * step0;
                update_best(eval_program(program.get(), vars), p0);
            }
        } else if (dim == 2) {
            const std::int64_t c0 = counts[0];
            const std::int64_t c1 = counts[1];
            const double min0 = mins[0], min1 = mins[1];
            const double step0 = steps[0], step1 = steps[1];
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
            for (std::int64_t p1 = 0; p1 < c1; ++p1) {
                vars[1] = min1 + static_cast<double>(p1) * step1;
                vars[0] = min0;
                const std::int64_t base_idx = p1 * c0;
                for (std::int64_t p0 = 0; p0 < c0; ++p0) {
                    update_best(eval_program(program.get(), vars), base_idx + p0);
                    vars[0] += step0;
                }
            }
        } else if (dim == 3) {
            const std::int64_t c0 = counts[0];
            const std::int64_t c1 = counts[1];
            const std::int64_t c2 = counts[2];
            const double min0 = mins[0], min1 = mins[1], min2 = mins[2];
            const double step0 = steps[0], step1 = steps[1], step2 = steps[2];
#ifdef _OPENMP
#pragma omp for schedule(static)
#endif
            for (std::int64_t p2 = 0; p2 < c2; ++p2) {
                vars[2] = min2 + static_cast<double>(p2) * step2;
                for (std::int64_t p1 = 0; p1 < c1; ++p1) {
                    vars[1] = min1 + static_cast<double>(p1) * step1;
                    vars[0] = min0;
                    const std::int64_t base_idx = (p2 * c1 + p1) * c0;
                    for (std::int64_t p0 = 0; p0 < c0; ++p0) {
                        update_best(eval_program(program.get(), vars), base_idx + p0);
                        vars[0] += step0;
                    }
                }
            }
        } else if (dim == 4) {
            const std::int64_t c0 = counts[0];
            const std::int64_t c1 = counts[1];
            const std::int64_t c2 = counts[2];
            const std::int64_t c3 = counts[3];
            const double min0 = mins[0], min1 = mins[1], min2 = mins[2], min3 = mins[3];
            const double step0 = steps[0], step1 = steps[1], step2 = steps[2], step3 = steps[3];
#ifdef _OPENMP
#pragma omp for collapse(2) schedule(static)
#endif
            for (std::int64_t p3 = 0; p3 < c3; ++p3) {
                for (std::int64_t p2 = 0; p2 < c2; ++p2) {
                    vars[3] = min3 + static_cast<double>(p3) * step3;
                    vars[2] = min2 + static_cast<double>(p2) * step2;
                    for (std::int64_t p1 = 0; p1 < c1; ++p1) {
                        vars[1] = min1 + static_cast<double>(p1) * step1;
                        vars[0] = min0;
                        const std::int64_t base_idx = ((p3 * c2 + p2) * c1 + p1) * c0;
                        for (std::int64_t p0 = 0; p0 < c0; ++p0) {
                            update_best(eval_program(program.get(), vars), base_idx + p0);
                            vars[0] += step0;
                        }
                    }
                }
            }
        } else {
            const std::int64_t chunk = total / active_threads;
            const std::int64_t extra = total % active_threads;
            const std::int64_t begin = thread_id * chunk + (thread_id < extra ? thread_id : extra);
            const std::int64_t span = chunk + (thread_id < extra ? 1 : 0);
            const std::int64_t end = begin + span;

            if (begin < end) {
                std::vector<std::int64_t> pos(dim);
                std::int64_t rem = begin;
                for (std::size_t d = dim; d-- > 0;) {
                    pos[d] = rem / strides[d];
                    rem %= strides[d];
                    vars[d] = mins[d] + static_cast<double>(pos[d]) * steps[d];
                }

                for (std::int64_t idx = begin; idx < end; ++idx) {
                    update_best(eval_program(program.get(), vars), idx);
                    for (std::size_t d = 0; d < dim; ++d) {
                        ++pos[d];
                        vars[d] += steps[d];
                        if (pos[d] < counts[d]) {
                            break;
                        }
                        pos[d] = 0;
                        vars[d] = mins[d];
                    }
                }
            }
        }

        thread_best_values[thread_id] = local_best;
        thread_best_indices[thread_id] = local_best_idx;
    }

    double global_best = thread_best_values[0];
    std::int64_t global_best_idx = thread_best_indices[0];
    for (int i = 1; i < thread_count; ++i) {
        if (better(thread_best_values[i], global_best, maximise)) {
            global_best = thread_best_values[i];
            global_best_idx = thread_best_indices[i];
        }
    }

    std::vector<double> global_point(dim);
    for (std::size_t d = 0; d < dim; ++d) {
        const std::int64_t pos = (global_best_idx / strides[d]) % counts[d];
        global_point[d] = mins[d] + static_cast<double>(pos) * steps[d];
    }

    return std::make_pair(global_best, global_point);
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "gridoptim core";
    m.def("optimise", &optimise, "Run grid search optimisation");
}
