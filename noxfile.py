import nox
import os

@nox.session
def pybind11_project(session: nox.Session):
    session.install("-U", "pip")
    if dist_dir := os.getenv('PY_BUILD_CMAKE_WHEEL_DIR'):
        session.install("--find-links=" + dist_dir, "py-build-cmake")
    else:
        session.install(".")
    session.chdir("examples/pybind11-project")
    session.install("build")
    session.install("pybind11", "pybind11_stubgen", "mypy", "cmake", "ninja")
    session.run("python", "-m", "build", ".", "-n")
    session.install(".", "--no-build-isolation")
    session.install("pytest")
    session.run("pytest")

@nox.session
def tests(session: nox.Session):
    session.install("-U", "pip")
    if dist_dir := os.getenv('PY_BUILD_CMAKE_WHEEL_DIR'):
        session.install("--find-links=" + dist_dir, "py-build-cmake")
    else:
        session.install(".")
    session.install('pytest')
    session.run('pytest')
