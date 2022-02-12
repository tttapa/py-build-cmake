"""Example module that adds two integers in C++."""

import os
import typing
if not typing.TYPE_CHECKING and os.getenv('PYBIND11_PROJECT_PYTHON_DEBUG'):
    from pybind11_project._add_module_d import *
    from pybind11_project._add_module_d import __version__
else:
    from pybind11_project._add_module import *
    from pybind11_project._add_module import __version__
