from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from ..common import PackageInfo
from ..common.platform import BuildPlatformInfo, OSIdentifier
from ..config.environment import substitute_environment_options
from .builder import Builder, Option, PackageTags, PythonSettings
from .cmd_runner import CommandRunner
from .file import VerboseFile

logger = logging.getLogger(__name__)


@dataclass
class CMakeSettings:
    minimum_required: str
    maximum_policy: str | None
    command: Path = Path("cmake")
    make_program: Path | None = None


@dataclass
class CMakeConfigureSettings:
    working_dir: Path
    source_path: Path
    build_path: Path
    os: OSIdentifier
    generator_platform: str | None
    cross_compiling: bool
    toolchain_file: Path | None
    environment: dict
    build_type: str | None
    options: dict[str, str]
    args: list[str]
    preset: str | None
    generator: str | None


@dataclass
class CMakeBuildSettings:
    args: list[str]
    tool_args: list[str]
    presets: list[str]
    configs: list[str]


@dataclass
class CMakeInstallSettings:
    args: list[str]
    configs: list[str]
    components: list[str]
    prefix: Path | None


class CMaker(Builder):
    def __init__(
        self,
        plat: BuildPlatformInfo,
        package_info: PackageInfo,
        package_tags: PackageTags,
        python_settings: PythonSettings,
        cmake_settings: CMakeSettings,
        conf_settings: CMakeConfigureSettings,
        build_settings: CMakeBuildSettings,
        install_settings: CMakeInstallSettings,
        runner: CommandRunner,
    ):
        super().__init__(plat, package_info, package_tags, python_settings, runner)
        self.cmake_settings = cmake_settings
        self.conf_settings = conf_settings
        self.build_settings = build_settings
        self.install_settings = install_settings
        self.environment: dict[str, str] | None = None

        self.check_environment(self.conf_settings.environment)
        self.check_cmake_options(self.conf_settings.options)

    @property
    def cmake_version_policy(self):
        """Determine argument for cmake_minimum_required(VERSION X)."""
        version = self.cmake_settings.minimum_required
        max_pol = self.cmake_settings.maximum_policy
        if max_pol:
            version += "..." + max_pol
        return version

    def run(self, *args, **kwargs):
        return self.runner.run(*args, **kwargs)

    def prepare_environment(self):
        """Copy of the current environment with the variables defined in the
        user's configuration settings."""
        if self.environment is None:
            self.environment = os.environ.copy()
            self.environment.update(self.get_env_vars_package())
            pbc = "PY_BUILD_CMAKE"
            self.environment[f"{pbc}_BINARY_DIR"] = str(self.conf_settings.build_path)
            if self.install_settings.prefix is not None:
                install_prefix = str(self.install_settings.prefix)
                self.environment[f"{pbc}_INSTALL_PREFIX"] = install_prefix
            if not self.cross_compiling() and self.plat.os_name == "mac":
                version = self.plat.macos_version_str
                self.environment["MACOSX_DEPLOYMENT_TARGET"] = version
            if self.conf_settings.environment:
                substitute_environment_options(
                    self.environment, self.conf_settings.environment
                )
        return self.environment

    def cross_compiling(self) -> bool:
        return self.conf_settings.cross_compiling

    def get_native_python_abi_tuple(self):
        cmake_version = self.cmake_settings.minimum_required
        return super()._get_native_python_abi_tuple(cmake_version)

    def get_configure_options_install(self) -> list[Option]:
        prefix = self.install_settings.prefix
        if prefix:
            return [
                Option("CMAKE_INSTALL_PREFIX", prefix.as_posix(), "PATH"),
                Option("CMAKE_FIND_NO_INSTALL_PREFIX", "On", "BOOL"),
            ]
        return []

    def get_configure_options_make(self) -> list[Option]:
        """Sets CMAKE_MAKE_PROGRAM."""
        if self.cmake_settings.make_program:
            opt = Option(
                "CMAKE_MAKE_PROGRAM",
                self.cmake_settings.make_program.as_posix(),
                "FILEPATH",
            )
            return [opt]
        return []

    def get_configure_options_target(self) -> list[Option]:
        """Sets CMake variables for the target."""
        opts = []
        if not self.cross_compiling() and self.plat.os_name == "mac":
            version = self.plat.macos_version_str
            opts += [Option("CMAKE_OSX_DEPLOYMENT_TARGET", version, "STRING")]
        return opts

    def get_configure_options_toolchain(self) -> list[Option]:
        """Sets CMAKE_TOOLCHAIN_FILE."""
        opts = []
        if self.conf_settings.toolchain_file:
            toolchain = str(self.conf_settings.toolchain_file)
            opts += [Option("CMAKE_TOOLCHAIN_FILE", toolchain, "FILEPATH")]
        return opts

    def get_configure_options_settings(self) -> list[Option]:
        def _cvt_opt(k: str, v: str):
            kt = k.rsplit(":", 1)
            return Option(kt[0], v, "") if len(kt) == 1 else Option(kt[0], v, kt[1])

        return [_cvt_opt(k, v) for k, v in self.conf_settings.options.items()]

    def get_configure_options(self) -> list[Option]:
        """Get the list of options (-D) passed to the CMake configure step
        through the command line."""
        return (
            self.get_configure_options_target()
            + self.get_configure_options_toolchain()
            + self.get_configure_options_settings()
        )

    def get_preload_options(self) -> list[Option]:
        """Get the list of options set in the CMake pre-load script (-C)."""
        return (
            self.get_configure_options_package()
            + self.get_configure_options_make()
            + self.get_configure_options_python()
            + self.get_configure_options_install()
        )

    def write_preload_options(self) -> Path | None:
        """Write the options into the CMake pre-load script and return its
        path."""
        opts = self.get_preload_options()
        if not opts:
            return None

        preload_file = self.conf_settings.build_path / "py-build-cmake-preload.cmake"
        if not self.runner.dry:
            self.conf_settings.build_path.mkdir(parents=True, exist_ok=True)
        with VerboseFile(self.runner, preload_file, "CMake pre-load file") as f:
            f.write(f"cmake_minimum_required(VERSION {self.cmake_version_policy})\n")
            for o in opts:
                f.write(o.to_preload_set())
        return preload_file

    def get_cmake_generator_platform(self) -> list[str]:
        """Returns -A <platform> for the Visual Studio generator on Windows."""
        win = self.conf_settings.os == "windows"
        gen = self.conf_settings.generator
        vs_gen = win and (not gen or gen.lower().startswith("visual studio"))
        cmake_plat = self.conf_settings.generator_platform
        if vs_gen and cmake_plat:
            return ["-A", cmake_plat]
        return []

    def get_configure_command(self):
        options = self.get_configure_options()
        cmd = [str(self.cmake_settings.command)]
        cmd += ["-S", str(self.conf_settings.source_path)]
        if self.conf_settings.preset:
            cmd += ["--preset", self.conf_settings.preset]
        if not self.conf_settings.preset or not self.build_settings.presets:
            cmd += ["-B", str(self.conf_settings.build_path)]
        if self.conf_settings.generator:
            cmd += ["-G", self.conf_settings.generator]
        cmd += self.get_cmake_generator_platform()
        preload_file = self.write_preload_options()
        if preload_file is not None:
            cmd += ["-C", str(preload_file)]
        cmd += [f for opt in options for f in ("-D", opt.to_cli_string())]
        cmd += self.conf_settings.args
        return cmd

    def get_working_dir(self) -> Path:
        return self.conf_settings.working_dir

    def configure(self):
        env = self.prepare_environment()
        cmd = self.get_configure_command()
        cwd = self.get_working_dir()
        self.run(cmd, cwd=cwd, check=True, env=env)

    def get_build_command(self, config, preset):
        cmd = [str(self.cmake_settings.command), "--build"]
        if preset is not None:
            cmd += ["--preset", preset]
        else:
            cmd += [str(self.conf_settings.build_path)]
        if config is not None:
            cmd += ["--config", config]
        if self.build_settings.args:
            cmd += self.build_settings.args
        if self.build_settings.tool_args:
            cmd += ["--", *self.build_settings.tool_args]
        return cmd

    def get_build_commands(self):
        presets = self.build_settings.presets or [None]
        configs = self.build_settings.configs or [None]
        for preset, config in product(presets, configs):
            yield self.get_build_command(config, preset)

    def build(self):
        env = self.prepare_environment()
        cwd = self.get_working_dir()
        for cmd in self.get_build_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)

    def get_install_command(self, config):
        for component in self.install_settings.components:
            cmd = [str(self.cmake_settings.command), "--install"]
            cmd += [str(self.conf_settings.build_path)]
            if self.install_settings.prefix:
                cmd += ["--prefix", str(self.install_settings.prefix)]
            if config is not None:
                cmd += ["--config", config]
            if component:
                cmd += ["--component", component]
            if self.install_settings.args:
                cmd += self.install_settings.args
            yield cmd

    def get_install_commands(self):
        for config in self.install_settings.configs or [None]:
            yield from self.get_install_command(config)

    def install(self):
        env = self.prepare_environment()
        cwd = self.get_working_dir()
        for cmd in self.get_install_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)

    def get_build_environment(self):
        """Get the environment variables to add to the build hook files."""
        env = self.prepare_environment()
        return {k: v for k, v in env.items() if k in self.conf_settings.environment}
