#include <pybind11/pybind11.h>
using pybind11::operator""_a;

PYBIND11_MODULE(MODULE_NAME, m) {
    m.doc()               = "Module for adding integers";
    m.attr("__version__") = VERSION_INFO;
    m.def(
        "add", [](int a, int b) { return a + b; }, "a"_a, "b"_a,
        "Adds two integers");
}