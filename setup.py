from pathlib import Path
from setuptools import setup, Extension
import pybind11
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

if sys.platform == "win32":
    compile_args = ["/O2", "/openmp"]
    link_args = []
else:
    compile_args = ["-Ofast", "-march=native", "-fno-math-errno", "-fopenmp"]
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

project_metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
project_version = project_metadata["project"]["version"]

setup(
    name="gridoptim",
    version=project_version,
    packages=["gridoptim"],
    ext_modules=ext_modules,
)
