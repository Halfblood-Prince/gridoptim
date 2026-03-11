#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "tinyexpr.h"
#include <vector>
#include <string>
#include <limits>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace py = pybind11;

py::dict optimise(
    const std::string& expr,
    const std::vector<std::string>& names,
    const std::vector<double>& mins,
    const std::vector<double>& maxs,
    const std::vector<double>& steps,
    bool maximise)
{
    size_t dim = names.size();

    std::vector<int64_t> counts(dim);
    int64_t total = 1;

    for (size_t i = 0; i < dim; i++) {
        counts[i] = (int64_t)((maxs[i] - mins[i]) / steps[i]) + 1;
        total *= counts[i];
    }

    double global_best = maximise ? -std::numeric_limits<double>::infinity()
                                  :  std::numeric_limits<double>::infinity();

    std::vector<double> global_point(dim);

#ifdef _OPENMP
    #pragma omp parallel
#endif
    {
        std::vector<double> vars(dim);
        std::vector<te_variable> te_vars(dim);

        for (size_t i = 0; i < dim; i++) {
            te_vars[i] = { names[i].c_str(), &vars[i] };
        }

        int err = 0;
        te_expr* compiled = te_compile(expr.c_str(), te_vars.data(), (int)dim, &err);

        if (!compiled) {
#ifdef _OPENMP
            #pragma omp critical
#endif
            {
                throw std::runtime_error("Failed to compile expression with tinyexpr");
            }
        }

        double best = maximise ? -std::numeric_limits<double>::infinity()
                               :  std::numeric_limits<double>::infinity();
        std::vector<double> best_point(dim);

#ifdef _OPENMP
        #pragma omp for
#endif
        for (int64_t idx = 0; idx < total; idx++) {
            int64_t t = idx;

            for (size_t d = 0; d < dim; d++) {
                int64_t pos = t % counts[d];
                t /= counts[d];
                vars[d] = mins[d] + pos * steps[d];
            }

            double val = te_eval(compiled);

            if ((maximise && val > best) || (!maximise && val < best)) {
                best = val;
                best_point = vars;
            }
        }

#ifdef _OPENMP
        #pragma omp critical
#endif
        {
            if ((maximise && best > global_best) ||
                (!maximise && best < global_best)) {
                global_best = best;
                global_point = best_point;
            }
        }

        te_free(compiled);
    }

    py::dict result;
    result["value"] = global_best;

    py::dict point;
    for (size_t i = 0; i < dim; i++) {
        point[names[i].c_str()] = global_point[i];
    }

    result["point"] = point;
    return result;
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "gridoptim core";
    m.def("optimise", &optimise, "Run grid search optimisation");
}
