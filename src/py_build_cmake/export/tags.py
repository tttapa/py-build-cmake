from typing import Dict, Any, Optional, List
import re
from copy import copy

from .native_tags import get_native_tags, WheelTags


def get_cross_tags(crosscfg: Dict[str, Any]) -> WheelTags:
    """Get the PEP 425 tags to use when cross-compiling."""
    tags = get_native_tags()
    if "implementation" in crosscfg and "version" in crosscfg:
        tags["pyver"] = [crosscfg["implementation"] + crosscfg["version"]]
    if "abi" in crosscfg:
        tags["abi"] = [crosscfg["abi"]]
    if "arch" in crosscfg:
        tags["arch"] = [crosscfg["arch"]]
    return tags


def convert_abi_tag(abi_tag: str, cmake_cfg: Optional[dict]) -> str:
    """Set the ABI tag to 'none' or 'abi3', depending on the config options
    specified by the user."""
    if not cmake_cfg:
        return "none"
    elif cmake_cfg["python_abi"] == "auto":
        return abi_tag
    elif cmake_cfg["python_abi"] == "none":
        return "none"
    elif cmake_cfg["python_abi"] == "abi3":
        # Only use abi3 if we're actually building for CPython
        m = re.match(r"^cp(\d+).*$", abi_tag)
        if m and int(m[1]) >= cmake_cfg["abi3_minimum_cpython_version"]:
            return "abi3"
        return abi_tag
    else:
        assert False, "Unsupported python_abi"


def convert_wheel_tags(
    tags: Dict[str, List[str]], cmake_cfg: Optional[dict]
) -> WheelTags:
    """Apply convert_abi_tag to each of the abi tags."""
    tags = copy(tags)
    cvt_abi = lambda tag: convert_abi_tag(tag, cmake_cfg)
    tags["abi"] = list(map(cvt_abi, tags["abi"]))
    if "none" in tags["abi"]:
        tags["pyver"] = ["py3"]
    return tags


def is_pure(cmake_cfg: Optional[dict]) -> bool:
    """Check if the package is a pure-Python package without platform-
    specific binaries."""
    if not cmake_cfg:
        return True
    return cmake_cfg["pure_python"]
