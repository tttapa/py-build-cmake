/**
 * @file    Example C++ extension for Python using nanobind that adds two
 *          integers.
 */

#include <cstdint>
#include <nanobind/nanobind.h>
namespace nb = nanobind;
using namespace nb::literals;

int32_t add(int32_t a, int32_t b) {
    return a + b;
}

NB_MODULE(MODULE_NAME, m) {
    m.doc()               = "Module for adding integers";
    m.attr("__version__") = VERSION_INFO;
    m.def("add",              // function name in Python
          add,                // C++ function
          "a"_a, "b"_a,       // Argument names in Python
          "Adds two integers" // Docstring in Python
    );
}
