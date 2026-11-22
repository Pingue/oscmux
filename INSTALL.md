# Build

            $ cmake -S . -B build
            $ cmake --build build

The binary is `build/oscmux`.

# Dependencies

oscmux needs a C compiler, CMake 3.10 or newer, liblo and Eina (from the Enlightenment Foundation Libraries).

## Ubuntu 24.04

            $ sudo apt-get install -y \
                        build-essential \
                        cmake \
                        pkg-config \
                        liblo-dev \
                        libefl-all-dev

Ubuntu 24.04 has no separate `libeina-dev` package; `libefl-all-dev` is the package that ships the Eina headers.
No include path workaround is needed.

## Older Debian/Ubuntu

The previous instructions used `libeina-dev` instead of `libefl-all-dev`. If `Efl_Config.h` is missing, add
`/usr/include/efl-1` (or `${PC_EINA_INCLUDE_DIRS}`) to the include directories in CMakeLists.txt.

## MAC

            $ sudo port install liblo eina
