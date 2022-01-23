# First tries to find Python 3, then tries to import the pybind11 module to
# query the header location, and then creates an imported pybind11::pybind11
# target if successful. If importing the pybind11 module failed, falls back to 
# a standard find_package(pybind11) call.
function(find_pybind11_python_first)

    # First query Python to see if it knows where the headers are
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
    if (NOT PY_BUILD_PYBIND11_INCLUDE
        OR NOT EXISTS ${PY_BUILD_PYBIND11_INCLUDE})
        execute_process(COMMAND ${Python3_EXECUTABLE}
                -c "import pybind11; print(pybind11.get_include())"
            OUTPUT_VARIABLE PY_BUILD_PYBIND11_INCLUDE
            OUTPUT_STRIP_TRAILING_WHITESPACE
            RESULT_VARIABLE PY_BUILD_CMAKE_PYBIND11_RESULT)
        # If it was successful
        if (PY_BUILD_CMAKE_PYBIND11_RESULT EQUAL 0)
            message(STATUS "Found pybind11: ${PY_BUILD_PYBIND11_INCLUDE}")
            set(PY_BUILD_PYBIND11_INCLUDE ${PY_BUILD_PYBIND11_INCLUDE}
                CACHE PATH "Path to the Pybind11 headers." FORCE)
        else()
            unset(PY_BUILD_PYBIND11_INCLUDE CACHE)
        endif()
    endif()
    # If querying Python succeeded
    if (PY_BUILD_PYBIND11_INCLUDE)
        # Add a Pybind11 target
        add_library(pybind11::pybind11 INTERFACE IMPORTED)
        target_include_directories(pybind11::pybind11
            INTERFACE ${PY_BUILD_PYBIND11_INCLUDE})
        target_link_libraries(pybind11::pybind11 INTERFACE Python3::Module)
        target_compile_features(pybind11::pybind11
            INTERFACE cxx_inheriting_constructors cxx_user_literals
                      cxx_right_angle_brackets)
    # If querying Python failed
    else()
        # Try finding it using CMake
        find_package(pybind11 REQUIRED CONFIG)
    endif()

endfunction()