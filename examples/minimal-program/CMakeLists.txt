cmake_minimum_required(VERSION 3.15)
project(minimal-program)

# Add the executable to compile
add_executable(minimal_program "src/minimal_program.cpp")

# Install the executable
install(TARGETS minimal_program
        EXCLUDE_FROM_ALL
        COMPONENT python_binaries
        RUNTIME DESTINATION ${PY_BUILD_CMAKE_PACKAGE_NAME}-${PY_BUILD_CMAKE_PACKAGE_VERSION}.data/scripts
        LIBRARY DESTINATION ${PY_BUILD_CMAKE_PACKAGE_NAME}-${PY_BUILD_CMAKE_PACKAGE_VERSION}.data/platlib)
