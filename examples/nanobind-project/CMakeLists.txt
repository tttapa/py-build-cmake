cmake_minimum_required(VERSION 3.26)
project(nanobind-project VERSION 0.2.0)
set(PY_VERSION_SUFFIX "a7.dev0")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})

# Make sure that the Python and CMake versions match
if (DEFINED PY_BUILD_CMAKE_PACKAGE_VERSION)
    if (NOT "${PY_BUILD_CMAKE_PACKAGE_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${PY_BUILD_CMAKE_PACKAGE_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find the nanobind package
include(cmake/QueryPythonForNanobind.cmake)
find_nanobind_python_first()

# Compile the example Python module
nanobind_add_module(_add_module STABLE_ABI "src/add_module.cpp")
target_compile_definitions(_add_module PRIVATE
    MODULE_NAME=$<TARGET_FILE_BASE_NAME:_add_module>
    VERSION_INFO="${PY_FULL_VERSION}"
)
# Hide all symbols by default (including external libraries on Linux)
set_target_properties(_add_module PROPERTIES
    CXX_VISIBILITY_PRESET "hidden"
    VISIBILITY_INLINES_HIDDEN true)
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
    include(cmake/NanobindStubgen.cmake)
    nanobind_stubgen(_add_module)
    nanobind_stubgen_install(_add_module ${PY_BUILD_CMAKE_MODULE_NAME})
endif()
