"""
Tests for the py-build-cmake package.

 - Build all example and test projects
   - Run the package's pytest tests
   - Check the contents of the sdist and Wheel packages produced
 - Build the component backend example
   - Run the package's pytest tests
   - Check the contents of the Wheel packages produced
 - Test all three (+1) editable modes for the example and test projects
   -  Install in editable mode and run the package's pytest
 - Run the py-build-cmake pytest tests
"""

from __future__ import annotations

import hashlib
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

version = "0.3.4.dev0"
project_dir = Path(__file__).resolve().parent

examples = "minimal-program", "pybind11-project", "nanobind-project"
examples += "swig-project", "minimal"
test_packages = "namespace-project-a", "namespace-project-b"
test_packages += "bare-c-module", "cmake-preset", "cmake-options"

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
        with open_tar(sdist) as t:
            sdist_actual = sorted(t.getnames())
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
    with ZipFile(whl) as z:
        whl_actual = sorted(z.namelist())
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
    elif name == "nanobind-project":
        if py_v < (3, 8):
            ext_suffix = None  # skip
        elif impl.name == "cpython" and py_v >= (3, 12):
            ext_suffix = "." + ext_suffix.rsplit(".", 1)[-1]
            if sys.platform != "win32":
                ext_suffix = ".abi3" + ext_suffix
    elif name == "swig-project":  # noqa: SIM102
        if impl.name == "cpython" and py_v >= (3, 7):
            ext_suffix = "." + ext_suffix.rsplit(".", 1)[-1]
            if sys.platform != "win32":
                ext_suffix = ".abi3" + ext_suffix
    return ext_suffix


@nox.session
def find_python(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    with session.chdir("test-packages/find-python"):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        session.run("python", "-m", "build", ".", "-o", "dist-nox")


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


@nox.session
def reproducible(session: nox.Session):
    if os.name != "posix":
        session.skip("Skipping reproducible builds")
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.env["SOURCE_DATE_EPOCH"] = "1732565790"

    def build_and_hash(name):
        shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
        shutil.rmtree("dist-nox", ignore_errors=True)
        override = "override.cmake.options.REPRODUCIBLE_PROJECT_DIR=true"
        session.run("python", "-m", "build", "-o", "dist-nox", "-C", override)
        normname = re.sub(r"[-_.]+", "_", name).lower()
        plat = get_platform().replace(".", "_").replace("-", "_")
        sdist = Path(f"dist-nox/{normname}-{version}.tar.gz")
        whl_pattern = f"dist-nox/{normname}-{version}-*{plat}*.whl"
        whls = list(Path().glob(whl_pattern))
        if len(whls) != 1:
            session.error(f"Unexpected number of Wheels {whls} ({whl_pattern})")
        whl = whls[0]
        sdist_hash = hashlib.sha256(sdist.read_bytes()).hexdigest()
        whl_hash = hashlib.sha256(whl.read_bytes()).hexdigest()
        return sdist_hash, whl_hash

    test_proj = Path("test-packages/namespace-project-a")
    with session.chdir(test_proj):
        hashes = build_and_hash(test_proj.name)
    tmpdir = Path(session.create_tmp()).resolve()
    try:
        shutil.copytree(test_proj, tmpdir / test_proj.name)
        with session.chdir(tmpdir / test_proj.name):
            tmp_hashes = build_and_hash(test_proj.name)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(hashes)
    print(tmp_hashes)
    assert hashes == tmp_hashes


def test_editable(
    session: nox.Session, name: str, mode: str, dir: Path = Path("examples")
):
    ext_suffix = get_ext_suffix(name)
    if ext_suffix is None:
        return
    tmpdir = Path(session.create_tmp()).resolve()
    m = mode.split("+", 1)
    bh = len(m) > 1 and m[1] == "build_hook"
    skip_wrapper = ("namespace", "bare", "cmake-preset", "cmake-options")
    if m[0] == "wrapper" and any(k in name for k in skip_wrapper):
        return
    if m[0] == "symlink" and name == "minimal-program":
        return
    try:
        with session.chdir(dir / name):
            shutil.rmtree(".py-build-cmake_cache", ignore_errors=True)
            with (tmpdir / f"{mode}.toml").open("w") as f:
                f.write(f'[editable]\nmode = "{m[0]}"\n')
                f.write(f"build_hook = {str(bh).lower()}")
            args = ("--config-settings=--local=" + f.name,)
            if bh:
                args += ("--no-build-isolation",)
            session.install("-e", ".", *args)
            session.run("pytest")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@nox.session
@nox.parametrize("mode", ["symlink", "symlink+build_hook", "hook", "wrapper"])
def editable(session: nox.Session, mode):
    session.install(
        "-U",
        "pip",
        "build",
        "pytest",
        "pybind11~=2.13.5",
        "pybind11-stubgen~=2.5.1",
        "nanobind~=2.2.0",
        "swig~=4.3.0",
        "cmake",
        "ninja",
    )
    dist_dir = os.getenv("PY_BUILD_CMAKE_WHEEL_DIR")
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = str(Path(dist_dir).resolve())
    session.install(f"py-build-cmake=={version}")
    for name in examples:
        test_editable(session, name, mode)
    for name in test_packages:
        test_editable(session, name, mode, dir=Path("test-packages"))


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
