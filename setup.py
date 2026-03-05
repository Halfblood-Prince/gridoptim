from setuptools import setup, Extension
from pybind11 import get_include
from pybind11.setup_helpers import build_ext

# Limited API for Python 3.10+ => 0x030A0000
PY_LIMITED = "0x030A0000"

ext_modules = [
    Extension(
        "gridoptim._core",
        sources=[
            "cpp/gridoptim_core.cpp",
            "cpp/tinyexpr.c",
        ],
        include_dirs=[
            "cpp",
            get_include(),
        ],
        language="c++",
        define_macros=[("Py_LIMITED_API", PY_LIMITED)],
        py_limited_api=True,
        extra_compile_args=["-std=c++17"],
    )
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
