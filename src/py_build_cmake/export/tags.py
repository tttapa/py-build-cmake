from __future__ import annotations

import re
from copy import copy
from typing import Any

from ..common.platform import BuildPlatformInfo, WheelTags


def get_cross_tags(plat: BuildPlatformInfo, crosscfg: dict[str, Any]) -> WheelTags:
    """Get the PEP 425 tags to use when cross-compiling."""
    tags = plat.get_native_tags(guess=False)
    if "implementation" in crosscfg and "version" in crosscfg:
        tags["pyver"] = [crosscfg["implementation"] + crosscfg["version"]]
    if "abi" in crosscfg:
        tags["abi"] = [crosscfg["abi"]]
    if "arch" in crosscfg:
        tags["arch"] = [crosscfg["arch"]]
    return tags


def _supports_abi3(abi_tag: str, wheel_cfg: dict):
    # Free-threading builds are incompatible with the stable ABI
    m = re.match(r"^cp([0-9dmu]+)t.*$", abi_tag)
    if m:
        return False
    # Only use abi3 if we're actually building for CPython, and if we're at
    # at least the minimum version specified by the user
    m = re.match(r"^cp(\d+).*$", abi_tag)
    return m and int(m[1]) >= wheel_cfg["abi3_minimum_cpython_version"]


def convert_abi_tag(abi_tag: str, wheel_cfg: dict) -> str:
    """Set the ABI tag to 'none' or 'abi3', depending on the config options
    specified by the user."""
    if wheel_cfg["python_abi"] == "auto":
        return abi_tag
    elif wheel_cfg["python_abi"] == "none":
        return "none"
    elif wheel_cfg["python_abi"] == "abi3":
        return "abi3" if _supports_abi3(abi_tag, wheel_cfg) else abi_tag
    else:
        msg = "Unsupported python_abi"
        raise AssertionError(msg)


def convert_pyver_tag(pyver_tag: str, wheel_cfg: dict, abi_tags: list[str]) -> str:
    """Convert the Python tag to the version specified by
    abi3_minimum_cpython_version if ABI3 is supported."""
    if wheel_cfg["python_abi"] == "abi3" and "abi3" in abi_tags:
        return f"cp{wheel_cfg['abi3_minimum_cpython_version']}"
    # By default, we don't change anything if ABI3 is not available or if this
    # is not a new enough version of CPython.
    return pyver_tag


def convert_wheel_tags(tags: WheelTags, wheel_cfg: dict) -> WheelTags:
    """Apply convert_abi_tag to each of the abi tags and override any tags
    that were specified in the config file."""
    tags = copy(tags)
    # Convert the given Python and ABI tags according to the "python_abi" and
    # "abi3_minimum_cpython_version" settings in the user's config.
    cvt_abi = lambda t: convert_abi_tag(t, wheel_cfg)
    tags["abi"] = [cvt_abi(t) for t in tags["abi"]]
    cvt_ver = lambda t: convert_pyver_tag(t, wheel_cfg, tags["abi"])
    tags["pyver"] = [cvt_ver(t) for t in tags["pyver"]]
    # Finally, override these "default" and "automatic" tags by any explicit
    # overrides specified by the user.
    if wheel_cfg["python_tag"] != ["auto"]:
        pyver = tags["pyver"][0]
        pyver_cfg = wheel_cfg["python_tag"]
        tags["pyver"] = [pyver if v == "auto" else v for v in pyver_cfg]
        tags["pyver"] = list(dict.fromkeys(tags["pyver"]))  # unique tags
    if "abi_tag" in wheel_cfg:
        tags["abi"] = wheel_cfg["abi_tag"]
    if "platform_tag" in wheel_cfg:
        plat = wheel_cfg["platform_tag"]  # Platform tags specified by the user
        guess = tags["arch"]  # Tags guessed based on the current interpreter
        # If the user-specified tags contain "guess", replace it by the guesses
        tags["arch"] = [x for t in plat for x in (guess if t == "guess" else [t])]
    return tags


def is_pure(wheel_cfg: dict, cmake_cfg: dict | None) -> bool:
    """Check if the package is a pure-Python package without platform-
    specific binaries."""
    if "pure_python" in wheel_cfg:
        return wheel_cfg["pure_python"]
    return not cmake_cfg
