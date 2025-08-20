import contextlib
from pathlib import Path
import shlex
import types
import typing

import conan
import conan.api.conan_api
import conan.cli.cli
import conan.tools.cmake
import conan.tools.env

from .cmake import CMaker, VerboseFile


class ConanCMaker(CMaker):
    _SPECIAL_CMAKE_OPTIONS = {
        "system_name",
        "system_processor",
        "system_version",
        "toolset_arch",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conanfile: conan.ConanFile | None = None
        self.conan_config = {}
        for o in self._SPECIAL_CMAKE_OPTIONS:
            v = self.conf_settings.options.pop("CMAKE_" + o.upper(), None)
            if v is not None:
                self.conan_config[o] = v

    def write_toolchain(self) -> Path | None:
        opts = self.get_configure_options_python(native=None)
        toolchain_file = (
            self.cmake_settings.build_path / "py-build-cmake-toolchain.cmake"
        )
        if not self.runner.dry:
            self.cmake_settings.build_path.mkdir(parents=True, exist_ok=True)
        with VerboseFile(
            self.runner, toolchain_file, "CMake toolchain file (host context)"
        ) as f:
            f.write(f"cmake_minimum_required(VERSION {self.cmake_version_policy})\n")
            for o in opts:
                f.write(o.to_preload_set())
            if self.conf_settings.toolchain_file:
                toolchain = str(self.conf_settings.toolchain_file)
                f.write(f'include("{toolchain}")\n')
        return toolchain_file

    def write_toolchain_build(self) -> Path | None:
        opts = self.get_configure_options_python(native=True)
        toolchain_file = (
            self.cmake_settings.build_path / "py-build-cmake-toolchain-build.cmake"
        )
        if not self.runner.dry:
            self.cmake_settings.build_path.mkdir(parents=True, exist_ok=True)
        with VerboseFile(
            self.runner, toolchain_file, "CMake toolchain file (build context)"
        ) as f:
            f.write(f"cmake_minimum_required(VERSION {self.cmake_version_policy})\n")
            for o in opts:
                f.write(o.to_preload_set())
        return toolchain_file

    def write_profile(self) -> Path:
        toolchain_file = self.write_toolchain()

        profile_file = self.cmake_settings.build_path / "py-build-cmake-profile-build"
        conf = "[conf]\n"
        if toolchain_file is not None:
            conf += f"tools.cmake.cmaketoolchain:user_toolchain+={toolchain_file!s}\n"
        for k, v in self.conan_config.items():
            conf += f"tools.cmake.cmaketoolchain:{k}={v}\n"
        with VerboseFile(
            self.runner, profile_file, "Conan profile (host context)"
        ) as f:
            f.write(conf)
        return profile_file

    def write_profile_build(self) -> Path:
        toolchain_file = self.write_toolchain_build()

        profile_file = self.cmake_settings.build_path / "py-build-cmake-profile-build"
        conf = "[conf]\n"
        if toolchain_file is not None:
            conf += f"tools.cmake.cmaketoolchain:user_toolchain+={toolchain_file!s}\n"
        with VerboseFile(
            self.runner, profile_file, "Conan profile (build context)"
        ) as f:
            f.write(conf)
        return profile_file

    def write_preload_options(self) -> Path | None:
        """Write the options into the CMake pre-load script and return its path."""
        opts = self.get_configure_options_package()
        if not opts:
            return None

        preload_file = self.cmake_settings.build_path / "py-build-cmake-preload.cmake"
        if not self.runner.dry:
            self.cmake_settings.build_path.mkdir(parents=True, exist_ok=True)
        with VerboseFile(self.runner, preload_file, "CMake pre-load file") as f:
            f.write(f"cmake_minimum_required(VERSION {self.cmake_version_policy})\n")
            for o in opts:
                f.write(o.to_preload_set() + "\n")
        return preload_file

    def configure(self):
        default_build_profile = "default"
        default_host_profile = "default"
        conan_project_dir = self.cmake_settings.source_path
        conan_args = ["--build=missing"]
        cwd = "."  # TODO
        with contextlib.chdir(cwd):
            # 0. Write config files and pre-load files
            # ---
            build_profile = self.write_profile_build()
            host_profile = self.write_profile()
            pre_load = self.write_preload_options()
            # 1. Install dependencies
            # ---
            api = conan.api.conan_api.ConanAPI()
            # TODO: Why is this necessary? Where is this documented?
            conan.cli.cli.Cli(api).add_commands()
            cmd = [
                "install",
                conan_project_dir.as_posix(),
                "-pr:b",
                default_build_profile,
                "-pr:h",
                default_host_profile,
                "-pr:b",
                build_profile.as_posix(),
                "-pr:h",
                host_profile.as_posix(),
                "-of",
                self.cmake_settings.build_path.as_posix(),
            ] + conan_args
            install = api.command.run(shlex.join(cmd))
            dep_graph = install["graph"]
            self.conanfile = typing.cast(conan.ConanFile, dep_graph.root.conanfile)

            # 2. Set directories
            # ---
            # TODO: Is there an officially supported way to set the install prefix?
            prefix = self.install_settings.prefix
            if prefix is not None:
                self.conanfile.folders.set_base_package(prefix.as_posix())
            self.conanfile.folders.source = self.cmake_settings.source_path.as_posix()
            # 3. Configure CMake
            # ---
            args = self.conf_settings.args
            if pre_load is not None:
                args = ["-C", pre_load.as_posix()] + args
            cmake = conan.tools.cmake.CMake(self.conanfile)
            cmake.configure(variables=self.conf_settings.options, cli_args=args)

    def build(self):
        assert self.conanfile is not None
        cmake = conan.tools.cmake.CMake(self.conanfile)
        configs = self.build_settings.configs or [None]
        for config in configs:
            kwargs = dict(
                build_type=config,
                cli_args=self.build_settings.args,
                build_tool_args=self.build_settings.tool_args,
            )
            cmake.build(**kwargs)

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
        build_env = conan.tools.env.VirtualBuildEnv(self.conanfile)
        return {k: v for k, v in build_env.vars().items()}

    def _get_commands(self, func):
        cmd = []

        def wrap_run(self, command, **kwargs):
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
