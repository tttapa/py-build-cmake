option(USE_GLOBAL_SWIG "Don't query Python to find SWIG" Off)
mark_as_advanced(USE_GLOBAL_SWIG)

# First tries to find Python 3, then tries to import the swig module to
# query the SWIG installation location, and finally includes swig using
# find_package(swig ${ARGN} REQUIRED COMPONENTS python),
# where ${ARGN} are the arguments passed to this macro.
macro(find_swig_python_first)

    # Query Python to see if it knows where the swig folders are
    if (NOT USE_GLOBAL_SWIG AND Python_EXECUTABLE)
        if (NOT SWIG_EXECUTABLE OR NOT EXISTS ${SWIG_EXECUTABLE})
            message(STATUS "Detecting SWIG location")
            unset(SWIG_FOUND CACHE)
            unset(SWIG_EXECUTABLE CACHE)
            unset(SWIG_DIR CACHE)
            unset(SWIG_VERSION CACHE)
            unset(SWIG_python_FOUND CACHE)
            # Locate the SWIG executable
            execute_process(COMMAND ${Python_EXECUTABLE} -c
                   "import swig; print(swig.BIN_DIR)"
                OUTPUT_VARIABLE PY_BUILD_SWIG_BIN_DIR
                OUTPUT_STRIP_TRAILING_WHITESPACE
                RESULT_VARIABLE PY_BUILD_CMAKE_SWIG_RESULT)
            # If it was successful
            if (PY_BUILD_CMAKE_SWIG_RESULT EQUAL 0)
                # Look for the swig program in this folder
                find_program(SWIG_EXECUTABLE swig HINTS ${PY_BUILD_SWIG_BIN_DIR}
                    DOC "Path to the SWIG executable."
                    NO_CMAKE_FIND_ROOT_PATH)
                if (SWIG_EXECUTABLE)
                    message(STATUS "Found SWIG executable: ${SWIG_EXECUTABLE}")
                else()
                    message(WARNING "Could not find SWIG executable (searched in ${PY_BUILD_SWIG_BIN_DIR})")
                endif()
            endif()
            # Locate the SWIG library/data directory
            execute_process(COMMAND ${Python_EXECUTABLE} -c
                   "import swig; print(swig.SWIG_LIB_ENV['SWIG_LIB'])"
                OUTPUT_VARIABLE PY_BUILD_SWIG_LIB_DIR
                OUTPUT_STRIP_TRAILING_WHITESPACE
                RESULT_VARIABLE PY_BUILD_CMAKE_SWIG_RESULT)
            # If it was successful
            if (PY_BUILD_CMAKE_SWIG_RESULT EQUAL 0)
                # Look for the swig.swg file in this folder
                find_path(SWIG_DIR swig.swg HINTS ${PY_BUILD_SWIG_LIB_DIR}
                    DOC "Path to the SWIG library directory."
                    NO_CMAKE_FIND_ROOT_PATH)
                if (SWIG_DIR)
                    message(STATUS "Found SWIG library directory: ${SWIG_DIR}")
                else()
                    message(WARNING "Could not find SWIG library directory (searched in ${PY_BUILD_SWIG_LIB_DIR})")
                endif()
            endif()
        endif()
    endif()

    find_package(SWIG ${ARGN} REQUIRED COMPONENTS python)

endmacro()
