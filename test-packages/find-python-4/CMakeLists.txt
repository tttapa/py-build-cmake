cmake_minimum_required(VERSION 4.0)

project(TestRequiredArtifacts LANGUAGES C)

block(SCOPE_FOR VARIABLES)
  # Look for the development files for the target first
  if (CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING_EMULATOR)
    find_package(Python3 REQUIRED COMPONENTS Development.Module)
  else()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
  endif()
  # Then look for the interpreter for the build system,
  # but return its variables using a different name
  set(Python3_ARTIFACTS_PREFIX "_BUILD")
  if (NOT DEFINED Python3_BUILD_EXECUTABLE)
    message(SEND_ERROR "Python3_BUILD_EXECUTABLE not defined")
  endif()
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  if (NOT Python3_BUILD_EXECUTABLE STREQUAL PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER)
    message(SEND_ERROR "Inconsistent Python3_BUILD_EXECUTABLE: '${Python3_BUILD_EXECUTABLE}' instead of '${PY_BUILD_CMAKE_BUILD_PYTHON_INTERPRETER}'")
  endif()
endblock()

block(SCOPE_FOR VARIABLES)
  find_package(Python3 REQUIRED COMPONENTS Development)
endblock()
block(SCOPE_FOR VARIABLES)
  find_package(Python3 REQUIRED COMPONENTS Development.Module)
endblock()
block(SCOPE_FOR VARIABLES)
  if (Python3_FIND_IMPLEMENTATIONS STREQUAL "CPython")
    find_package(Python3 REQUIRED COMPONENTS Development.Module Development.SABIModule)
  endif()
endblock()
block(SCOPE_FOR VARIABLES)
  find_package(Python3 REQUIRED COMPONENTS Development.Module
                       OPTIONAL_COMPONENTS Development.SABIModule)
endblock()
