from setuptools import setup, Extension
from pybind11 import get_include
from pybind11.setup_helpers import build_ext

ext_modules = [
    Extension(
        "gridoptim._core",
        sources=[
            "cpp/gridoptim_core.cpp",  # C++
            "cpp/tinyexpr.c",          # C
        ],
        include_dirs=[
            "cpp",
            get_include(),
        ],
        language="c++",
        extra_compile_args=["-std=c++17"],
    )
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
