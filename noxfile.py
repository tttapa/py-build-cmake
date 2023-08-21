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

import shutil
import nox
import os
import re
import sys
from tarfile import open as open_tar
from zipfile import ZipFile
from pathlib import Path
from difflib import unified_diff
from glob import glob
from distlib.util import get_platform

if sys.version_info < (3, 8):
    import distutils.sysconfig as dist_sysconfig
else:
    import sysconfig as dist_sysconfig

version = "0.2.0a6.dev0"
project_dir = Path(__file__).resolve().parent

examples = "minimal-program", "pybind11-project", "nanobind-project", "minimal"


def get_contents_subs(ext_suffix: str):
    if ext_suffix.endswith(".pyd"):
        dbg_suffix = ".pdb"
        exe_suffix = ".exe"
    else:
        dbg_suffix = ext_suffix + ".debug"
        exe_suffix = ""
    return dict(
        version=version,
        ext_suffix=ext_suffix,
        dbg_suffix=dbg_suffix,
        exe_suffix=exe_suffix,
    )


def check_pkg_contents(
    session: nox.Session, name: str, ext_suffix: str, with_sdist=True
):
    d = project_dir / "test" / "expected_contents" / name
    normname = re.sub(r"[-_.]+", "_", name).lower()
    plat = get_platform().replace(".", "_").replace("-", "_")
    subs = get_contents_subs(ext_suffix)
    # Compare sdist contents
    sdist = Path(f"dist-nox/{normname}-{version}.tar.gz")
    if with_sdist:
        sdist_expect = (d / "sdist.txt").read_text().format(**subs).split("\n")
        sdist_actual = sorted(open_tar(sdist).getnames())
        if sdist_expect != sdist_actual:
            diff = "\n".join(unified_diff(sdist_expect, sdist_actual))
            session.error("sdist contents mismatch:\n" + diff)
    # Find Wheel
    whl_pattern = f"dist-nox/{normname}-{version}-*{plat}*.whl"
    whls = glob(whl_pattern)
    if len(whls) != 1:
        session.error(f"Unexpected number of Wheels {whls} ({whl_pattern})")
    whl = whls[0]
    # Compare Wheel contents
    whl_expect = (d / "whl.txt").read_text().format(**subs).split("\n")
    whl_actual = sorted(ZipFile(whl).namelist())
    if whl_expect != whl_actual:
        diff = "\n".join(unified_diff(whl_expect, whl_actual))
        session.error("Wheel contents mismatch:\n" + diff)


def test_example_project(session: nox.Session, name: str, ext_suffix: str):
    with session.chdir("examples/" + name):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        session.run("python", "-m", "build", ".", "-o", "dist-nox")
        check_pkg_contents(session, name, ext_suffix)
        session.install(".")
        session.run("pytest")


def get_ext_suffix(name: str):
    impl = sys.implementation
    py_v = sys.version_info
    ext_suffix = dist_sysconfig.get_config_var("EXT_SUFFIX")
    assert isinstance(ext_suffix, str)
    if name == "minimal" and ext_suffix.endswith(".pyd") and py_v < (3, 8):
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
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install(f"py-build-cmake=={version}")
    for name in examples:
        ext_suffix = get_ext_suffix(name)
        if ext_suffix is not None:
            test_example_project(session, name, ext_suffix)


@nox.session
def component(session: nox.Session):
    if sys.platform != "linux" and sys.platform != "win32":
        return
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install(f"py-build-cmake=={version}")
    with session.chdir("examples/minimal-debug-component"):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        session.run("python", "-m", "build", "-w", ".", "-o", "dist-nox")
        session.run("python", "-m", "build", "-w", "./debug", "-o", "dist-nox")
        ext_suffix = get_ext_suffix("minimal")
        check_pkg_contents(session, "minimal-comp", ext_suffix, False)
        check_pkg_contents(session, "minimal-comp-debug", ext_suffix, False)
        session.install(".")
        session.install("./debug")
        session.run("pytest")


def test_editable(session: nox.Session, mode: str):
    tmpdir = os.path.realpath(session.create_tmp())
    try:
        with session.chdir("examples/pybind11-project"):
            shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
            with open(os.path.join(tmpdir, f"{mode}.toml"), "w") as f:
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
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install(f"py-build-cmake=={version}")
    for mode in "wrapper", "hook", "symlink":
        test_editable(session, mode)


@nox.session
def tests(session: nox.Session):
    session.install("-U", "pip", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir:
        session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
        session.install(f"py-build-cmake=={version}")
    else:
        session.install(".")
    session.run("pytest")
