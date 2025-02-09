from __future__ import annotations

from string import Template
from typing import Mapping

from .options.string import StringOption


def substitute_environment_options(
    env: dict[str, str], config_env: Mapping[str, StringOption | None]
):
    """Given the environment-like options in config_env, update the environment
    in env. Supports simple template expansion using ${VAR}."""

    def _template_expand(a):
        return Template(a).substitute(env)

    for k, v in config_env.items():
        if v is None:
            continue
        assert isinstance(v, StringOption)
        # Perform template substitution on the different components
        for attr in "value", "append", "append_path", "prepend", "prepend_path":
            a = getattr(v, attr)
            if a is not None:
                setattr(v, attr, _template_expand(a))
        if v.remove:
            v.remove = [_template_expand(r) for r in v.remove]
        # If we're appending or prepending to the original value, we need
        # to set the initial value to the current value in the environment
        if (
            k in env
            and not v.value
            and (v.append or v.prepend or v.append_path or v.prepend_path)
        ):
            v.value = env[k]
        str_v = v.finalize()
        if str_v is not None:
            env[k] = str_v
        elif k in env:
            del env[k]
