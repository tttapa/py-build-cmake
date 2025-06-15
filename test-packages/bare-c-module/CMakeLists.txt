cmake_minimum_required(VERSION 3.17...4.0)
project(bare-c-module)

# Find the Python development files
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)

# Add the module to compile
Python3_add_library(bare_c_module MODULE "add_module.c" WITH_SOABI)

# Install the module
install(TARGETS bare_c_module
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION .)
