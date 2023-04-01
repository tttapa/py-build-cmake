option(USE_GLOBAL_NANOBIND "Don't query Python to find nanobind" Off)
mark_as_advanced(USE_GLOBAL_NANOBIND)

# First tries to find Python 3, then tries to import the nanobind module to
# query the CMake config location, and finally imports nanobind using
# find_package(nanobind REQUIRED CONFIG CMAKE_FIND_ROOT_PATH_BOTH).
# This is a macro rather than a function to make the variables set by
# find_package(Python) available to the nanobind functions when called in the
# main project (specifically, the nanobind_build_library function explicitly
# adds the ${Python_INCLUDE_DIRS} to the nanobind include directories). It also
# allows un-setting NB_SUFFIX when cross-compiling.
macro(find_nanobind_python_first)

    find_package(Python 3.8 REQUIRED COMPONENTS Interpreter Development.Module)
    if (NOT USE_GLOBAL_NANOBIND)
        # Query Python to see if it knows where the headers are
        if (NOT nanobind_ROOT OR NOT EXISTS ${nanobind_ROOT})
            message(STATUS "Detecting nanobind CMake location")
            execute_process(COMMAND ${Python_EXECUTABLE}
                    -c "import nanobind; print(nanobind.cmake_dir())"
                OUTPUT_VARIABLE PY_BUILD_NANOBIND_ROOT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                RESULT_VARIABLE PY_BUILD_CMAKE_NANOBIND_RESULT)
            # If it was successful
            if (PY_BUILD_CMAKE_NANOBIND_RESULT EQUAL 0)
                message(STATUS "nanobind CMake location: ${PY_BUILD_NANOBIND_ROOT}")
                set(nanobind_ROOT ${PY_BUILD_NANOBIND_ROOT}
                    CACHE PATH "Path to the nanobind CMake configuration." FORCE)
            else()
                unset(nanobind_ROOT CACHE)
            endif()
        endif()
    endif()

    # nanobind consists of just sources and a CMake config file, so finding a
    # native version is fine
    find_package(nanobind ${ARGN} REQUIRED CONFIG CMAKE_FIND_ROOT_PATH_BOTH)

    # Tweak extension suffix when cross-compiling
    if (CMAKE_CROSSCOMPILING)
        if (NOT PY_BUILD_EXT_SUFFIX)
            message(STATUS "Determining Python extension suffix")
            # Find the python3.x-config script in the sysroot instead of on the
            # build system:
            find_program(PY_BUILD_Python_CONFIG
                python${Python_VERSION_MAJOR}.${Python_VERSION_MINOR}-config
                ONLY_CMAKE_FIND_ROOT_PATH)
            # Report errors:
            if (NOT PY_BUILD_Python_CONFIG)
                message(FATAL_ERROR "Unable to find python3-config."
                    "\nTry manually setting PY_BUILD_EXT_SUFFIX.")
            else()
                # If we found the python3.x-config script, query it for the
                # extension suffix:
                execute_process(COMMAND ${PY_BUILD_Python_CONFIG}
                    --extension-suffix
                    OUTPUT_VARIABLE PY_BUILD_EXT_SUFFIX
                    ERROR_VARIABLE PY_BUILD_EXT_SUFFIX_ERR
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    RESULT_VARIABLE PY_BUILD_EXT_SUFFIX_RESULT)
                # Report errors:
                if (NOT PY_BUILD_EXT_SUFFIX_RESULT EQUAL 0
                    OR NOT PY_BUILD_EXT_SUFFIX)
                    message(FATAL_ERROR "Unable to determine extension suffix:"
                        "\n${PY_BUILD_EXT_SUFFIX}"
                        "\n${PY_BUILD_EXT_SUFFIX_ERR}"
                        "\nTry manually setting PY_BUILD_EXT_SUFFIX.")
                endif()
                # Cache the result:
                set(PY_BUILD_EXT_SUFFIX ${PY_BUILD_EXT_SUFFIX} CACHE STRING
                    "The extension for Python extension modules")
            endif()
        endif()
        # Override nanobind-config.cmake's NB_SUFFIX variable:
        message(STATUS "Python extension suffix: ${PY_BUILD_EXT_SUFFIX}")
        unset(NB_SUFFIX)
        set(NB_SUFFIX ${PY_BUILD_EXT_SUFFIX} CACHE INTERNAL "" FORCE)
    endif()

endmacro()