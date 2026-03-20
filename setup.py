from pathlib import Path
from setuptools import setup, Extension
import pybind11
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

native_opt_in = os.environ.get("GRIDOPTIM_NATIVE", "").strip().lower() in {"1", "true", "yes", "on"}

if sys.platform == "win32":
    compile_args = ["/O2", "/openmp"]
    link_args = []
else:
    compile_args = ["-Ofast", "-fno-math-errno", "-fopenmp"]
    if native_opt_in:
        compile_args.append("-march=native")
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
