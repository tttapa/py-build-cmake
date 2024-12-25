cmake_minimum_required(VERSION 3.17)
project(cmake-preset)

# Find the Python development files
find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Make sure that we got the secret from the CMakePresets.json file
if (NOT PRESET_SECRET STREQUAL "secret-preset-value")
    message(FATAL_ERROR "Invalid PRESET_SECRET")
endif()

# Add a custom target to generate a Python file
add_custom_command(OUTPUT "__init__.py"
    COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/generate.py "${PRESET_SECRET}"
    MAIN_DEPENDENCY generate.py)
add_custom_target(init ALL DEPENDS "__init__.py")

# Install the module
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/__init__.py"
    DESTINATION ${PY_BUILD_CMAKE_IMPORT_NAME}
    COMPONENT python_modules
    EXCLUDE_FROM_ALL)
