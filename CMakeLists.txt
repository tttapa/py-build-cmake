cmake_minimum_required(VERSION 3.20)
project(py-build-cmake VERSION 0.0.0)
set(PY_VERSION_SUFFIX "a0")
set(PY_FULL_VERSION ${PROJECT_VERSION}${PY_VERSION_SUFFIX})

# Make sure that the Python and CMake versions match
if (DEFINED VERIFY_VERSION)
    if (NOT "${VERIFY_VERSION}" MATCHES "^${PY_FULL_VERSION}$")
        message(FATAL_ERROR "Version number does not match "
                             "(${VERIFY_VERSION} - ${PY_FULL_VERSION}).")
    endif()
endif()

# Find the Pybind11 headers
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
if (NOT PY_BUILD_CMAKE_PYBIND11_INCLUDE)
    execute_process(COMMAND ${Python3_EXECUTABLE}
            -c "import pybind11; print(pybind11.get_include())"
        OUTPUT_VARIABLE PY_BUILD_CMAKE_PYBIND11_INCLUDE
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE PY_BUILD_CMAKE_PYBIND11_RESULT)
    if (NOT PY_BUILD_CMAKE_PYBIND11_RESULT EQUAL 0)
        message(FATAL_ERROR "Could NOT find pybind11.")
    endif()
    message(STATUS "Found pybind11: ${PY_BUILD_CMAKE_PYBIND11_INCLUDE}")
    set(PY_BUILD_CMAKE_PYBIND11_INCLUDE ${PY_BUILD_CMAKE_PYBIND11_INCLUDE}
        CACHE PATH "Path to the Pybind11 headers.")
endif()
# Add a Pybind11 target
add_library(pybind11::pybind11 INTERFACE IMPORTED)
target_include_directories(pybind11::pybind11
    INTERFACE ${PY_BUILD_CMAKE_PYBIND11_INCLUDE})
target_link_libraries(pybind11::pybind11 INTERFACE Python3::Module)

# Compile the example Python module
Python3_add_library(_add_module MODULE "src/add_module.cpp")
target_link_libraries(_add_module PRIVATE pybind11::pybind11)
target_compile_definitions(_add_module PRIVATE
    MODULE_NAME=_add_module
    VERSION_INFO="${PY_FULL_VERSION}"
)
if (NOT WIN32)
    target_link_options(_add_module PRIVATE "LINKER:--exclude-libs,ALL")
endif()

# Install the Python module
install(TARGETS _add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION py_build_cmake)

# Generate stubs for the Python module
option(WITH_PY_STUBS
    "Generate Python stub files (.pyi) for the Python module." On)
if (WITH_PY_STUBS)
    set(STUBS_DIR ${CMAKE_CURRENT_BINARY_DIR}/stubs)
    add_custom_command(TARGET _add_module POST_BUILD
    COMMAND ${Python3_EXECUTABLE} -m pybind11_stubgen
            _add_module
            --ignore-invalid=defaultarg
            --no-setup-py
            -o ${STUBS_DIR}
    BYPRODUCTS ${STUBS_DIR}/_add_module-stubs/__init__.pyi
    WORKING_DIRECTORY $<TARGET_FILE_DIR:_add_module>
    USES_TERMINAL)
endif()

# Install the stubs
if (WITH_PY_STUBS)
    install(FILES ${STUBS_DIR}/_add_module-stubs/__init__.pyi
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        RENAME _add_module.pyi
        DESTINATION py_build_cmake)
endif()
