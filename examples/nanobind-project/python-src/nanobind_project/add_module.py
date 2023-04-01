"""Example module that adds two integers in C++."""

import os
import typing
if not typing.TYPE_CHECKING and os.getenv('NANOBIND_PROJECT_PYTHON_DEBUG'):
    from nanobind_project._add_module_d import *
    from nanobind_project._add_module_d import __version__
else:
    from nanobind_project._add_module import *
    from nanobind_project._add_module import __version__
