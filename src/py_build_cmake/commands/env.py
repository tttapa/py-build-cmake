from __future__ import annotations

_SAFE_VALUES = (
    "",
    "0",
    "1",
    "off",
    "on",
    "false",
    "true",
)

_SAFE_PREFIXES = (
    "AUDITWHEEL_",
    "CIBW_",
    "CMAKE_",
    "LD_",
    "PIP_",
    "PKG_CONFIG_",
    "PY_BUILD_CMAKE_",
    "_PYPROJECT_HOOKS_",
)

_SAFE_VARIABLES = (
    "ARCHFLAGS",
    "CI",
    "CIBUILDWHEEL",
    "MACOSX_DEPLOYMENT_TARGET",
    "PATH",
    "PYTHONPATH",
    "PYTHONNOUSERSITE",
    "PWD",
    "RUNNER_OS",
    "RUNNER_ARCH",
    "SETUPTOOLS_EXT_SUFFIX",
    "VIRTUALENV_PIP",
    "VIRTUAL_ENV",
    "VIRTUAL_ENV_PROMPT",
    "_PYTHON_HOST_PLATFORM",
)


def filter_environment_for_logging(env: dict[str, str]) -> dict[str, str]:
    def is_safe_var(k: str, v: str):
        if v.lower() in _SAFE_VALUES:
            return True
        return k in _SAFE_VARIABLES or any(k.startswith(pfx) for pfx in _SAFE_PREFIXES)

    env = env.copy()
    for k in env:
        if not is_safe_var(k, env[k]):
            env[k] = "***  (set PY_BUILD_CMAKE_VERBOSE_ENV=1 to show)"
    return env
