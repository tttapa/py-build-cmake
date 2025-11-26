/**
 * @file    Example C++ extension for Python using Pybind11 that adds two
 *          integers.
 */

#include <cstdint>
#include <pybind11/pybind11.h>
#include <fmt/printf.h>

using namespace pybind11::literals;


int32_t add(int32_t a, int32_t b) {
    const std::string thing("World");
    fmt::print("PRINT: Hello {}!\n", thing);
    return a + b;
}

PYBIND11_MODULE(MODULE_NAME, m) {
    m.doc()               = "Module for adding integers";
    m.attr("__version__") = VERSION_INFO;
    m.def("add",              // function name in Python
          add,                // C++ function
          "a"_a, "b"_a,       // Argument names in Python
          "Adds two integers" // Docstring in Python
    );
}
