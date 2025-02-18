from __future__ import annotations

from pathlib import Path, PurePosixPath

from ...common import CMAKE_MINIMUM_REQUIRED
from .bool import BoolConfigOption
from .cmake_opt import CMakeOptConfigOption
from .config_option import ConfigOption, MultiConfigOption, UncheckedConfigOption
from .config_path import ConfPath
from .default import DefaultValueValue, NoDefaultValue, RefDefaultValue, RequiredValue
from .dict import DictOfStrConfigOption
from .dir_pattern import DirPatternsConfigOption
from .enum import EnumConfigOption
from .int import IntConfigOption
from .list import ListOfStrConfigOption
from .path import PathConfigOption, RelativeToCurrentConfig, RelativeToProject
from .string import StringConfigOption


def get_tool_pbc_path():
    return ConfPath.from_string("pyproject.toml/tool/py-build-cmake")


def get_component_path():
    return ConfPath.from_string("pyproject.toml/tool/py-build-cmake/component")


def get_cross_path():
    return ConfPath.from_string("pyproject.toml/tool/py-build-cmake/cross")


def get_options(project_path: Path | PurePosixPath, *, test: bool = False):
    root = ConfigOption("root")
    pyproject = root.insert(UncheckedConfigOption("pyproject.toml"))
    project = pyproject.insert(UncheckedConfigOption("project"))
    project.insert(UncheckedConfigOption("name", default=RequiredValue()))
    name_pth = ConfPath.from_string("pyproject.toml/project/name")
    tool = pyproject.insert(
        UncheckedConfigOption("tool",
                              default=DefaultValueValue({}),
                              create_if_inheritance_target_exists=True,
        ))  # fmt: skip
    pbc = tool.insert(
        ConfigOption("py-build-cmake",
                     default=DefaultValueValue({}),
                     create_if_inheritance_target_exists=True,
        ))  # fmt: skip
    # TODO: we should warn if these are present in the main config
    pbc.insert_multiple([
        UncheckedConfigOption("main_project"),
        UncheckedConfigOption("component"),
    ])  # fmt: skip

    # [tool.py-build-cmake.module]
    module = pbc.insert(
        ConfigOption("module",
                     "Defines the import name of the module or package, and "
                     "the directory where it can be found.",
                     default=DefaultValueValue({}),
        ))  # fmt: skip
    module.insert_multiple([
        StringConfigOption("name",
                           "Import name in Python (can be different from the "
                           "name on PyPI, which is defined in the [project] "
                           "section).",
                        default=RefDefaultValue(name_pth)),
        PathConfigOption("directory",
                         "Directory containing the Python module/package.",
                         default=DefaultValueValue("."),
                         base_path=RelativeToProject(project_path),
                         must_exist=not test),
        BoolConfigOption("namespace",
                         "Set to true for PEP 420 namespace packages.",
                         default=DefaultValueValue(False)),
        EnumConfigOption("generated",
                         "Do not try to locate the main module in the source "
                         "directory, but assume that it is generated by CMake. "
                         "Dynamic metadata cannot be used when set.",
                         options=["module", "package"]),
    ])  # fmt: skip

    # [tool.py-build-cmake.editable]
    editable = pbc.insert(
        ConfigOption("editable",
                     "Defines how to perform an editable install (PEP 660). "
                     "See <{docs_url}/usage/editable-install.{docs_ext}> for "
                     "more information.",
                     default=DefaultValueValue({}),
        ))  # fmt: skip
    editable_pth = ConfPath.from_string("pyproject.toml/tool/py-build-cmake/editable")
    editable.insert_multiple([
        EnumConfigOption("mode",
                         "Mechanism to use for editable installations. "
                         "Either write a wrapper `__init__.py` file, install "
                         "an import hook, or install symlinks to the original "
                         "files.",
                         default=DefaultValueValue("symlink"),
                         options=["wrapper", "hook", "symlink"]),
        BoolConfigOption("build_hook",
                         "Automatically re-build any changed files and C "
                         "extension modules when the package is first "
                         "imported by Python. It is recommended to use a fast "
                         "generator like Ninja. Currently, the only "
                         "mode that supports build hooks is `symlink`.",
                         default=DefaultValueValue(False)),
    ])  # fmt: skip

    # [tool.py-build-cmake.sdist]
    sdist = pbc.insert(
        ConfigOption("sdist",
                     "Specifies the files that should be included in the "
                     "source distribution for this package.",
                     default=DefaultValueValue({}),
                     create_if_inheritance_target_exists=True,
        ))  # fmt: skip
    sdist_pth = ConfPath.from_string("pyproject.toml/tool/py-build-cmake/sdist")
    sdist.insert_multiple([
        DirPatternsConfigOption("include",
                                "Files and folders to include in the source "
                                "distribution. May include the '*' wildcard "
                                "or '**' for recursive patterns.",
                                default=DefaultValueValue([])),
        DirPatternsConfigOption("exclude",
                                "Files and folders to exclude from the source "
                                "distribution. May include the '*' wildcard "
                                "or '**' for recursive patterns.",
                                default=DefaultValueValue([])),
    ])  # fmt: skip

    # [tool.py-build-cmake.cmake]
    cmake = pbc.insert(
        MultiConfigOption("cmake",
                     "Defines how to build the project to package. If omitted, "
                     "py-build-cmake will produce a pure Python package.",
        ))  # fmt: skip
    cmake_pth = ConfPath.from_string("pyproject.toml/tool/py-build-cmake/cmake")
    cmake.insert_multiple([
        StringConfigOption("minimum_version",
                           "Minimum required CMake version. Used for policies "
                           "in the automatically generated CMake cache pre-"
                           "load files. If this version is not available in "
                           "the system PATH, it will be installed "
                           "automatically as a build dependency (using Pip).",
                           "minimum_version = \"3.18\"",
                           default=DefaultValueValue(CMAKE_MINIMUM_REQUIRED)),
        StringConfigOption("build_type",
                           "Build type passed to the configuration step, as "
                           "`-DCMAKE_BUILD_TYPE=<?>`.",
                           "build_type = \"RelWithDebInfo\""),
        ListOfStrConfigOption("config",
                              "Configuration type passed to the build step, "
                              "as `--config <?>`. You can specify either a "
                              "single string, or a list of strings. If a "
                              "multi-config generator is used, all "
                              "configurations in this list will be built.",
                              "config = [\"Debug\", \"Release\"]",
                              default=RefDefaultValue(
                                  ConfPath.from_string("build_type"),
                                  relative=True,
                              ),
                              convert_str_to_singleton=True),
        StringConfigOption("preset",
                           "CMake preset to use for configuration. Passed as "
                           "`--preset <?>` during the configuration phase."),
        ListOfStrConfigOption('build_presets',
                              "CMake presets to use for building. Passed as "
                              "`--preset <?>` during the build phase, once "
                              "for each preset.",
                              default=None,
                              convert_str_to_singleton=True),
        StringConfigOption("generator",
                           "CMake generator to use, passed to the "
                           "configuration step, as "
                           "`-G <?>`. If Ninja is used, and if it is not "
                           "available in the system PATH, it will be installed "
                           "automatically as a build dependency.",
                           "generator = \"Ninja Multi-Config\""),
        PathConfigOption("source_path",
                         "Folder containing CMakeLists.txt.",
                         default=DefaultValueValue("."),
                         expected_contents=[] if test else ["CMakeLists.txt"],
                         base_path=RelativeToProject(project_path),
                         must_exist=not test),
        PathConfigOption("build_path",
                         "CMake build and cache folder. The placeholder "
                         "`{build_config}` can be used to insert the name of "
                         "the Python version and ABI, operating system, and "
                         "architecture. This ensures that separate build "
                         "directories are used for different host systems and "
                         "Python versions/implementations.",
                         default=DefaultValueValue(".py-build-cmake_cache/{build_config}"),
                         allow_abs=True,
                         base_path=RelativeToProject(project_path),
                         must_exist=False),
        CMakeOptConfigOption("options",
                             "Extra options passed to the configuration step, "
                             "as `-D<option>=<value>`.\n"
                             "Note that setting `CMAKE_OSX_DEPLOYMENT_TARGET` "
                             "here is not supported, see "
                             "<{docs_url}/usage/faq.{docs_ext}#how-to-set-the-"
                             "minimum-supported-macos-version>.",
                             "options = {\"WITH_FEATURE_X\" = true}",
                             default=DefaultValueValue({})),
        ListOfStrConfigOption("args",
                              "Extra arguments passed to the configuration "
                              "step.",
                              "args = [\"--debug-find\", \"-Wdev\"]",
                              default=DefaultValueValue([]),
                              append_by_default=True),
        BoolConfigOption("find_python",
                         "Specify hints for CMake's FindPython module.",
                         "find_python = false",
                         default=DefaultValueValue(True)),
        BoolConfigOption("find_python3",
                         "Specify hints for CMake's FindPython3 module.",
                         "find_python3 = false",
                         default=DefaultValueValue(True)),
        ListOfStrConfigOption("build_args",
                              "Extra arguments passed to the build step.",
                              "build_args = [\"-j\", \"--target\", \"foo\"]",
                              default=DefaultValueValue([]),
                              append_by_default=True),
        ListOfStrConfigOption("build_tool_args",
                              "Extra arguments passed to the build tool in the "
                              "build step (e.g. to Make or Ninja).",
                              "build_tool_args = "
                              "[\"--verbose\", \"-d\", \"explain\"]",
                              default=DefaultValueValue([]),
                              append_by_default=True),
        ListOfStrConfigOption("install_config",
                              "Configuration types passed to the "
                              "install step, as `--config <?>`. You can "
                              "specify either a single string, or a list of "
                              "strings. If a multi-config generator is used, "
                              "all configurations in this list will be "
                              "included in the package.",
                              "install_config = [\"Debug\", \"Release\"]",
                              default=RefDefaultValue(
                                  ConfPath.from_string("config"),
                                  relative=True,
                              ),
                              convert_str_to_singleton=True),
        ListOfStrConfigOption("install_args",
                              "Extra arguments passed to the install step.",
                              "install_args = [\"--strip\"]",
                              default=DefaultValueValue([]),
                              append_by_default=True),
        ListOfStrConfigOption("install_components",
                              "List of components to install, the install step "
                              "is executed once for each component, with the "
                              "option `--component <?>`.\n"
                              "Use an empty string to specify the default "
                              "component.",
                              default=DefaultValueValue([""])),
        DictOfStrConfigOption("env",
                              "Environment variables to set when running "
                              "CMake. Supports variable expansion using "
                              "`${VAR}`. Use a double dollar sign `$$` to "
                              "insert a literal `$`.\n"
                              "Note that setting `MACOSX_DEPLOYMENT_TARGET` "
                              "here is not supported, see "
                             "<{docs_url}/usage/faq.{docs_ext}#how-to-set-the-"
                             "minimum-supported-macos-version>.",
                              "env = { \"CMAKE_PREFIX_PATH\" "
                              "= \"${HOME}/.local\" }",
                              default=DefaultValueValue({}),
                              finalize_to_str=False),
    ])  # fmt: skip

    # [tool.py-build-cmake.wheel]
    wheel = pbc.insert(
        ConfigOption("wheel",
                     "Defines how to create the Wheel package.",
                     default=DefaultValueValue({}),
        ))  # fmt: skip
    wheel_pth = ConfPath.from_string("pyproject.toml/tool/py-build-cmake/wheel")
    wheel.insert_multiple([
        BoolConfigOption("pure_python",
                         "Indicate that this package contains no platform-"
                         "specific binaries, only Python scripts and other "
                         "platform-agnostic files. Setting this value to true "
                         "causes the Wheel tags to be set to `py3-none-any`, "
                         "and selects the `purelib` folder instead of "
                         "`platlib`.\n"
                         "If unset, the value depends on whether the `cmake` "
                         "option is set.",
                         "pure_python = true"),
        ListOfStrConfigOption("python_tag",
                              "Override the default Python tag for the Wheel "
                              "package.\n"
                              "If your package contains any Python extension "
                              "modules, you want to set this to `auto`.\n"
                              "For details about platform compatibility tags, "
                              "see the PyPA specification: "
                              "<https://packaging.python.org/en/latest/"
                              "specifications/platform-compatibility-tags>",
                              "python_tag = ['py2', 'py3']",
                              convert_str_to_singleton=True,
                              default=DefaultValueValue("auto")),
        EnumConfigOption("python_abi",
                         "Override the default ABI tag for the Wheel package.\n"
                         "For packages with a Python extension module that "
                         "make use of the full Python C API, this option "
                         "should be set to `auto`.\n"
                         "If your package does not contain Python extension "
                         "modules (e.g. because it only includes executables "
                         "to run as a subprocess, or only shared library files "
                         "to be loaded using `ctypes`), you can set this to "
                         "`none`.\n"
                         "If your package only includes Python extension "
                         "modules that use the CPython stable ABI, set this "
                         "to `abi3` (see also `abi3_minimum_cpython_version` "
                         "below).\n"
                         "For details about platform compatibility tags, see "
                         "the PyPA specification: <https://packaging.python.org/"
                         "en/latest/specifications/platform-compatibility-tags>",
                         "python_abi = 'none'",
                         default=DefaultValueValue("auto"),
                         options=["auto", "none", "abi3"]),
        IntConfigOption("abi3_minimum_cpython_version",
                        "If `python_abi` is set to `abi3`, only use the stable "
                        "CPython API for CPython version that are newer than "
                        "`abi3_minimum_version`. Useful for nanobind, which "
                        "supports the stable ABI for CPython 12 and later.\n"
                        "This option only applies to CPython using the stable "
                        "ABI, in which case it has the following effect: the "
                        "Python tag of the resulting wheel is set to the given "
                        "version of CPython, and the ABI tag of the wheel is "
                        "set to ABI3.\n"
                        "The Python version is encoded as a single integer, "
                        "consisting of the major and minor version numbers, "
                        "without a dot (the same format as the Python tag).\n"
                        "This value should match the value of the "
                        "`Py_LIMITED_API` macro used to build the Python "
                        "module. For example, if you're using "
                        "`abi3_minimum_cpython_version=312`, you should set "
                        "`Py_LIMITED_API=0x030C0000`. If you're using CMake's "
                        "`Python3_add_library` command, you should specify the "
                        "`USE_SABI 3.12` option.",
                        "abi3_minimum_cpython_version = 312",
                        default=DefaultValueValue(32)),
        ListOfStrConfigOption("abi_tag",
                              "Override the default ABI tag for the Wheel "
                              "package.\n"
                              "It is not recommended to set this value in "
                              "your pyproject.toml file directly. Instead, it "
                              "is intended to be specified from the command "
                              "line, or in a local override. "
                              "See also: cross.abi.\n"
                              "For details about platform compatibility tags, "
                              "see the PyPA specification: "
                              "<https://packaging.python.org/en/latest/"
                              "specifications/platform-compatibility-tags>",
                              "abi_tag = 'pypy310_pp73'",
                              convert_str_to_singleton=True,
                              default=NoDefaultValue()),
        ListOfStrConfigOption("platform_tag",
                              "Override the default platform tag for the Wheel "
                              "package.\n"
                              "The special value `guess` tries to select a "
                              "sensible value based on the environment and the "
                              "current Python interpreter (not supported when "
                              "cross-compiling).\n"
                              "It is not recommended to set this value in "
                              "your pyproject.toml file directly. Instead, it "
                              "is intended to be specified from the command "
                              "line, or in a local override. "
                              "See also: cross.arch.\n"
                              "There are no checks in place to ensure that the "
                              "platform tag applies to all files in the Wheel. "
                              "If possible, you should use a tool such as "
                              "auditwheel (<https://github.com/pypa/auditwheel>) or "
                              "delocate (<https://github.com/matthew-brett/delocate>) "
                              "to select the tag and to verify/fix the resulting "
                              "package.\n"
                              "For details about platform compatibility tags, "
                              "see the PyPA specification: "
                              "<https://packaging.python.org/en/latest/"
                              "specifications/platform-compatibility-tags>",
                              "platform_tag = 'manylinux_2_35_x86_64'",
                              convert_str_to_singleton=True,
                              default=NoDefaultValue()),
        StringConfigOption("build_tag",
                           "Add an optional build number to the Wheel "
                           "package. "
                           "Must start with a number and cannot contain "
                           "`-` characters.\n"
                           "It is not recommended to set this value in "
                            "your pyproject.toml file directly. Instead, it "
                            "is intended to be specified from the command "
                            "line, or in a local override.\n"
                           "For details about Wheel build tags, "
                           "see the PyPA specification: "
                           "<https://packaging.python.org/en/latest/"
                           "specifications/binary-distribution-format/"
                           "#file-name-convention>",
                           "build_tag = '1'",
                           default=NoDefaultValue()),
    ])  # fmt: skip
    # [tool.py-build-cmake.stubgen]
    stubgen = pbc.insert(
        ConfigOption("stubgen",
                     "If specified, mypy's stubgen utility will be used to "
                     "generate typed stubs for the Python files in the "
                     "package.",
        ))  # fmt: skip
    stubgen.insert_multiple([
        ListOfStrConfigOption("packages",
                              "List of packages to generate stubs for, passed "
                              "to stubgen as `-p <?>`."),
        ListOfStrConfigOption("modules",
                              "List of modules to generate stubs for, passed "
                              "to stubgen as `-m <?>`."),
        ListOfStrConfigOption("files",
                              "List of files to generate stubs for, passed to "
                              "stubgen without any flags."),
        ListOfStrConfigOption("args",
                              "List of extra arguments passed to stubgen.",
                              default=DefaultValueValue([]),
                              append_by_default=True),
    ])  # fmt: skip

    # [tool.py-build-cmake.{linux,windows,mac}]
    for system, system_name in (
        ("linux", "Linux"),
        ("windows", "Windows"),
        ("mac", "macOS"),
    ):
        opt = pbc.insert(
            ConfigOption(system,
                         f"Specific options for {system_name}.",
                         create_if_inheritance_target_exists=True,
                         default=DefaultValueValue({}),
            ))  # fmt: skip
        opt.insert_multiple([
            ConfigOption("editable",
                         f"{system_name}-specific editable options.",
                         inherit_from=editable_pth,
                         create_if_inheritance_target_exists=True),
            ConfigOption("sdist",
                         f"{system_name}-specific sdist options.",
                         inherit_from=sdist_pth,
                         create_if_inheritance_target_exists=True),
            MultiConfigOption("cmake",
                         f"{system_name}-specific CMake options.",
                         inherit_from=cmake_pth,
                         create_if_inheritance_target_exists=True),
            ConfigOption("wheel",
                         f"{system_name}-specific Wheel options.",
                         inherit_from=wheel_pth,
                         create_if_inheritance_target_exists=True),
        ])  # fmt: skip

    # [tool.py-build-cmake.cross]
    cross = pbc.insert(
        ConfigOption("cross",
                     "Causes py-build-cmake to cross-compile the project. See "
                     "<{docs_url}/usage/cross-compilation.{docs_ext}> for more "
                     "information.",
        ))  # fmt: skip
    cross.insert_multiple([
        EnumConfigOption("os",
                         "Operating system configuration to inherit from.",
                         options=["linux", "mac", "windows"]),
        StringConfigOption("implementation",
                           "Identifier for the Python implementation.\n"
                           "For details about platform compatibility tags, see "
                           "the PyPA specification: <https://packaging.python.org/"
                           "en/latest/specifications/platform-compatibility-tags>",
                           "implementation = 'cp' # CPython",
                           default=NoDefaultValue("same as current interpreter")),
        StringConfigOption("version",
                           "Python version, major and minor, without dots.\n"
                           "For details about platform compatibility tags, see "
                           "the PyPA specification: <https://packaging.python.org/"
                           "en/latest/specifications/platform-compatibility-tags>",
                           "version = '310' # 3.10",
                           default=NoDefaultValue("same as current interpreter")),
        StringConfigOption("abi",
                           "Python ABI.\n"
                           "For details about platform compatibility tags, see "
                           "the PyPA specification: <https://packaging.python.org/"
                           "en/latest/specifications/platform-compatibility-tags>",
                           "abi = 'cp310'",
                           default=NoDefaultValue("same as current interpreter")),
        StringConfigOption("arch",
                           "Platform tag, consisting of the operating system "
                           "and architecture (no dots or dashes, only "
                           "underscores, all lowercase).\n"
                           "For details about platform compatibility tags, see "
                           "the PyPA specification: <https://packaging.python.org/"
                           "en/latest/specifications/platform-compatibility-tags>",
                           "arch = 'linux_x86_64'",
                           default=NoDefaultValue("same as current interpreter")),
        PathConfigOption("prefix",
                         "Root path of the Python installation. "
                         "Used to set the `Python3_ROOT_DIR` CMake hint, "
                         "see <https://cmake.org/cmake/help/latest/module/"
                         "FindPython3.html#hints>.",
                         base_path=RelativeToCurrentConfig(project_path),
                         allow_abs=True,
                         is_folder=True,
                         must_exist=True,
                         default=None),
        PathConfigOption("library",
                         "Python library file (.so on Linux, .lib on Windows). "
                         "Used to set the `Python3_LIBRARY` CMake artifact, "
                         "see <https://cmake.org/cmake/help/latest/module/"
                         "FindPython3.html#artifacts-specification>.",
                         base_path=RelativeToCurrentConfig(project_path),
                         allow_abs=True,
                         is_folder=False,
                         must_exist=True,
                         default=None),
        PathConfigOption("include_dir",
                         "Python include directory (containing Python.h). "
                         "Used to set the `Python3_INCLUDE_DIR` CMake "
                         "artifact, "
                         "see <https://cmake.org/cmake/help/latest/module/"
                         "FindPython3.html#artifacts-specification>.",
                         base_path=RelativeToCurrentConfig(project_path),
                         allow_abs=True,
                         is_folder=True,
                         must_exist=True,
                         default=None),
        PathConfigOption("toolchain_file",
                         "CMake toolchain file to use. See "
                         "<https://cmake.org/cmake/help/book/mastering-cmake"
                         "/chapter/Cross%20Compiling%20With%20CMake.html> for "
                         "more information.",
                         default=None,
                         base_path=RelativeToCurrentConfig(project_path),
                         must_exist=not test,
                         allow_abs=True,
                         is_folder=False),
        StringConfigOption("generator_platform",
                           "The value for `CMAKE_GENERATOR_PLATFORM`. Only "
                           "applies to the Visual Studio generator on "
                           "Windows. See <https://cmake.org/cmake/help/"
                           "latest/variable/CMAKE_GENERATOR_PLATFORM.html> "
                           "for details.",
                           "generator_platform = 'ARM64'",
                           default=None),
        ConfigOption("editable",
                     "Override editable options when cross-compiling.",
                     inherit_from=editable_pth,
                     create_if_inheritance_target_exists=True),
        ConfigOption("sdist",
                     "Override sdist options when cross-compiling.",
                     inherit_from=sdist_pth,
                     create_if_inheritance_target_exists=True),
        MultiConfigOption("cmake",
                     "Override CMake options when cross-compiling.",
                     inherit_from=cmake_pth,
                     create_if_inheritance_target_exists=True),
        ConfigOption("wheel",
                     "Override Wheel options when cross-compiling.",
                     inherit_from=wheel_pth,
                     create_if_inheritance_target_exists=True),
    ])  # fmt: skip

    return root


