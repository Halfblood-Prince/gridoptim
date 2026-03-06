#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cmath>
#include <limits>
#include <mutex>
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
    const long long n = static_cast<long long>(std::floor(span / step)) + 1;
    return (n < 1) ? 1 : n;
}

struct ThreadCache {
    std::vector<double> x;
    std::vector<te_variable> vars;
    te_expr* compiled = nullptr;

    void reset() {
        if (compiled) {
            te_free(compiled);
            compiled = nullptr;
        }
        x.clear();
        vars.clear();
    }

    ~ThreadCache() { reset(); }
    ThreadCache() = default;
    ThreadCache(const ThreadCache&) = delete;
    ThreadCache& operator=(const ThreadCache&) = delete;
    ThreadCache(ThreadCache&& other) noexcept
        : x(std::move(other.x)), vars(std::move(other.vars)), compiled(other.compiled) {
        other.compiled = nullptr;
    }
    ThreadCache& operator=(ThreadCache&& other) noexcept {
        if (this != &other) {
            reset();
            x = std::move(other.x);
            vars = std::move(other.vars);
            compiled = other.compiled;
            other.compiled = nullptr;
        }
        return *this;
    }
};

class GridOptimCore {
public:
    void configure(
        const std::string& expr,
        const std::vector<std::string>& var_names,
        const std::vector<double>& mins,
        const std::vector<double>& maxs,
        const std::vector<double>& steps
    ) {
        const size_t d = var_names.size();
        if (d == 0) throw std::runtime_error("No variables");
        if (mins.size() != d || maxs.size() != d || steps.size() != d) {
            throw std::runtime_error("mins/maxs/steps must match var_names length");
        }

        std::lock_guard<std::mutex> guard(mutex_);

        const bool same_config = configured_
            && expr_ == expr
            && var_names_ == var_names
            && mins_ == mins
            && maxs_ == maxs
            && steps_ == steps;
        if (same_config) {
            return;
        }

        expr_ = expr;
        var_names_ = var_names;
        mins_ = mins;
        maxs_ = maxs;
        steps_ = steps;

        n_.assign(d, 0);
        grid_values_.assign(d, {});
        total_ = 1;

        for (size_t i = 0; i < d; ++i) {
            n_[i] = count_steps(mins_[i], maxs_[i], steps_[i]);
            if (n_[i] <= 0) throw std::runtime_error("Invalid step count");
            if (total_ > std::numeric_limits<long long>::max() / n_[i]) {
                throw std::runtime_error("Grid too large");
            }
            total_ *= n_[i];

            auto& values = grid_values_[i];
            values.resize(static_cast<size_t>(n_[i]));
            for (long long k = 0; k < n_[i]; ++k) {
                values[static_cast<size_t>(k)] = mins_[i] + static_cast<double>(k) * steps_[i];
            }
            values.back() = maxs_[i];
        }

        destroy_thread_caches();
        configured_ = true;
    }

    py::tuple optimise(const std::string& mode) {
        py::gil_scoped_release release;

        const bool is_min = (mode == "min");
        const bool is_max = (mode == "max");
        if (!is_min && !is_max) throw std::runtime_error("mode must be 'min' or 'max'");

        std::lock_guard<std::mutex> guard(mutex_);
        if (!configured_) throw std::runtime_error("Optimiser not configured");

        const int requested_threads = max_threads();
        prepare_thread_caches(requested_threads);

        const size_t d = var_names_.size();
        const double init_best = is_min ? std::numeric_limits<double>::infinity()
                                        : -std::numeric_limits<double>::infinity();
        double best_val = init_best;
        std::vector<double> best_point(d, 0.0);

        #pragma omp parallel
        {
            const int tid = thread_id();
            ThreadCache& cache = thread_caches_[static_cast<size_t>(tid)];
            double local_best = init_best;
            std::vector<double> local_point(d, 0.0);
            std::vector<long long> idxs(d, 0);

            const long long start = (total_ * tid) / requested_threads;
            const long long end = (total_ * (tid + 1)) / requested_threads;

            if (start < end) {
                long long rem = start;
                for (size_t off = d; off-- > 0;) {
                    const long long base = n_[off];
                    idxs[off] = rem % base;
                    rem /= base;
                    cache.x[off] = grid_values_[off][static_cast<size_t>(idxs[off])];
                }

                for (long long linear = start; linear < end; ++linear) {
                    const double val = te_eval(cache.compiled);

                    if ((is_min && val < local_best) || (is_max && val > local_best)) {
                        local_best = val;
                        local_point = cache.x;
                    }

                    if (linear + 1 == end) break;

                    for (size_t off = d; off-- > 0;) {
                        long long next = idxs[off] + 1;
                        if (next < n_[off]) {
                            idxs[off] = next;
                            cache.x[off] = grid_values_[off][static_cast<size_t>(next)];
                            break;
                        }
                        idxs[off] = 0;
                        cache.x[off] = grid_values_[off][0];
                    }
                }
            }

            #pragma omp critical
            {
                if ((is_min && local_best < best_val) || (is_max && local_best > best_val)) {
                    best_val = local_best;
                    best_point = local_point;
                }
            }
        }

        return py::make_tuple(best_val, best_point);
    }

