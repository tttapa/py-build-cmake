cmake_minimum_required(VERSION 3.18)
project(swig-project VERSION 0.3.4)
set(PY_VERSION_SUFFIX ".dev0")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})
set(Py_LIMITED_API 0x03070000 CACHE STRING
    "CPython stable ABI version. Should match abi3_minimum_cpython_version")

# Make sure that the Python and CMake versions match
if (DEFINED PY_BUILD_CMAKE_PACKAGE_VERSION)
    if (NOT "${PY_BUILD_CMAKE_PACKAGE_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${PY_BUILD_CMAKE_PACKAGE_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find Python
if (CMAKE_CROSSCOMPILING AND NOT (APPLE AND "$ENV{CIBUILDWHEEL}" STREQUAL "1"))
    find_package(Python 3.7 REQUIRED COMPONENTS Development.Module
                                     OPTIONAL_COMPONENTS Development.SABIModule)
else()
    find_package(Python 3.7 REQUIRED COMPONENTS Interpreter Development.Module
                                     OPTIONAL_COMPONENTS Development.SABIModule)
endif()

# Function to fix the Python SOABI extension suffix for the generated module
function(configure_python_soabi target abi)
    if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
        set_property (TARGET ${target} PROPERTY SUFFIX ".pyd")
    endif()
    if (abi)
        get_property (suffix TARGET ${target} PROPERTY SUFFIX)
        if (NOT suffix)
            set (suffix "${CMAKE_SHARED_MODULE_SUFFIX}")
        endif()
        set_property (TARGET ${target} PROPERTY SUFFIX ".${abi}${suffix}")
    endif()
endfunction()

# Find the SWIG package to generate Python bindings
include(cmake/QueryPythonForSWIG.cmake)
find_swig_python_first()
set(UseSWIG_MODULE_VERSION 2)
include(UseSWIG)

# Create a SWIG module with Python bindings for add_module.cpp
set_source_files_properties("src/add_module.i" PROPERTIES CPLUSPLUS ON)
swig_add_library(add_module TYPE MODULE LANGUAGE python
    SOURCES "src/add_module.i" "src/add_module.cpp")
set_target_properties(add_module PROPERTIES
    SWIG_USE_TARGET_INCLUDE_DIRECTORIES TRUE
    SWIG_COMPILE_OPTIONS "-Wall")
target_compile_definitions(add_module PRIVATE VERSION_INFO="${PY_FULL_VERSION}")

# Link to the correct Python library and configure the appropriate ABI
if (Python_INTERPRETER_ID STREQUAL "Python")
    if (NOT TARGET Python::SABIModule)
        message(SEND_ERROR "CPython requires component Development.SABIModule")
    endif()
    message(STATUS "Using CPython stable ABI (${Py_LIMITED_API} - ${Python_SOSABI})")
    set_target_properties(add_module PROPERTIES
        SWIG_COMPILE_DEFINITIONS Py_LIMITED_API=${Py_LIMITED_API})
    target_compile_definitions(add_module PRIVATE Py_LIMITED_API=${Py_LIMITED_API})
    target_link_libraries(add_module PRIVATE Python::SABIModule)
    configure_python_soabi(add_module "${Python_SOSABI}")
else()
    message(STATUS "Using default ABI (${Python_SOABI})")
    target_link_libraries(add_module PRIVATE Python::Module)
    configure_python_soabi(add_module "${Python_SOABI}")
endif()

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
