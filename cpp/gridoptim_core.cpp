#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "tinyexpr.h"
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

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
        counts[i] = static_cast<std::int64_t>((maxs[i] - mins[i]) / steps[i]) + 1;
        if (counts[i] <= 0) {
            throw std::runtime_error("computed grid count must be positive");
        }
        strides[i] = total;
        total *= counts[i];
    }

    double global_best = maximise ? -std::numeric_limits<double>::infinity()
                                  : std::numeric_limits<double>::infinity();
    std::int64_t global_best_idx = 0;

#ifdef _OPENMP
#pragma omp parallel
#endif
    {
        std::vector<double> vars(dim);
        std::vector<te_variable> te_vars(dim);
        for (std::size_t i = 0; i < dim; ++i) {
            te_vars[i] = te_variable{names[i].c_str(), &vars[i]};
        }

        int err = 0;
        te_expr* compiled = te_compile(expr.c_str(), te_vars.data(), static_cast<int>(dim), &err);
        if (compiled == nullptr) {
#ifdef _OPENMP
#pragma omp critical
#endif
            {
                throw std::runtime_error("Failed to compile expression with tinyexpr");
            }
        }

        double local_best = maximise ? -std::numeric_limits<double>::infinity()
                                     : std::numeric_limits<double>::infinity();
        std::int64_t local_best_idx = 0;

#ifdef _OPENMP
        const int thread_id = omp_get_thread_num();
        const int thread_count = omp_get_num_threads();
#else
        const int thread_id = 0;
        const int thread_count = 1;
#endif

        const std::int64_t chunk = total / thread_count;
        const std::int64_t extra = total % thread_count;
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
                const double val = te_eval(compiled);
                if ((maximise && val > local_best) || (!maximise && val < local_best)) {
                    local_best = val;
                    local_best_idx = idx;
                }

                // increment mixed-radix position
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

#ifdef _OPENMP
#pragma omp critical
#endif
        {
            if ((maximise && local_best > global_best) || (!maximise && local_best < global_best)) {
                global_best = local_best;
                global_best_idx = local_best_idx;
            }
        }

        te_free(compiled);
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