def get_component_options(project_path: Path, *, test: bool = False):
    root = ConfigOption("root")
    pyproject = root.insert(UncheckedConfigOption("pyproject.toml"))
    project = pyproject.insert(UncheckedConfigOption("project"))
    project.insert(UncheckedConfigOption("name", default=RequiredValue()))
    tool = pyproject.insert(
        UncheckedConfigOption("tool",
                              default=DefaultValueValue({}),
                              create_if_inheritance_target_exists=True,
        ))  # fmt: skip
    pbc = tool.insert(
        ConfigOption("py-build-cmake",
                     default=DefaultValueValue({}),
                     create_if_inheritance_target_exists=True,
        ))  # fmt: skip
    # TODO: we should warn if these are present in a component config
    pbc.insert_multiple([
        UncheckedConfigOption("module"),
        UncheckedConfigOption("editable"),
        UncheckedConfigOption("sdist"),
        UncheckedConfigOption("cmake"),
        UncheckedConfigOption("wheel"),
        UncheckedConfigOption("stubgen"),
        UncheckedConfigOption("linux"),
        UncheckedConfigOption("windows"),
        UncheckedConfigOption("mac"),
        UncheckedConfigOption("cross"),
    ])  # fmt: skip

    # [tool.py-build-cmake.main_project]
    pbc.insert(
        PathConfigOption("main_project",
                         "Directory containing the main pyproject.toml file.",
                         default=DefaultValueValue(".."),
                         base_path=RelativeToProject(project_path),
                         must_exist=not test,
    ))  # fmt: skip
    # [tool.py-build-cmake.component]
    component = pbc.insert(
        MultiConfigOption("component",
                          "Options for a separately packaged component.",
                          default=DefaultValueValue({}),
    ))  # fmt: skip
    component.insert_multiple([
        ListOfStrConfigOption('build_presets',
                              "CMake presets to use for building. Passed as "
                              "`--preset <?>` during the build phase, once "
                              "for each preset.",
                              default=None,
                              convert_str_to_singleton=True),
        ListOfStrConfigOption("build_args",
                              "Extra arguments passed to the build step.",
                              "build_args = [\"-j\", \"--target\", \"foo\"]",
                              default=None,
                              append_by_default=True),
        ListOfStrConfigOption("build_tool_args",
                              "Extra arguments passed to the build tool in the "
                              "build step (e.g. to Make or Ninja).",
                              "build_tool_args = "
                              "[\"--verbose\", \"-d\", \"explain\"]",
                              default=None,
                              append_by_default=True),
        BoolConfigOption("install_only",
                         "Do not build the project, only install it.",
                         "install_only = true",
                         default=DefaultValueValue(False)),
        ListOfStrConfigOption("install_args",
                              "Extra arguments passed to the install step.",
                              "install_args = [\"--strip\"]",
                              default=None,
                              append_by_default=True),
        ListOfStrConfigOption("install_components",
                              "List of components to install, the install step "
                              "is executed once for each component, with the "
                              "option `--component <?>`.",
                              default=RequiredValue()),
    ])  # fmt: skip

    return root
