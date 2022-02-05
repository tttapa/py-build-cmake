import shutil
import nox
import os

@nox.session
def example_projects(session: nox.Session):
    session.install("-U", "pip")
    if dist_dir := os.getenv('PY_BUILD_CMAKE_WHEEL_DIR'):
        session.install("--find-links=" + dist_dir, "py-build-cmake")
    else:
        session.install(".")
    session.install("build", "pytest", "cmake", "ninja")
    with session.chdir("examples/minimal"):
        session.install("mypy")
        shutil.rmtree('.py-build-cmake_cache')
        session.run("python", "-m", "build", ".", "-n")
        session.install(".", "--no-build-isolation")
        session.run("pytest")
    with session.chdir("examples/pybind11-project"):
        session.install("pybind11", "pybind11_stubgen", "mypy")
        shutil.rmtree('.py-build-cmake_cache')
        session.run("python", "-m", "build", ".", "-n")
        session.install(".", "--no-build-isolation")
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
