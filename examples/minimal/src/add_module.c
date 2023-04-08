/* Example based on https://docs.python.org/3/extending/extending.html */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* This is the addition function we wish to expose to Python. */
long add(long a, long b) {
    return a + b;
}

/* Docstring for our Python module. */
PyDoc_STRVAR(
    docstring,
    "Simple module that adds integers. "
    "Based loosely on https://docs.python.org/3/extending/extending.html");

/* Wrapper for our 'add' function, using the Python C API to get the function
   arguments as integers, and to return the result as a Python object. */
static PyObject *add_module_add(PyObject *self, PyObject *args) {
    (void)self;
    long a, b;
    if (!PyArg_ParseTuple(args, "ll", &a, &b))
        return NULL;
    long result = add(a, b);
    return PyLong_FromLong(result);
}

/* Define the functions/methods that this module exports. */
static PyMethodDef AddModuleMethods[] = {
    {"add", add_module_add, METH_VARARGS, "Add two integers."},
    {NULL, NULL, 0, NULL}, /* Sentinel */
};

/* Define the actual module. */
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

/* The main entry point that is called by Python when our module is imported. */
PyMODINIT_FUNC PyInit__add_module(void) {
    return PyModule_Create(&add_module);
}