    ~GridOptimCore() {
        std::lock_guard<std::mutex> guard(mutex_);
        destroy_thread_caches();
    }

private:
    std::string expr_;
    std::vector<std::string> var_names_;
    std::vector<double> mins_;
    std::vector<double> maxs_;
    std::vector<double> steps_;
    std::vector<long long> n_;
    std::vector<std::vector<double>> grid_values_;
    long long total_ = 0;
    bool configured_ = false;
    std::vector<ThreadCache> thread_caches_;
    std::mutex mutex_;

    int max_threads() const {
#ifdef _OPENMP
        return omp_get_max_threads();
#else
        return 1;
#endif
    }

    int thread_id() const {
#ifdef _OPENMP
        return omp_get_thread_num();
#else
        return 0;
#endif
    }

    void prepare_thread_caches(int thread_count) {
        if (thread_count < 1) thread_count = 1;
        if (thread_caches_.size() == static_cast<size_t>(thread_count)) {
            return;
        }

        destroy_thread_caches();
        thread_caches_.resize(static_cast<size_t>(thread_count));

        const size_t d = var_names_.size();
        for (ThreadCache& cache : thread_caches_) {
            cache.x.assign(d, 0.0);
            cache.vars.resize(d);
            for (size_t i = 0; i < d; ++i) {
                cache.vars[i].name = var_names_[i].c_str();
                cache.vars[i].address = &cache.x[i];
                cache.vars[i].type = TE_VARIABLE;
                cache.vars[i].context = nullptr;
            }
            int err = 0;
            cache.compiled = te_compile(expr_.c_str(), cache.vars.data(), static_cast<int>(d), &err);
            if (!cache.compiled) {
                throw std::runtime_error("Failed to compile expression at position " + std::to_string(err));
            }
        }
    }

    void destroy_thread_caches() {
        for (ThreadCache& cache : thread_caches_) {
            cache.reset();
        }
        thread_caches_.clear();
    }
};

py::tuple optimise_cpp(
    const std::string& expr,
    const std::vector<std::string>& var_names,
    const std::vector<double>& mins,
    const std::vector<double>& maxs,
    const std::vector<double>& steps,
    const std::string& mode
) {
    GridOptimCore core;
    core.configure(expr, var_names, mins, maxs, steps);
    return core.optimise(mode);
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "gridoptim C++ core (OpenMP)";
    py::class_<GridOptimCore>(m, "GridOptimCore")
        .def(py::init<>())
        .def("configure", &GridOptimCore::configure,
             py::arg("expr"),
             py::arg("var_names"),
             py::arg("mins"),
             py::arg("maxs"),
             py::arg("steps"))
        .def("optimise", &GridOptimCore::optimise, py::arg("mode"));

    m.def("optimise", &optimise_cpp,
          py::arg("expr"),
          py::arg("var_names"),
          py::arg("mins"),
          py::arg("maxs"),
          py::arg("steps"),
          py::arg("mode"));
}
