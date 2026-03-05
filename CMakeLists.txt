cmake_minimum_required(VERSION 3.18)
project(gridoptim LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 CONFIG REQUIRED)

# OpenMP (optional but strongly recommended)
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
  message(STATUS "OpenMP found")
else()
  message(STATUS "OpenMP not found; building single-threaded")
endif()

pybind11_add_module(_core
  cpp/gridoptim_core.cpp
  cpp/tinyexpr.c
)

target_include_directories(_core PRIVATE cpp)

if(OpenMP_CXX_FOUND)
  target_link_libraries(_core PRIVATE OpenMP::OpenMP_CXX)
endif()