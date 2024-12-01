cmake_minimum_required(VERSION 3.18)
project(swig-project VERSION 0.3.1)
set(PY_VERSION_SUFFIX ".dev0")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})
set(Py_LIMITED_API 0x03070000)  # Should match abi3_minimum_cpython_version

# Make sure that the Python and CMake versions match
if (DEFINED PY_BUILD_CMAKE_PACKAGE_VERSION)
    if (NOT "${PY_BUILD_CMAKE_PACKAGE_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${PY_BUILD_CMAKE_PACKAGE_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find Python
if (CMAKE_CROSSCOMPILING AND NOT (APPLE AND "$ENV{CIBUILDWHEEL}" STREQUAL "1"))
    find_package(Python 3.7 REQUIRED COMPONENTS Development.SABIModule)
else()
    find_package(Python 3.7 REQUIRED COMPONENTS Interpreter Development.SABIModule)
endif()

# Find the SWIG package to generate Python bindings
include(cmake/QueryPythonForSWIG.cmake)
find_swig_python_first()
set(UseSWIG_MODULE_VERSION 2)
include(UseSWIG)

# Create a SWIG module
set_source_files_properties(src/add_module.i PROPERTIES CPLUSPLUS ON)
swig_add_library(add_module TYPE MODULE LANGUAGE python
    SOURCES src/add_module.i src/add_module.cpp)
set_target_properties(add_module PROPERTIES
    SWIG_USE_TARGET_INCLUDE_DIRECTORIES TRUE
    SWIG_COMPILE_OPTIONS "-Wall"
    SWIG_COMPILE_DEFINITIONS Py_LIMITED_API=${Py_LIMITED_API})
target_compile_definitions(add_module PRIVATE Py_LIMITED_API=${Py_LIMITED_API})
target_link_libraries(add_module PRIVATE Python::SABIModule)
target_compile_definitions(add_module PRIVATE VERSION_INFO="${PY_FULL_VERSION}")

# Fix the Python SOABI extension suffix
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
  set_property (TARGET add_module PROPERTY SUFFIX ".pyd")
endif()
get_property (suffix TARGET add_module PROPERTY SUFFIX)
if (NOT suffix)
    set (suffix "${CMAKE_SHARED_MODULE_SUFFIX}")
endif()
set_property (TARGET add_module PROPERTY SUFFIX ".${Python_SOSABI}${suffix}")

# Hide all symbols by default (including external libraries on Linux)
set_target_properties(add_module PROPERTIES
    CXX_VISIBILITY_PRESET "hidden"
    VISIBILITY_INLINES_HIDDEN true)
if (CMAKE_SYSTEM_NAME MATCHES "Linux")
    target_link_options(add_module PRIVATE "LINKER:--exclude-libs,ALL")
endif()

# Install the Python module
install(TARGETS add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PY_BUILD_CMAKE_MODULE_NAME})
install(FILES $<TARGET_PROPERTY:add_module,SWIG_SUPPORT_FILES>
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PY_BUILD_CMAKE_MODULE_NAME})
