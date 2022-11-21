cmake_minimum_required(VERSION 3.17)
project(py-build-cmake VERSION 0.0.16)
set(PY_VERSION_SUFFIX "a2")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})

# Make sure that the Python and CMake versions match
if (DEFINED PY_BUILD_CMAKE_PACKAGE_VERSION)
    if (NOT "${PY_BUILD_CMAKE_PACKAGE_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${PY_BUILD_CMAKE_PACKAGE_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find the pybind11 package
include(cmake/QueryPythonForPybind11.cmake)
find_pybind11_python_first()

# Compile the example Python module
pybind11_add_module(_add_module MODULE "src/add_module.cpp")
target_compile_definitions(_add_module PRIVATE
    MODULE_NAME=$<TARGET_FILE_BASE_NAME:_add_module>
    VERSION_INFO="${PY_FULL_VERSION}"
)
set_target_properties(_add_module PROPERTIES CXX_VISIBILITY_PRESET "hidden")
if (CMAKE_SYSTEM_NAME MATCHES "Linux")
    target_link_options(_add_module PRIVATE "LINKER:--exclude-libs,ALL")
endif()

# Install the Python module
install(TARGETS _add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PY_BUILD_CMAKE_MODULE_NAME})

# Generate stubs for the Python module
option(WITH_PY_STUBS
    "Generate Python stub files (.pyi) for the Python module." On)
if (WITH_PY_STUBS AND NOT CMAKE_CROSSCOMPILING)
    include(cmake/Pybind11Stubgen.cmake)
    pybind11_stubgen(_add_module)
    pybind11_stubgen_install(_add_module ${PY_BUILD_CMAKE_MODULE_NAME})
endif()
