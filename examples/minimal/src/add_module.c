#define PY_SSIZE_T_CLEAN
#include <Python.h>

PyDoc_STRVAR(
    docstring,
    "Simple module that adds integers. "
    "Based loosely on https://docs.python.org/3/extending/extending.html");

static PyObject *add_module_add(PyObject *self, PyObject *args) {
    (void) self;
    long a, b;
    if (!PyArg_ParseTuple(args, "ll", &a, &b))
        return NULL;
    long result = a + b;
    return PyLong_FromLong(result);
}

static PyMethodDef AddModuleMethods[] = {
    {"add", add_module_add, METH_VARARGS, "Add two integers."},
    {NULL, NULL, 0, NULL}, /* Sentinel */
};

static struct PyModuleDef add_module = {
    PyModuleDef_HEAD_INIT,
    "_add_module", /* name of module */
    docstring,     /* module documentation, may be NULL */
    -1,            /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    AddModuleMethods,
    NULL,
    NULL,
    NULL,
    NULL,
};

PyMODINIT_FUNC PyInit__add_module(void) { return PyModule_Create(&add_module); }