cmake_minimum_required(VERSION 4.1)
cmake_policy(SET CMP0155 OLD)
project(py-conan-add VERSION 0.6.0)
set(PY_VERSION_SUFFIX "a3.dev0")  # e.g. b3.dev1, see PEP 440
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})

# Make sure that the Python and CMake versions match
if (DEFINED PY_BUILD_CMAKE_PROJECT_VERSION)
    if (NOT "${PY_BUILD_CMAKE_PROJECT_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${PY_BUILD_CMAKE_PROJECT_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find the Python development files
if (CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING_EMULATOR OR CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
    find_package(Python3 REQUIRED COMPONENTS Development.Module)
else()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
endif()

# Find the pybind11 library
set(PYBIND11_USE_CROSSCOMPILING On) # https://github.com/pybind/pybind11/pull/5083
find_package(pybind11 REQUIRED)

# Compile the example Python module
pybind11_add_module(_add_module MODULE "src/ext/add_module.cpp")
target_compile_definitions(_add_module PRIVATE
    MODULE_NAME=_add_module
    VERSION_INFO="${PY_FULL_VERSION}"
)

# Add other libraries after pybind11_add_module
find_package(fmt REQUIRED)
target_link_libraries(_add_module PRIVATE fmt::fmt)

# Hide all symbols by default (including external libraries on Linux)
set_target_properties(_add_module PROPERTIES
    CXX_VISIBILITY_PRESET "hidden"
    VISIBILITY_INLINES_HIDDEN true)
if (CMAKE_SYSTEM_NAME MATCHES "Linux")
    target_link_options(_add_module PRIVATE "LINKER:--exclude-libs,ALL")
endif()

# Install the Python module
set(PYTHON_MODULE_DESTINATION ${PY_BUILD_CMAKE_IMPORT_NAME})
install(TARGETS _add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PYTHON_MODULE_DESTINATION})
# Install the debug file for the Python module (Windows only)
if (WIN32)
    install(FILES $<TARGET_PDB_FILE:_add_module>
            EXCLUDE_FROM_ALL
            COMPONENT python_modules
            DESTINATION ${PYTHON_MODULE_DESTINATION}
            OPTIONAL)
endif()

