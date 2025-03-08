cmake_minimum_required(VERSION 3.17...3.31)
project(minimal-debug-component)

# Find the Python development files
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# Add the module to compile
Python3_add_library(_add_module MODULE "src/ext/add_module.c" WITH_SOABI)

# Install the module
install(TARGETS _add_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PY_BUILD_CMAKE_IMPORT_NAME})

# Install stubs to get autocomplete and type hints
install(FILES "src/ext/_add_module.pyi"
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${PY_BUILD_CMAKE_IMPORT_NAME})

# Strip and install debug information
include(cmake/Debug.cmake)
minimal_install_debug_syms(_add_module python_modules_debug
    ${PY_BUILD_CMAKE_IMPORT_NAME} ${PY_BUILD_CMAKE_IMPORT_NAME})
