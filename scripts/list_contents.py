from zipfile import ZipFile
from tarfile import open as tar_open

tar_files = [
    "examples/minimal-program/dist-nox/minimal_program-0.2.0a5.dev0.tar.gz",
    "examples/minimal/dist-nox/minimal-0.2.0a5.dev0.tar.gz",
    "examples/pybind11-project/dist-nox/pybind11_project-0.2.0a5.dev0.tar.gz",
    "examples/nanobind-project/dist-nox/nanobind_project-0.2.0a5.dev0.tar.gz",
]

zip_files = [
    "examples/minimal-program/dist-nox/minimal_program-0.2.0a5.dev0-py3-none-linux_x86_64.whl",
    "examples/minimal/dist-nox/minimal-0.2.0a5.dev0-cp39-cp39-linux_x86_64.whl",
    "examples/pybind11-project/dist-nox/pybind11_project-0.2.0a5.dev0-cp39-cp39-linux_x86_64.whl",
    "examples/nanobind-project/dist-nox/nanobind_project-0.2.0a5.dev0-cp39-cp39-linux_x86_64.whl",
    "examples/minimal-debug-component/dist-nox/minimal_comp-0.2.0a5.dev0-cp39-cp39-linux_x86_64.whl",
    "examples/minimal-debug-component/dist-nox/minimal_comp_debug-0.2.0a5.dev0-cp39-cp39-linux_x86_64.whl",
]

for f in tar_files:
    print(*sorted(tar_open(f).getnames()), sep='\n', end='\n\n')
for f in zip_files:
    print(*sorted(ZipFile(f).namelist()), sep='\n', end='\n\n')
