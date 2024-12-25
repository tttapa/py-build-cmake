function(pybind11_stubgen target)

    cmake_parse_arguments(STUBGEN "" "PACKAGE;DESTINATION;COMPONENT" "" ${ARGN})
    if (NOT DEFINED STUBGEN_PACKAGE)
        set(STUBGEN_PACKAGE ${PY_BUILD_CMAKE_IMPORT_NAME})
    endif()
    if (NOT DEFINED STUBGEN_DESTINATION)
        set(STUBGEN_DESTINATION "")
    endif()
    if (NOT DEFINED STUBGEN_COMPONENT)
        set(STUBGEN_COMPONENT "python_stubs")
    endif()

    if (NOT DEFINED Python3_EXECUTABLE)
        find_package(Python3 REQUIRED COMPONENTS Interpreter)
    endif()

    set(STUBGEN_MODULE ${STUBGEN_PACKAGE}.$<TARGET_FILE_BASE_NAME:${target}>)
    set(STUBGEN_CMD "\"${Python3_EXECUTABLE}\" -m pybind11_stubgen -o . --exit-code \"${STUBGEN_MODULE}\"")
    install(CODE "
        execute_process(COMMAND ${STUBGEN_CMD}
                        WORKING_DIRECTORY \"\${CMAKE_INSTALL_PREFIX}/${STUBGEN_DESTINATION}\"
                        RESULT_VARIABLE STUBGEN_RET)
        if(NOT STUBGEN_RET EQUAL 0)
            message(SEND_ERROR \"pybind11-stubgen ${STUBGEN_MODULE} failed.\")
        endif()
        " EXCLUDE_FROM_ALL COMPONENT ${STUBGEN_COMPONENT})

endfunction()
