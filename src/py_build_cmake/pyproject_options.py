from .config_options import *


def get_tool_pbc_path():
    return pth('pyproject.toml/tool/py-build-cmake')


def get_cross_path():
    return pth('pyproject.toml/tool/py-build-cmake/cross')


def get_options(config_path: Optional[Path] = None):
    root = ConfigOption("root")
    pyproject = root.insert(UncheckedConfigOption("pyproject.toml"))
    project = pyproject.insert(UncheckedConfigOption('project'))
    project.insert(UncheckedConfigOption('name', default=RequiredValue()))
    name_pth = pth('pyproject.toml/project/name')
    tool = pyproject.insert(
        UncheckedConfigOption("tool",
                              default=DefaultValueValue({}),
                              create_if_inheritance_target_exists=True))
    pbc = tool.insert(
        ConfigOption("py-build-cmake",
                     default=DefaultValueValue({}),
                     create_if_inheritance_target_exists=True))

    # [tool.py-build-cmake.module]
    module = pbc.insert(
        ConfigOption(
            "module",
            "Defines the name and the directory of the module to package.",
            default=DefaultValueValue({}),
        ))
    pbc_pth = get_tool_pbc_path()
    module.insert_multiple([
        StrConfigOption('name',
                        "Import name in Python (can be different from the "
                        "name on PyPI, which is defined in the [project] "
                        "section).",
                        default=RefDefaultValue(name_pth)),
        PathConfigOption('directory',
                         "Directory containing the Python package.",
                         default=DefaultValueValue("."),
                         base_path=config_path),
    ])

    # [tool.py-build-cmake.sdist]
    sdist = pbc.insert(
        ConfigOption(
            "sdist",
            "Specifies the files that should be included in the source "
            "distribution for this package.",
            default=DefaultValueValue({}),
            create_if_inheritance_target_exists=True,
        ))
    sdist_pth = pth('pyproject.toml/tool/py-build-cmake/sdist')
    sdist.insert_multiple([
        ListOfStrConfigOption('include',
                              "Files and folders to include in the source "
                              "distribution. May include the '*' wildcard "
                              "(but not '**' for recursive patterns).",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('exclude',
                              "Files and folders to exclude from the source "
                              "distribution. May include the '*' wildcard "
                              "(but not '**' for recursive patterns).",
                              default=DefaultValueValue([])),
    ])  # yapf: disable

    # [tool.py-build-cmake.cmake]
    cmake = pbc.insert(
        ConfigOption(
            "cmake",
            "Defines how to build the project to package. If omitted, "
            "py-build-cmake will produce a pure Python package.",
        ))
    cmake_pth = pth('pyproject.toml/tool/py-build-cmake/cmake')
    cmake.insert_multiple([
        StrConfigOption('minimum_version',
                        "Minimum required CMake version.",
                        "minimum_version = \"3.18\"",
                        default=NoDefaultValue()),
        StrConfigOption('build_type',
                        "Build type passed to the configuration step, as "
                        "-DCMAKE_BUILD_TYPE=<?>.",
                        "build_type = \"RelWithDebInfo\""),
        ListOfStrConfigOption('config',
                              "Configuration type passed to the build and "
                              "install steps, as --config <?>. You can "
                              "specify either a single string, or a list of "
                              "strings. If a multi-config generator is used, "
                              "all configurations in this list will be "
                              "included in the package.",
                              default=RefDefaultValue(pth('build_type'),
                                                      relative=True),
                              convert_str_to_singleton=True),
        StrConfigOption('generator',
                        "CMake generator to use, passed to the "
                        "configuration step, as "
                        "-G <?>."),
        PathConfigOption('source_path',
                         "Folder containing CMakeLists.txt.",
                         default=DefaultValueValue("."),
                         expected_contents=["CMakeLists.txt"],
                         base_path=config_path),
        PathConfigOption('build_path',
                         "CMake build and cache folder.",
                         default=DefaultValueValue('.py-build-cmake_cache'),
                         must_exist=False),
        DictOfStrConfigOption('options',
                              "Extra options passed to the configuration step, "
                              "as -D<option>=<value>.",
                              "options = {\"WITH_FEATURE_X\" = \"On\"}",
                              default=DefaultValueValue({})),
        ListOfStrConfigOption('args',
                              "Extra arguments passed to the configuration "
                              "step.",
                              "args = [\"--debug-find\", \"-Wdev\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('build_args',
                              "Extra arguments passed to the build step.",
                              "build_args = [\"-j\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('build_tool_args',
                              "Extra arguments passed to the build tool in the "
                              "build step (e.g. to Make or Ninja).",
                              "build_tool_args = [\"VERBOSE=1\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption('install_args',
                              "Extra arguments passed to the install step.",
                              "install_args = [\"--strip\"]",
                              default=DefaultValueValue([])),
        ListOfStrConfigOption("install_components",
                              "List of components to install, the install step "
                              "is executed once for each component, with the "
                              "option --component <?>.\n"
                              "Use an empty string to specify the default "
                              "component.",
                              default=DefaultValueValue([""])),
        DictOfStrConfigOption("env",
                              "Environment variables to set when running "
                              "CMake.",
                              default=DefaultValueValue({})),
    ])# yapf: disable

    # [tool.py-build-cmake.stubgen]
    stubgen = pbc.insert(
        ConfigOption(
            "stubgen",
            "If specified, mypy's stubgen utility will be used to generate "
            "typed stubs for the Python files in the package.",
        ))
    stubgen.insert_multiple([
        ListOfStrConfigOption('packages',
                              "List of packages to generate stubs for, passed "
                              "to stubgen as -p <?>."),
        ListOfStrConfigOption('modules',
                              "List of modules to generate stubs for, passed "
                              "to stubgen as -m <?>."),
        ListOfStrConfigOption('files',
                              "List of files to generate stubs for, passed to "
                              "stubgen without any flags."),
        ListOfStrConfigOption('args',
                              "List of extra arguments passed to stubgen.",
                              default=DefaultValueValue([])),
    ]) # yapf: disable

    # [tool.py-build-cmake.{linux,windows,mac}]
    for system in ["Linux", "Windows", "Mac"]:
        name = system.lower()
        opt = pbc.insert(
            ConfigOption(
                name,
                f"Override options for {system}.",
                create_if_inheritance_target_exists=True,
                default=DefaultValueValue({}),
            ))
        opt.insert_multiple([
            ConfigOption("sdist",
                         f"{system}-specific sdist options.",
                         inherit_from=sdist_pth,
                         create_if_inheritance_target_exists=True),
            ConfigOption("cmake",
                         f"{system}-specific CMake options.",
                         inherit_from=cmake_pth,
                         create_if_inheritance_target_exists=True),
        ])

    # [tool.py-build-cmake.cross]
    cross = pbc.insert(
        ConfigOption(
            "cross",
            "Causes py-build-cmake to cross-compile the project.",
        ))
    cross_pth = get_cross_path()
    cross.insert_multiple([
        StrConfigOption('implementation',
                        "Identifier for the Python implementation.",
                        "implementation = 'cp' # CPython",
                        default=RequiredValue()),
        StrConfigOption('version',
                        "Python version, major and minor, without dots.",
                        "version = '310' # 3.10",
                        default=RequiredValue()),
        StrConfigOption('abi',
                        "Python ABI.",
                        "abi = 'cp310'",
                        default=RequiredValue()),
        StrConfigOption('arch',
                        "Operating system and architecture (no dots or "
                        "dashes, only underscores, all lowercase).",
                        "arch = 'linux_x86_64'",
                        default=RequiredValue()),
        PathConfigOption('toolchain_file',
                         "CMake toolchain file to use.",
                         default=RequiredValue(),
                         base_path=config_path),
        ListOfStrConfigOption('copy_from_native_build',
                              "If set, this will cause a native version of the "
                              "CMake project to be built and installed in a "
                              "temporary directory first, and the files in this "
                              "list will be copied to the final cross-compiled "
                              "package. This is useful if you need binary "
                              "utilities that run on the build system while "
                              "cross-compiling, or for things like stubs for "
                              "extension modules that cannot be generated while "
                              "cross-compiling.\n"
                              "May include the '*' wildcard "
                              "(but not '**' for recursive patterns)."),
        ConfigOption("sdist",
                     "Override sdist options when cross-compiling.",
                     inherit_from=sdist_pth,
                     create_if_inheritance_target_exists=True),
        ConfigOption("cmake",
                     "Override CMake options when cross-compiling.",
                     inherit_from=cmake_pth,
                     create_if_inheritance_target_exists=True),
    ]) # yapf: disable

    # local override
    root.insert(
        OverrideConfigOption("py-build-cmake.local.toml",
                             "Allows you to override the "
                             "settings in pyproject.toml",
                             targetpath=pbc_pth))

    # cross-compilation local override
    root.insert(
        OverrideConfigOption("py-build-cmake.cross.toml",
                             "Allows you to override the cross-"
                             "compilation settings in pyproject.toml",
                             targetpath=cross_pth))

    return root