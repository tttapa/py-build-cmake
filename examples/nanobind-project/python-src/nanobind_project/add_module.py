"""Example module that adds two integers in C++."""

import os
import typing

if not typing.TYPE_CHECKING and os.getenv("NANOBIND_PROJECT_PYTHON_DEBUG"):
    from ._add_module_d import *  # noqa: F403
    from ._add_module_d import __version__  # noqa: F401
else:
    from ._add_module import *  # noqa: F403
    from ._add_module import __version__  # noqa: F401
