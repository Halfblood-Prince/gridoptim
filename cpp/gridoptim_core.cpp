#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _OPENMP
  #include <omp.h>
#endif

extern "C" {
#include "tinyexpr.h"
}

namespace py = pybind11;

static inline long long count_steps(double minv, double maxv, double step) {
    if (step <= 0.0) throw std::runtime_error("step must be > 0");
    if (maxv < minv) throw std::runtime_error("max must be >= min");
    const double span = maxv - minv;
    long long n = (long long)std::floor(span / step) + 1;
    return (n < 1) ? 1 : n;
}

py::tuple optimise_cpp(
    const std::string& expr,
    const std::vector<std::string>& var_names,
    const std::vector<double>& mins,
    const std::vector<double>& maxs,
    const std::vector<double>& steps,
    const std::string& mode
) {
    const size_t d = var_names.size();
    if (d == 0) throw std::runtime_error("No variables");
    if (mins.size() != d || maxs.size() != d || steps.size() != d)
        throw std::runtime_error("mins/maxs/steps must match var_names length");

    const bool is_min = (mode == "min");
    const bool is_max = (mode == "max");
    if (!is_min && !is_max) throw std::runtime_error("mode must be 'min' or 'max'");

    // Variable storage used by tinyexpr
    std::vector<double> x(d, 0.0);

    // tinyexpr variable bindings
    std::vector<te_variable> vars;
    vars.reserve(d);
    for (size_t i = 0; i < d; i++) {
        te_variable v;
        v.name = var_names[i].c_str();
        v.address = &x[i];
        v.type = TE_VARIABLE;
        v.context = nullptr;
        vars.push_back(v);
    }

    int err = 0;
    te_expr* compiled = te_compile(expr.c_str(), vars.data(), (int)d, &err);
    if (!compiled) {
        throw std::runtime_error("Failed to compile expression at position " + std::to_string(err));
    }

    // Per-dimension step counts
    std::vector<long long> n(d);
    for (size_t i = 0; i < d; i++) n[i] = count_steps(mins[i], maxs[i], steps[i]);

    // Strides for linear index -> multi-index
    std::vector<long long> stride(d, 1);
    for (size_t i = d; i-- > 1;) {
        stride[i-1] = stride[i] * n[i];
    }
    const long long total = n[0] * stride[0];

    double best_val = is_min ? std::numeric_limits<double>::infinity()
                             : -std::numeric_limits<double>::infinity();
    std::vector<double> best_point(d, 0.0);

    #pragma omp parallel
    {
        double local_best = best_val;
        std::vector<double> local_point(d, 0.0);
        std::vector<double> local_x(d, 0.0);

        // Each thread needs its own compiled expression because tinyexpr uses variable addresses
        // bound to the local_x array.
        std::vector<te_variable> local_vars;
        local_vars.reserve(d);
        for (size_t i = 0; i < d; i++) {
            te_variable v;
            v.name = var_names[i].c_str();
            v.address = &local_x[i];
            v.type = TE_VARIABLE;
            v.context = nullptr;
            local_vars.push_back(v);
        }
        int local_err = 0;
        te_expr* local_compiled = te_compile(expr.c_str(), local_vars.data(), (int)d, &local_err);
        if (!local_compiled) {
            // If compile fails here, something is very wrong (should match earlier compile).
            // Abort by setting a flag; easiest is to throw outside parallel region, but C++ exceptions
            // across OpenMP are messy. We'll just skip work for this thread.
            local_compiled = nullptr;
        }

        #pragma omp for schedule(static)
        for (long long idx = 0; idx < total; idx++) {
            if (!local_compiled) continue;

            long long rem = idx;
            for (size_t i = 0; i < d; i++) {
                const long long qi = rem / stride[i];
                rem = rem % stride[i];
                double v = mins[i] + (double)qi * steps[i];
                // Guard against float rounding beyond max
                if (v > maxs[i]) v = maxs[i];
                local_x[i] = v;
            }

            const double val = te_eval(local_compiled);

            if (is_min) {
                if (val < local_best) {
                    local_best = val;
                    for (size_t i = 0; i < d; i++) local_point[i] = local_x[i];
                }
            } else {
                if (val > local_best) {
                    local_best = val;
                    for (size_t i = 0; i < d; i++) local_point[i] = local_x[i];
                }
            }
        }

        if (local_compiled) te_free(local_compiled);

        #pragma omp critical
        {
            if (is_min) {
                if (local_best < best_val) {
                    best_val = local_best;
                    best_point = local_point;
                }
            } else {
                if (local_best > best_val) {
                    best_val = local_best;
                    best_point = local_point;
                }
            }
        }
    }

    te_free(compiled);
    return py::make_tuple(best_val, best_point);
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "gridoptim C++ core (OpenMP)";
    m.def("optimise", &optimise_cpp,
          py::arg("expr"),
          py::arg("var_names"),
          py::arg("mins"),
          py::arg("maxs"),
          py::arg("steps"),
          py::arg("mode"));
}
