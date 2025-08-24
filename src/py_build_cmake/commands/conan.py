from __future__ import annotations

import contextlib
import logging
import os
import shlex
import textwrap
import types
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any, Mapping, cast

import conan  # type: ignore[import-untyped]
import conan.api.conan_api  # type: ignore[import-untyped]
import conan.cli.cli  # type: ignore[import-untyped]
import conan.tools.cmake  # type: ignore[import-untyped]
import conan.tools.env  # type: ignore[import-untyped]

from ..commands.cmd_runner import CommandRunner
from ..common import ConfigError, PackageInfo
from ..common.platform import BuildPlatformInfo, OSIdentifier
from ..common.util import (
    archs_to_conan_arch,
    os_to_conan_os,
    sysconfig_platform_to_conan_arch,
)
from ..config.options.string import StringOption
from .builder import Builder, PackageTags, PythonSettings
from .chdir import chdir
from .file import VerboseFile

logger = logging.getLogger(__name__)


@dataclass
class ConanSettings:
    output_folder: Path
    build_profiles: list[str]
    host_profiles: list[str]
    extra_host_profile_data: dict[str, list[str]]
    build_config_name: str
    args: list[str]


@dataclass
class CMakeSettings:
    minimum_required: str
    maximum_policy: str | None


@dataclass
class CMakeConfigureSettings:
    working_dir: Path
    source_path: Path
    os: OSIdentifier
    cross_compiling: bool
    toolchain_file: Path | None
    environment: dict
    build_type: str | None
    options: dict[str, str]
    args: list[str]
    generator: str | None


@dataclass
class CMakeBuildSettings:
    args: list[str]
    tool_args: list[str]
    configs: list[str]


@dataclass
class CMakeInstallSettings:
    args: list[str]
    configs: list[str]
    components: list[str]
    prefix: Path | None


_CMAKE_TOOLCHAIN_POLICY = "3.5...4.1"


_SPECIAL_CMAKE_OPTIONS = {
    "system_name",
    "system_processor",
    "system_version",
    "toolset_arch",
}

_MODULE_LINK_FLAGS = {  # https://github.com/conan-io/conan/issues/17539
    f"CMAKE_MODULE_LINKER_FLAGS{c}_INIT": f"${{CMAKE_SHARED_LINKER_FLAGS{c}_INIT}}"
    for c in ("", "_DEBUG", "_RELEASE", "_RELWITHDEBINFO")
}


