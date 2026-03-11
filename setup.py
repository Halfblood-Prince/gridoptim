from setuptools import setup, Extension
import pybind11
import sys

if sys.platform == "win32":
    compile_args = ["/O2", "/openmp"]
    link_args = []
else:
    compile_args = ["-O3", "-fopenmp"]
    link_args = ["-fopenmp"]

ext_modules = [
    Extension(
        "gridoptim._core",
        ["cpp/gridoptim_core.cpp", "cpp/tinyexpr.c"],
        include_dirs=[pybind11.get_include(), "cpp"],
        language="c++",
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    )
]

setup(
    name="gridoptim",
    version="0.1",
    packages=["gridoptim"],
    ext_modules=ext_modules,
)
