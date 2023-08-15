import shutil
import nox
import os
import sys

@nox.session
def example_projects(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv('PY_BUILD_CMAKE_WHEEL_DIR')
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install("py-build-cmake~=0.2.0a4")
    with session.chdir("examples/minimal"):
        shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
        session.run("python", "-m", "build", ".")
        session.install(".")
        session.run("pytest")
    with session.chdir("examples/pybind11-project"):
        shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
        session.run("python", "-m", "build", ".")
        session.install(".")
        session.run("pytest")
    if sys.version_info >= (3, 8):
        with session.chdir("examples/nanobind-project"):
            shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
            session.run("python", "-m", "build", ".")
            session.install(".")
            session.run("pytest")
    with session.chdir("examples/minimal-program"):
        shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
        session.run("python", "-m", "build", ".")
        session.install(".")
        session.run("pytest")


@nox.session
def component(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv('PY_BUILD_CMAKE_WHEEL_DIR')
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install("py-build-cmake~=0.2.0a4")
    with session.chdir("examples/minimal-debug-component"):
        shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
        session.install(".")
        session.install("./debug")
        session.run("pytest")


def test_editable(session: nox.Session, mode: str):
    tmpdir = os.path.realpath(session.create_tmp())
    try:
        with session.chdir("examples/pybind11-project"):
            shutil.rmtree('.py-build-cmake_cache', ignore_errors=True)
            with open(os.path.join(tmpdir, f"{mode}.toml"), "w") as f:
                f.write(f"[editable]\nmode = \"{mode}\"")
            session.install("-e", ".", "--config-settings=--local=" + f.name)
            session.run("pytest")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@nox.session
def editable(session: nox.Session):
    session.install("-U", "pip", "build", "pytest")
    dist_dir = os.getenv('PY_BUILD_CMAKE_WHEEL_DIR')
    if dist_dir is None:
        session.run("python", "-m", "build", ".")
        dist_dir = "dist"
    session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
    session.install("py-build-cmake~=0.2.0a4")
    for mode in ("wrapper", "hook", "symlink"):
        test_editable(session, mode)


@nox.session
def tests(session: nox.Session):
    session.install("-U", "pip", "pytest")
    dist_dir = os.getenv('PY_BUILD_CMAKE_WHEEL_DIR')
    if dist_dir:
        session.env["PIP_FIND_LINKS"] = os.path.abspath(dist_dir)
        session.install("py-build-cmake~=0.2.0a4")
    else:
        session.install(".")
    session.run('pytest')
