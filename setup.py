from setuptools import setup, Extension
import pybind11
import sys

compile_args = ["-O3"]

link_args = []

# Enable OpenMP depending on platform
if sys.platform == "win32":
    compile_args.append("/openmp")
else:
    compile_args.append("-fopenmp")
    link_args.append("-fopenmp")

ext_modules = [
    Extension(
        "gridoptim._core",
        ["cpp/gridoptim_core.cpp"],
        include_dirs=[pybind11.get_include()],
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
