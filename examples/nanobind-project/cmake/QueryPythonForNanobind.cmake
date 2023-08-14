option(USE_GLOBAL_NANOBIND "Don't query Python to find nanobind" Off)
mark_as_advanced(USE_GLOBAL_NANOBIND)

# First tries to find Python 3.8, then tries to import the nanobind module to
# query the CMake config location, and finally imports nanobind using
# find_package(nanobind REQUIRED CONFIG CMAKE_FIND_ROOT_PATH_BOTH).
# This is a macro rather than a function to make the variables set by
# find_package(Python) available to the nanobind functions when called in the
# main project (specifically, the nanobind_build_library function explicitly
# adds the ${Python_INCLUDE_DIRS} to the nanobind include directories). It also
# allows un-setting NB_SUFFIX when cross-compiling.
macro(find_nanobind_python_first)

    # Find Python
    if (CMAKE_CROSSCOMPILING AND FALSE) # https://gitlab.kitware.com/cmake/cmake/-/issues/25145#note_1396533
        find_package(Python 3.8 REQUIRED
            COMPONENTS Development.Module
            OPTIONAL_COMPONENTS Development.SABIModule)
    else()
        find_package(Python 3.8 REQUIRED
            COMPONENTS Interpreter Development.Module
            OPTIONAL_COMPONENTS Development.SABIModule)
    endif()

    # Tweak extension suffix and debug ABI when cross-compiling
    if (CMAKE_CROSSCOMPILING)
        if (NOT PY_BUILD_EXT_SUFFIX AND DEFINED TOOLCHAIN_Python_EXT_SUFFIX)
            set(PY_BUILD_EXT_SUFFIX ${TOOLCHAIN_Python_EXT_SUFFIX})
        endif()
        # SETUPTOOLS_EXT_SUFFIX environment variable
        if (NOT PY_BUILD_EXT_SUFFIX AND DEFINED ENV{SETUPTOOLS_EXT_SUFFIX})
            message(STATUS "Setting PY_BUILD_EXT_SUFFIX to "
                "ENV{SETUPTOOLS_EXT_SUFFIX}: $ENV{SETUPTOOLS_EXT_SUFFIX}")
            set(PY_BUILD_EXT_SUFFIX $ENV{SETUPTOOLS_EXT_SUFFIX})
        endif()
        # If that still didn't work, use the Python_SOABI variable:
        if (NOT PY_BUILD_EXT_SUFFIX AND Python_SOABI)
            message(STATUS "Determining Python extension suffix based on "
                    "Python_SOABI.")
            if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
                set(PY_BUILD_EXTENSION ".pyd")
            else()
                set(PY_BUILD_EXTENSION "${CMAKE_SHARED_MODULE_SUFFIX}")
            endif()
            set(PY_BUILD_EXT_SUFFIX ".${Python_SOABI}${PY_BUILD_EXTENSION}")
        endif()
        # Sanity checks:
        if (NOT PY_BUILD_EXT_SUFFIX)
            message(FATAL_ERROR "Unable to determine extension suffix.\
                Try manually setting PY_BUILD_EXT_SUFFIX.")
        endif()
        if (Python_SOABI AND
                NOT PY_BUILD_EXT_SUFFIX MATCHES "\\.${Python_SOABI}\\.")
            message(WARNING "PY_BUILD_EXT_SUFFIX (${PY_BUILD_EXT_SUFFIX}) "
                "does not match Python_SOABI (${Python_SOABI})")
        endif()
        # Check the debug ABI:
        if (NOT PY_BUILD_DEBUG_ABI AND DEFINED TOOLCHAIN_Python_DEBUG_ABI)
            set(PY_BUILD_DEBUG_ABI ${TOOLCHAIN_Python_DEBUG_ABI})
        endif()
        # Otherwise, try to deduce it from the SOABI:
        if (NOT DEFINED PY_BUILD_DEBUG_ABI)
            if (PY_BUILD_EXT_SUFFIX MATCHES "[0-9]+d-")
                set(PY_BUILD_DEBUG_ABI true)
            else()
                set(PY_BUILD_DEBUG_ABI false)
            endif()
        endif()
        # Cache the result:
        set(PY_BUILD_EXT_SUFFIX ${PY_BUILD_EXT_SUFFIX} CACHE STRING
            "The extension for Python extension modules")
        set(PY_BUILD_DEBUG_ABI ${PY_BUILD_DEBUG_ABI} CACHE BOOL
            "Whether to compile for a debug version of Python")
        # Override nanobind-config.cmake's NB_SUFFIX variable:
        message(STATUS "Python extension suffix: ${PY_BUILD_EXT_SUFFIX}")
        set(NB_SUFFIX ${PY_BUILD_EXT_SUFFIX} CACHE INTERNAL "" FORCE)
    endif()

    # Query Python to see if it knows where the pybind11 root is
    if (NOT USE_GLOBAL_NANOBIND AND Python_EXECUTABLE)
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

    if (CMAKE_CROSSCOMPILING)
        # nanobind-config.cmake unconditionally sets this, but we want it to
        # use our cache variable instead.
        unset(NB_SUFFIX)
    endif()

endmacro()