class ConanCMaker(Builder):

    def __init__(
        self,
        plat: BuildPlatformInfo,
        package_info: PackageInfo,
        package_tags: PackageTags,
        python_settings: PythonSettings,
        conan_settings: ConanSettings,
        cmake_settings: CMakeSettings,
        conf_settings: CMakeConfigureSettings,
        build_settings: CMakeBuildSettings,
        install_settings: CMakeInstallSettings,
        runner: CommandRunner,
    ):
        super().__init__(plat, package_info, package_tags, python_settings, runner)
        self.conan_settings = conan_settings
        self.cmake_settings = cmake_settings
        self.conf_settings = conf_settings
        self.build_settings = build_settings
        self.install_settings = install_settings
        self.conanfile: conan.ConanFile | None = None
        self.buildenv: conan.tools.env.VirtualBuildEnv | None = None

        self.check_environment(self.conf_settings.environment)
        self.check_cmake_options(self.conf_settings.options)

    def check_cmake_options(self, opts: dict[str, Any]):
        super().check_cmake_options(opts)
        if "CMAKE_BUILD_TYPE" in self.conf_settings.options:
            msg = "Setting CMAKE_BUILD_TYPE as a CMake option is not "
            msg += "supported. Please set 'settings.build_type' in the "
            msg += "selected Conan host profile instead."
            logger.warning(msg)
        for o in _SPECIAL_CMAKE_OPTIONS:
            key = "CMAKE_" + o.upper()
            v = self.conf_settings.options.pop(key, None)
            if v:
                msg = f"Setting {key} as a CMake option is not supported. "
                msg += f"Please set 'tools.cmake.cmaketoolchain:{o}' in the "
                msg += "selected Conan host profile instead."
                logger.warning(msg)

    def cross_compiling(self) -> bool:
        return self.conf_settings.cross_compiling

    def get_native_python_abi_tuple(self):
        cmake_version = self.cmake_settings.minimum_required
        return super()._get_native_python_abi_tuple(cmake_version)

    @property
    def cmake_version_policy(self):
        """Determine argument for cmake_minimum_required(VERSION X)."""
        version = self.cmake_settings.minimum_required
        max_pol = self.cmake_settings.maximum_policy
        if max_pol:
            version += "..." + max_pol
        return version

    def write_toolchain(self) -> Path | None:
        opts = self.get_configure_options_python(native=None)
        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        toolchain_file = of / "py-build-cmake-toolchain.cmake"
        user_toolchain_file = self.conf_settings.toolchain_file
        if not self.runner.dry:
            of.mkdir(parents=True, exist_ok=True)
        with VerboseFile(
            self.runner, toolchain_file, "CMake toolchain file (host context)"
        ) as f:
            f.write(f"cmake_minimum_required(VERSION {_CMAKE_TOOLCHAIN_POLICY})\n")
            for o in opts:
                f.write(o.to_preload_set(force=False))
            # https://github.com/pyodide/pyodide-build/issues/104
            pyodide104 = "pyodide_build/tools/cmake/Modules/Platform/Emscripten.cmake"
            if (
                self.conf_settings.os == "pyodide"
                and user_toolchain_file is not None
                and user_toolchain_file.as_posix().endswith(pyodide104)
            ):
                user_toolchain_file = self._wrap_pyodide_toolchain(user_toolchain_file)
            if user_toolchain_file is not None:
                content = f"""\
                set(PBC_USER_TOOLCHAIN_FILE "{user_toolchain_file.as_posix()}")
                message(STATUS "Including user toolchain: ${{PBC_USER_TOOLCHAIN_FILE}}")
                include(${{PBC_USER_TOOLCHAIN_FILE}})
                """
                f.write(textwrap.dedent(content))
        return toolchain_file

    def write_toolchain_build(self) -> Path | None:
        opts = self.get_configure_options_python(native=True)
        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        toolchain_file = of / "py-build-cmake-toolchain-build.cmake"
        if not self.runner.dry:
            of.mkdir(parents=True, exist_ok=True)
        with VerboseFile(
            self.runner, toolchain_file, "CMake toolchain file (build context)"
        ) as f:
            f.write(f"cmake_minimum_required(VERSION {_CMAKE_TOOLCHAIN_POLICY})\n")
            for o in opts:
                f.write(o.to_preload_set(force=False))
        return toolchain_file

    def write_profile(self) -> Path:
        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        profile_file = of / "py-build-cmake-profile"
        profile = deepcopy(self.conan_settings.extra_host_profile_data)
        profile.setdefault("settings", [])
        profile.setdefault("conf", [])
        profile.setdefault("tool_requires", [])

        # Operating system
        if all(not ln.startswith("os=") for ln in profile["settings"]):
            profile["settings"] += [
                f"os={os_to_conan_os(self.conf_settings.os)}",
            ]
        # macOS version
        if not self.cross_compiling() and self.plat.os_name == "mac":
            profile["settings"] += [
                f"os.version={self.plat.macos_version_str}",
            ]
        # Architecture
        if not self.cross_compiling():
            profile["settings"] += [f"arch={self._get_arch()}"]
        # Build type
        if self.conf_settings.build_type is not None:
            profile["settings"] += [
                f"build_type={self.conf_settings.build_type}",
            ]
        # Correct linker flags for CMake MODULE libraries (https://github.com/conan-io/conan/issues/17539)
        profile["conf"] += [
            f"&:tools.cmake.cmaketoolchain:extra_variables*={_MODULE_LINK_FLAGS!r}"
        ]
        # CMake toolchain file with Python hints etc.
        toolchain_file = self.write_toolchain()
        if toolchain_file is not None:
            profile["conf"] += [
                f"tools.cmake.cmaketoolchain:user_toolchain+={toolchain_file.as_posix()}"
            ]
        # Ninja build tool
        generator = self.conf_settings.generator
        if generator is not None:
            if "Ninja" in generator:
                profile["tool_requires"] += ["&:ninja/[*]"]
            profile["conf"] += [f"&:tools.cmake.cmaketoolchain:generator={generator}"]
        # CMake build tool
        profile["tool_requires"] += [
            f"&:cmake/[>={self.cmake_settings.minimum_required}]",
        ]
        # Build folder name
        if self.conan_settings.build_config_name is not None:
            build_vars = [f"const.{self.conan_settings.build_config_name}"]
            profile["conf"] += [
                f"tools.cmake.cmake_layout:build_folder_vars={build_vars!r}"
            ]
        with VerboseFile(
            self.runner, profile_file, "Conan profile (host context)"
        ) as f:
            for k, v in profile.items():
                f.write(f"[{k}]\n")
                for line in v:
                    f.write(line + "\n")
        return profile_file

    def _get_arch(self):
        arch = sysconfig_platform_to_conan_arch(self.plat.sysconfig_platform)
        if self.plat.os_name == "mac" and self.plat.archs:
            arch = archs_to_conan_arch(self.plat.archs)  # TODO: move to quirks
        return arch

    def write_profile_build(self) -> Path:
        toolchain_file = self.write_toolchain_build()
        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        profile_file = of / "py-build-cmake-profile-build"
        conf = "[conf]\n"
        if toolchain_file is not None:
            conf += f"tools.cmake.cmaketoolchain:user_toolchain+={toolchain_file.as_posix()}"
        with VerboseFile(
            self.runner, profile_file, "Conan profile (build context)"
        ) as f:
            f.write(conf)
        return profile_file

    def write_preload_options(self) -> Path | None:
        """Write the options into the CMake pre-load script and return its path."""
        opts = [
            *self.get_configure_options_package(),
            *self.get_configure_options_python(native=None),
        ]
        if not opts:
            return None

        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        preload_file = of / "py-build-cmake-preload.cmake"
        if not self.runner.dry:
            of.mkdir(parents=True, exist_ok=True)
        with VerboseFile(self.runner, preload_file, "CMake pre-load file") as f:
            f.write(f"cmake_minimum_required(VERSION {self.cmake_version_policy})\n")
            for o in opts:
                f.write(o.to_preload_set())
        return preload_file

    def _configure_environment(self, env: conan.tools.env.Environment):
        for k, v in self.get_env_vars_package().items():
            env.define(k, v)
        pbc = "PY_BUILD_CMAKE"
        if self.conanfile:
            build_folder = self.conanfile.build_folder
            if build_folder:
                env.define(f"{pbc}_BINARY_DIR", Path(build_folder).as_posix())
        install_prefix = self.install_settings.prefix
        if install_prefix is not None:
            env.define(f"{pbc}_INSTALL_PREFIX", install_prefix.as_posix())
        self._substitute_environment_options(env, self.conf_settings.environment)
        return env

    def _substitute_environment_options(  # noqa: PLR0912
        self,
        env: conan.tools.env.Environment,
        config_env: Mapping[str, StringOption | None],
    ):
        """Given the environment-like options in config_env, update the environment
        in env. Supports simple template expansion using ${VAR}."""

        def _template_expand(k, a, vars):
            try:
                try:
                    return Template(a).substitute(vars)
                except KeyError:
                    return Template(a).substitute(os.environ)
            except KeyError as e:
                msg = f"Invalid substitution in environment variable '{k}': {e.args[0]}"
                raise ConfigError(msg) from e

        for k, v in config_env.items():
            if v is None:
                continue
            assert isinstance(v, StringOption)
            # Perform template substitution on the different components
            vars = env.vars(self.conanfile)  # TODO: could be slow?
            for attr in "value", "append", "append_path", "prepend", "prepend_path":
                a = getattr(v, attr)
                if a is not None:
                    setattr(v, attr, _template_expand(k, a, vars))
            # Simple case: if we have a value, simply define the variable
            if v.value is not None:
                str_v = v.finalize()
                if str_v is not None:
                    env.define(k, str_v)
            # TODO: A bit late, but better than nothing
            elif v.remove:
                msg = "Remove operation is not supported for Conan "
                msg += "environment variables."
                raise ConfigError(msg)
            # If we're appending or prepending to the original value, translate
            # to Conan equivalents
            elif v.append or v.prepend:
                assert not v.append_path
                assert not v.prepend_path
                if v.prepend:
                    env.prepend(k, v.prepend)
                if v.append:
                    env.append(k, v.append)
            # If we're appending or prepending to the original path, translate
            # to Conan equivalents
            elif v.append_path or v.prepend_path:
                if v.prepend_path:
                    env.prepend_path(k, v.prepend_path)
                if v.append_path:
                    env.append_path(k, v.append_path)
            elif v.clear:
                env.unset(k)
            # TODO: ensure all cases are handled, add more thorough testing

    def configure(self):
        conan_project_dir = self.conf_settings.source_path
        with chdir(self.conf_settings.working_dir):
            # 0. Write config files and pre-load files
            # ---
            build_profile = self.write_profile_build()
            host_profile = self.write_profile()
            pre_load = self.write_preload_options()

            # 1. Install dependencies
            # ---
            cmd = ["install", conan_project_dir.as_posix()]
            for pr in self.conan_settings.build_profiles:
                cmd += ["-pr:b", pr]
            for pr in self.conan_settings.host_profiles:
                cmd += ["-pr:h", pr]
            cmd += ["-pr:b", build_profile.as_posix()]
            cmd += ["-pr:h", host_profile.as_posix()]
            cmd += ["-of", self.conan_settings.output_folder.as_posix()]
            cmd += self.conan_settings.args
            if self.runner.verbose:
                print(["conan", *cmd])  # noqa: T201
            api = conan.api.conan_api.ConanAPI()
            # TODO: Why is this necessary? Where is this documented?
            conan.cli.cli.Cli(api).add_commands()
            install = api.command.run(shlex.join(cmd))
            dep_graph = install["graph"]
            self.conanfile = cast(conan.ConanFile, dep_graph.root.conanfile)

            # 2. Set directories
            # ---
            prefix = self.install_settings.prefix
            if prefix is not None:
                # TODO: Is there an officially supported way to set the install prefix?
                self.conanfile.folders.set_base_package(prefix.as_posix())
            self.conanfile.folders.source = self.conf_settings.source_path.as_posix()

            # 3. Set environment variables
            # ---
            self.buildenv = conan.tools.env.VirtualBuildEnv(self.conanfile)
            self._configure_environment(self.buildenv.environment())
            self.buildenv.generate()

            # 4. Re-generate CMake toolchain (to include environment variables)
            # ---
            with contextlib.suppress(ValueError):
                self.conanfile.generators.remove("CMakeToolchain")
            tc = conan.tools.cmake.CMakeToolchain(self.conanfile)
            tc.presets_build_environment = self.buildenv.environment()
            tc.generate()

            # 5. Configure CMake
            # ---
            args = self.conf_settings.args
            if pre_load is not None:
                args = ["-C", pre_load.as_posix(), *args]
            cmake = conan.tools.cmake.CMake(self.conanfile)
            cmake.configure(variables=self.conf_settings.options, cli_args=args)

    def build(self):
        assert self.conanfile is not None
        cmake = conan.tools.cmake.CMake(self.conanfile)
        configs = self.build_settings.configs or [None]
        for config in configs:
            cmake.build(
                build_type=config,
                cli_args=self.build_settings.args,
                build_tool_args=self.build_settings.tool_args,
            )

    def install(self):
        assert self.conanfile is not None
        cmake = conan.tools.cmake.CMake(self.conanfile)
        configs = self.build_settings.configs or [None]
        for config in configs:
            for component in self.install_settings.components:
                cmake.install(
                    build_type=config,
                    component=component,
                    cli_args=self.install_settings.args,
                )

    def get_build_environment(self):
        assert self.buildenv is not None
        return dict(self.buildenv.vars().items())

    def _get_commands(self, func):
        cmd = []

        def wrap_run(self, command, *args, **kwargs):
            cmd.append(command)

        assert self.conanfile is not None
        old_run = self.conanfile.run
        self.conanfile.run = types.MethodType(wrap_run, self.conanfile)
        try:
            func()
        finally:
            self.conanfile.run = old_run
        return cmd

    def get_build_commands(self):
        return self._get_commands(self.build)

    def get_install_commands(self):
        return self._get_commands(self.install)

    def get_working_dir(self):
        assert self.conanfile
        assert isinstance(self.conanfile.build_folder, str)
        return Path(self.conanfile.build_folder)

    def _wrap_pyodide_toolchain(self, toolchain_file: Path) -> Path:
        """Workaround for https://github.com/pyodide/pyodide-build/issues/104."""
        of = self.conan_settings.output_folder / self.conan_settings.build_config_name
        wrapper = of / "pyodide-build-toolchain.cmake"
        content = f"""\
        cmake_minimum_required(VERSION {_CMAKE_TOOLCHAIN_POLICY})
        set(PYODIDE_TOOLCHAIN_FILE "{toolchain_file.as_posix()}")
        if (DEFINED CMAKE_C_FLAGS)
            set(PBC_CMAKE_C_FLAGS_SET On)
        endif()
        if (DEFINED CMAKE_CXX_FLAGS)
            set(PBC_CMAKE_CXX_FLAGS_SET On)
        endif()
        if (DEFINED CMAKE_SHARED_LINKER_FLAGS)
            set(PBC_CMAKE_SHARED_LINKER_FLAGS_SET On)
        endif()
        message(STATUS "Including Pyodide toolchain: ${{PYODIDE_TOOLCHAIN_FILE}}")
        include(${{PYODIDE_TOOLCHAIN_FILE}})
        message(STATUS "Adding side module flags to CMAKE_C_FLAGS_INIT, CMAKE_CXX_FLAGS_INIT, CMAKE_SHARED_LINKER_FLAGS_INIT")
        set(CMAKE_C_FLAGS_INIT "${{CMAKE_C_FLAGS_INIT}} $ENV{{SIDE_MODULE_CFLAGS}}")
        set(CMAKE_CXX_FLAGS_INIT "${{CMAKE_CXX_FLAGS_INIT}} $ENV{{SIDE_MODULE_CXXFLAGS}}")
        set(CMAKE_SHARED_LINKER_FLAGS_INIT "${{CMAKE_SHARED_LINKER_FLAGS_INIT}} $ENV{{SIDE_MODULE_LDFLAGS}}")
        if (NOT PBC_CMAKE_C_FLAGS_SET)
            message(STATUS "unset(CMAKE_C_FLAGS)")
            unset(CMAKE_C_FLAGS)
        endif()
        if (NOT PBC_CMAKE_CXX_FLAGS_SET)
            message(STATUS "unset(CMAKE_CXX_FLAGS)")
            unset(CMAKE_CXX_FLAGS)
        endif()
        if (NOT PBC_CMAKE_SHARED_LINKER_FLAGS_SET)
            message(STATUS "unset(CMAKE_SHARED_LINKER_FLAGS)")
            unset(CMAKE_SHARED_LINKER_FLAGS)
        endif()
        """
        if not self.runner.dry:
            of.mkdir(parents=True, exist_ok=True)
        with VerboseFile(self.runner, wrapper, "pyodide-build toolchain wrapper") as f:
            f.write(textwrap.dedent(content))

        return wrapper
