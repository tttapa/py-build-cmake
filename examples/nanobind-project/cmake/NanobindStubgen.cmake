function(nanobind_stubgen target)

    find_package(Python REQUIRED COMPONENTS Interpreter)
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND ${Python_EXECUTABLE} -m nanobind_stubgen
                --out $<TARGET_FILE_DIR:${target}>
                $<TARGET_FILE_BASE_NAME:${target}>
        WORKING_DIRECTORY $<TARGET_FILE_DIR:${target}>
        USES_TERMINAL)

endfunction()

function(nanobind_stubgen_install target destination)

    install(FILES
        $<TARGET_FILE_DIR:${target}>/$<TARGET_FILE_BASE_NAME:${target}>.pyi
        RENAME __init__.pyi
        EXCLUDE_FROM_ALL
        COMPONENT python_modules
        DESTINATION ${destination}/$<TARGET_FILE_BASE_NAME:${target}>)

endfunction()