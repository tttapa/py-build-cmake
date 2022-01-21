#include <pybind11/pybind11.h>

PYBIND11_MODULE(MODULE_NAME, m) {
    m.doc()               = "Module for adding integers";
    m.attr("__version__") = VERSION_INFO;
    m.def("add", [](int a, int b) { return a + b; }, "Adds two integers");
}