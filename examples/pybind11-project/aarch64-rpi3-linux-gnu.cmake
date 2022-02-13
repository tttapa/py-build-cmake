# For more information, see 
# https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html and
# https://tttapa.github.io/Pages/Raspberry-Pi/C++-Development-RPiOS/index.html.

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_SYSROOT /var/lib/schroot/chroots/rpi3-impish-arm64)
SET(CMAKE_FIND_ROOT_PATH ${CMAKE_SYSROOT}) 
set(CMAKE_LIBRARY_ARCHITECTURE aarch64-linux-gnu)
set(CMAKE_STAGING_PREFIX $ENV{HOME}/RPi-dev/staging-aarch64-rpi3)

set(cross "aarch64-rpi3-linux-gnu")
set(CMAKE_C_COMPILER ${cross}-gcc)
set(CMAKE_CXX_COMPILER ${cross}-g++)
set(CMAKE_Fortran_COMPILER ${cross}-gfortran)

set(ARCH_FLAGS "-mcpu=cortex-a53+crc+simd")
SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${ARCH_FLAGS}")
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${ARCH_FLAGS}")
SET(CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} ${ARCH_FLAGS}")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE arm64)
