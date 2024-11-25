option(USE_GLOBAL_NANOBIND "Don't query Python to find nanobind" Off)
mark_as_advanced(USE_GLOBAL_NANOBIND)

# Returns the parent folder of the current file.
function(find_nanobind_python_first_dir var)
    set(${var} ${CMAKE_CURRENT_FUNCTION_LIST_DIR} PARENT_SCOPE)
endfunction()

# First tries to find Python 3.8, then tries to import the nanobind module to
# query the CMake config location, and finally imports nanobind using
# find_package(nanobind REQUIRED CONFIG CMAKE_FIND_ROOT_PATH_BOTH). It also
# allows setting (and fixing) NB_SUFFIX and NB_SUFFIX_S when cross-compiling.
#
# This is a macro rather than a function to make the variables set by
# find_package(Python) available to the nanobind functions when called in the
# main project (specifically, the nanobind_build_library function explicitly
# adds the ${Python_INCLUDE_DIRS} to the nanobind include directories).
macro(find_nanobind_python_first)

    # Find Python
    if (CMAKE_CROSSCOMPILING AND NOT (APPLE AND "$ENV{CIBUILDWHEEL}" STREQUAL "1"))
        find_package(Python 3.8 REQUIRED
            COMPONENTS Development.Module
            OPTIONAL_COMPONENTS Development.SABIModule)
    else()
        find_package(Python 3.8 REQUIRED
            COMPONENTS Interpreter Development.Module
            OPTIONAL_COMPONENTS Development.SABIModule)
    endif()

    # Tweak extension suffix and debug ABI when cross-compiling
    if (CMAKE_CROSSCOMPILING AND NOT (DEFINED CACHE{NB_SUFFIX}
                                      AND DEFINED CACHE{NB_SUFFIX_S}))
        find_nanobind_python_first_dir(FNBF_CURRENT_DIR)
        include(${FNBF_CURRENT_DIR}/nanobindGuessPythonExtSuffix.cmake)
        nanobind_guess_python_module_extension(Python)
    endif()
    # Save for later ...
    if (CMAKE_CROSSCOMPILING AND (DEFINED NB_SUFFIX
                                  AND DEFINED NB_SUFFIX_S))
        set(PY_BUILD_CMAKE_NB_SUFFIX "${NB_SUFFIX}" CACHE STRING "")
        set(PY_BUILD_CMAKE_NB_SUFFIX_S "${NB_SUFFIX_S}" CACHE STRING "")
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

    # nanobind-config.cmake unconditionally sets these variables, but we want it
    # to use our variables instead.
    if (CMAKE_CROSSCOMPILING AND (DEFINED CACHE{PY_BUILD_CMAKE_NB_SUFFIX}
                                  AND DEFINED CACHE{PY_BUILD_CMAKE_NB_SUFFIX_S}))
        unset(NB_SUFFIX)
        unset(NB_SUFFIX_S)
        set(NB_SUFFIX "$CACHE{PY_BUILD_CMAKE_NB_SUFFIX}" CACHE INTERNAL "")
        set(NB_SUFFIX_S "$CACHE{PY_BUILD_CMAKE_NB_SUFFIX_S}" CACHE INTERNAL "")
    endif()

endmacro()
