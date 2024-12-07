# Based on https://gitlab.kitware.com/cmake/cmake/-/blob/ff65c5fca05ad11c564b2e193205f44b65376b6d/Tests/FindPython/RequiredArtifacts/CMakeLists.txt

# CMake - Cross Platform Makefile Generator
# Copyright 2000-2024 Kitware, Inc. and Contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# * Neither the name of Kitware, Inc. nor the names of Contributors
#   may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

cmake_minimum_required(VERSION 3.17)

project(TestRequiredArtifacts LANGUAGES C)

block(SCOPE_FOR VARIABLES)
  find_package(Python3 REQUIRED COMPONENTS Development.Module)
  if (NOT Python3_FOUND)
    message (FATAL_ERROR "Failed to find Python 3")
  endif()
  if (Python3_Development_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development' unexpectedly found")
  endif()
  if (Python3_Interpreter_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Interpreter' unexpectedly found")
  endif()
  if (Python3_Development.Embed_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.Embed' unexpectedly found")
  endif()
  if (Python3_Development.SABIModule_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.SABIModule' unexpectedly found")
  endif()
  if (NOT Python3_Development.Module_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.Module' not found")
  endif()
  message(STATUS "Python3_SOABI:  ${Python3_SOABI}")
  if (NOT WIN32 AND NOT Python3_SOABI)
    message (FATAL_ERROR "Python3, SOABI missing")
  endif()
  unset(_Python3_LIBRARY_RELEASE CACHE)
endblock()

block(SCOPE_FOR VARIABLES)
  find_package(Python3 REQUIRED COMPONENTS Development.SABIModule)
  if (NOT Python3_FOUND)
    message (FATAL_ERROR "Failed to find Python 3")
  endif()
  if (Python3_Development_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development' unexpectedly found")
  endif()
  if (Python3_Interpreter_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Interpreter' unexpectedly found")
  endif()
  if (Python3_Development.Embed_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.Embed' unexpectedly found")
  endif()
  if (Python3_Development.Module_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.Module' unexpectedly found")
  endif()
  if (NOT Python3_Development.SABIModule_FOUND)
    message (FATAL_ERROR "Python 3, COMPONENT 'Development.SABIModule' not found")
  endif()
  message(STATUS "Python3_SOSABI: ${Python3_SOSABI}")
  if (NOT WIN32 AND NOT Python3_SOSABI)
    message (FATAL_ERROR "Python3, SOSABI missing")
  endif()
  unset(_Python3_SABI_LIBRARY_RELEASE CACHE)
endblock()

block(SCOPE_FOR VARIABLES)
  # https://gitlab.kitware.com/cmake/cmake/-/issues/26493
  if (NOT WIN32 OR ${CMAKE_VERSION} VERSION_GREATER_EQUAL "3.31.2")
    find_package(Python3 REQUIRED COMPONENTS Development.Module Development.SABIModule)
    if (NOT Python3_FOUND)
      message (FATAL_ERROR "Failed to find Python 3")
    endif()
    if (Python3_Development_FOUND)
      message (FATAL_ERROR "Python 3, COMPONENT 'Development' unexpectedly found")
    endif()
    if (Python3_Interpreter_FOUND)
      message (FATAL_ERROR "Python 3, COMPONENT 'Interpreter' unexpectedly found")
    endif()
    if (Python3_Development.Embed_FOUND)
      message (FATAL_ERROR "Python 3, COMPONENT 'Development.Embed' unexpectedly found")
    endif()
    if (NOT Python3_Development.Module_FOUND)
      message (FATAL_ERROR "Python 3, COMPONENT 'Development.Module' not found")
    endif()
    if (NOT Python3_Development.SABIModule_FOUND)
      message (FATAL_ERROR "Python 3, COMPONENT 'Development.SABIModule' not found")
    endif()
    message(STATUS "Python3_SOSABI: ${Python3_SOSABI}")
    message(STATUS "Python3_SOABI:  ${Python3_SOABI}")
    if (NOT WIN32 AND NOT Python3_SOSABI)
      message (FATAL_ERROR "Python3, SOSABI missing")
    endif()
    if (NOT WIN32 AND NOT Python3_SOABI)
      message (FATAL_ERROR "Python3, SOABI missing")
    endif()
    unset(_Python3_LIBRARY_RELEASE CACHE)
    unset(_Python3_SABI_LIBRARY_RELEASE CACHE)
  endif()
endblock()
