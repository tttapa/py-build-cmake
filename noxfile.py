"""
Tests for the py-build-cmake package.

 - Build all example projects
   - Run the package's pytest tests
   - Check the contents of the sdist and Wheel packages produced
 - Build the component backend example
   - Run the package's pytest tests
   - Check the contents of the Wheel packages produced
 - Test all three editable modes for the pybind11-project example
   -  Install in editable mode and run the package's pytest
 - Run the py-build-cmake pytest tests
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from difflib import unified_diff
from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

import jinja2
import nox
from distlib.util import get_platform

if sys.version_info < (3, 8):
    import distutils.sysconfig as dist_sysconfig
else:
    import sysconfig as dist_sysconfig

version = "0.2.0a13.dev0"
project_dir = Path(__file__).resolve().parent

examples = "minimal-program", "pybind11-project", "nanobind-project", "minimal"
test_packages = "namespace-project-a", "namespace-project-b"
test_packages += "bare-c-module", "cmake-preset"

purity = {"namespace-project-b": True}


def get_contents_subs(ext_suffix: str):
    if ext_suffix.endswith(".pyd"):
        dbg_suffix = ".pdb"
        exe_suffix = ".exe"
    else:
        dbg_suffix = ext_suffix + ".debug"
        exe_suffix = ""
    return {
        "version": version,
        "ext_suffix": ext_suffix,
        "dbg_suffix": dbg_suffix,
        "exe_suffix": exe_suffix,
        "sys": {
            "version_info": sys.version_info,
            "implementation": sys.implementation,
            "platform": sys.platform,
        },
    }


def check_pkg_contents(
    session: nox.Session,
    name: str,
    ext_suffix: str,
    with_sdist=True,
    pure=False,
):
    d = project_dir / "tests" / "expected_contents" / name
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(d))
    normname = re.sub(r"[-_.]+", "_", name).lower()
    plat = "none" if pure else get_platform().replace(".", "_").replace("-", "_")
    subs = get_contents_subs(ext_suffix)
    # Compare sdist contents
    sdist = Path(f"dist-nox/{normname}-{version}.tar.gz")
    if with_sdist:
        sdist_template = template_env.get_template("sdist.txt")
        sdist_expect = sdist_template.render(**subs).split("\n")
        sdist_expect = sorted(filter(bool, sdist_expect))
        sdist_actual = sorted(open_tar(sdist).getnames())
        if sdist_expect != sdist_actual:
            diff = "\n".join(unified_diff(sdist_expect, sdist_actual))
            session.error("sdist contents mismatch:\n" + diff)
    # Find Wheel
    whl_pattern = f"dist-nox/{normname}-{version}-*{plat}*.whl"
    whls = list(Path().glob(whl_pattern))
    if len(whls) != 1:
        session.error(f"Unexpected number of Wheels {whls} ({whl_pattern})")
    whl = whls[0]
    # Compare Wheel contents
    whl_template = template_env.get_template("whl.txt")
    whl_expect = whl_template.render(**subs).split("\n")
    whl_expect = sorted(filter(bool, whl_expect))
    whl_actual = sorted(ZipFile(whl).namelist())
    if whl_expect != whl_actual:
        diff = "\n".join(unified_diff(whl_expect, whl_actual))
        session.error("Wheel contents mismatch:\n" + diff)


def test_example_project(
    session: nox.Session, name: str, ext_suffix: str, dir: Path = Path("examples")
):
    with session.chdir(dir / name):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        session.run("python", "-m", "build", ".", "-o", "dist-nox")
        pure = purity.get(name, False)
        check_pkg_contents(session, name, ext_suffix, pure=pure)
        session.install(".")
        session.run("pytest")


def get_ext_suffix(name: str):
    impl = sys.implementation
    py_v = sys.version_info
    ext_suffix = dist_sysconfig.get_config_var("EXT_SUFFIX")
    assert isinstance(ext_suffix, str)
    simple = name in ["minimal", "bare-c-module"]
    if simple and ext_suffix.endswith(".pyd") and py_v < (3, 8):
        ext_suffix = ".pyd"  # what a mess ...
    if name == "nanobind-project":
        if py_v < (3, 8):
            ext_suffix = None  # skip
        elif impl.name == "cpython" and py_v >= (3, 12):
            ext_suffix = "." + ext_suffix.rsplit(".", 1)[-1]
            if sys.platform != "win32":
                ext_suffix = ".abi3" + ext_suffix
    return ext_suffix


@nox.session
def example_projects(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    for name in examples:
        ext_suffix = get_ext_suffix(name)
        if ext_suffix is not None:
            test_example_project(session, name, ext_suffix)


@nox.session
def test_projects(session: nox.Session):
    dir = Path("test-packages")
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    for name in test_packages:
        ext_suffix = get_ext_suffix(name)
        if ext_suffix is not None:
            test_example_project(session, name, ext_suffix, dir=dir)


@nox.session
def component(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    with session.chdir("examples/minimal-debug-component"):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        session.run("python", "-m", "build", "-w", ".", "-o", "dist-nox")
        session.run("python", "-m", "build", "-w", "./debug", "-o", "dist-nox")
        ext_suffix = get_ext_suffix("minimal")
        if ext_suffix is not None:
            check_pkg_contents(session, "minimal-comp", ext_suffix, False)
            check_pkg_contents(session, "minimal-comp-debug", ext_suffix, False)
            session.install(".")
            session.install("./debug")
            session.run("pytest")


def test_editable(session: nox.Session, mode: str):
    tmpdir = Path(session.create_tmp()).resolve()
    try:
        with session.chdir("examples/pybind11-project"):
            shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
            with (tmpdir / f"{mode}.toml").open("w") as f:
                f.write(f'[editable]\nmode = "{mode}"')
            session.install("-e", ".", "--config-settings=--local=" + f.name)
            session.run("pytest")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@nox.session
def editable(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    for mode in "wrapper", "hook", "symlink":
        test_editable(session, mode)


@nox.session
def tests(session: nox.Session):
    session.install("-U", "pip", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir:
        session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
        session.install(f"py-build-cmake=={version}")
    else:
        session.install(".")
    session.run("pytest")
