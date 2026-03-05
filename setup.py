from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "gridoptim._core",
        sources=["cpp/gridoptim_core.cpp", "cpp/tinyexpr.c"],
        include_dirs=["cpp"],
        cxx_std=17,
        # OpenMP: best effort. Works on many setups; if it fails on some platforms,
        # we can refine flags per-compiler.
        extra_compile_args=[],
        extra_link_args=[],
    )
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
