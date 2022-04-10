cmake_minimum_required(VERSION 3.20)
project(py-build-cmake VERSION 0.0.5)
set(PY_VERSION_SUFFIX "")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})

# Make sure that the Python and CMake versions match
if (DEFINED VERIFY_VERSION)
    if (NOT "${VERIFY_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${VERIFY_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find the Pybind11 headers
include(cmake/QueryPythonForPybind11.cmake)
find_pybind11_python_first()

# Compile the example Python module
Python3_add_library(_add_module MODULE "src/add_module.cpp")
target_link_libraries(_add_module PRIVATE pybind11::pybind11)
target_compile_definitions(_add_module PRIVATE
    MODULE_NAME=$<TARGET_FILE_BASE_NAME:_add_module>
    VERSION_INFO="${PY_FULL_VERSION}"
)
if (NOT WIN32)
    target_link_options(_add_module PRIVATE "LINKER:--exclude-libs,ALL")
endif()

# Install the Python module
install(TARGETS _add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION pybind11_project)

# Generate stubs for the Python module
option(WITH_PY_STUBS
    "Generate Python stub files (.pyi) for the Python module." On)
if (WITH_PY_STUBS AND NOT CMAKE_CROSSCOMPILING)
    include(cmake/Pybind11Stubgen.cmake)
    pybind11_stubgen(_add_module)
    pybind11_stubgen_install(_add_module pybind11_project)
endif()
