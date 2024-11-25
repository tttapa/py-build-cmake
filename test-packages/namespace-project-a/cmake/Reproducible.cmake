# We want to avoid the temporary build paths used by PyPA build and pip to
# be included in the binaries, because that would make the whole package non-
# reproducible. Therefore, we strip out the paths of the build environment and
# of the project folder.
# https://reproducible-builds.org/docs/build-path/

set(PYTHON_DIRS ${Python3_STDLIB} ${Python3_STDARCH} ${Python3_SITELIB} ${Python3_SITEARCH})
list(REMOVE_DUPLICATES PYTHON_DIRS)
list(FILTER PYTHON_DIRS INCLUDE REGEX "/(pip-)?build-env-")
foreach(d PYTHON_DIRS)
    if (CMAKE_CXX_COMPILER_ID MATCHES "(^GNU$)|(Clang$)")
        add_compile_options("-ffile-prefix-map=${d}=/build-env")
    endif()
endforeach()

option(REPRODUCIBLE_PROJECT_DIR Off
    "Add a file prefix map for the project source directory itself")

if (REPRODUCIBLE_PROJECT_DIR)
    if (CMAKE_CXX_COMPILER_ID MATCHES "(^GNU$)|(Clang$)")
        add_compile_options("-ffile-prefix-map=${PROJECT_SOURCE_DIR}=/${PROJECT_NAME}")
    endif()
endif()
