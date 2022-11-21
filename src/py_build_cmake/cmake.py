from pathlib import Path
from dataclasses import dataclass
import os
from string import Template
import sys
from typing import Dict, List, Optional
import re
from pprint import pprint
from subprocess import run as sp_run
from .datastructures import PackageInfo

@dataclass
class CMakeSettings:
    working_dir: Path
    source_path: Path
    build_path: Path
    os: str
    command: Path = Path("cmake")


@dataclass
class CMakeConfigureSettings:
    environment: dict
    toolchain_file: Optional[Path]
    build_type: Optional[str]
    options: Dict[str, str]
    args: List[str]
    preset: Optional[str]
    generator: Optional[str]


@dataclass
class CMakeBuildSettings:
    args: List[str]
    tool_args: List[str]
    presets: List[str]
    configs: List[str]


@dataclass
class CMakeInstallSettings:
    args: List[str]
    presets: List[str]
    configs: List[str]
    components: List[str]
    prefix: Optional[Path]


class CMaker:

    def __init__(self,
                 cmake_settings: CMakeSettings,
                 conf_settings: CMakeConfigureSettings,
                 build_settings: CMakeBuildSettings,
                 install_settings: CMakeInstallSettings,
                 package_info: PackageInfo,
                 verbose: bool = False,
                 dry: bool = False):
        self.cmake_settings = cmake_settings
        self.conf_settings = conf_settings
        self.build_settings = build_settings
        self.install_settings = install_settings
        self.package_info = package_info
        self.verbose = verbose
        self.dry = dry
        self.environment: Optional[dict] = None

    def run(self, *args, **kwargs):
        """Wrapper around subprocess.run that optionally prints the command."""
        if self.verbose:
            pprint([*args])
            pprint(kwargs)
        elif self.dry:
            from shlex import join
            print(join(args[0]))
        if not self.dry:
            return sp_run(*args, **kwargs)

    def prepare_environment(self):
        """Copy of the current environment with the variables defined in the
        user's configuration settings."""
        if self.environment is None:
            self.environment = os.environ.copy()
            if self.conf_settings.environment:
                for k, v in self.conf_settings.environment.items():
                    templ = Template(v)
                    self.environment[k] = templ.substitute(self.environment)
        return self.environment

    def cross_compiling(self) -> bool:
        return self.conf_settings.toolchain_file is not None

    def get_configure_options_package(self) -> List[str]:
        """Flags specific to py-build-cmake, useful in the user's CMake scripts."""
        return [
            'PY_BUILD_CMAKE_PACKAGE_VERSION:STRING=' +
            self.package_info.version,
            'PY_BUILD_CMAKE_PACKAGE_NAME:STRING=' +
            self.package_info.package_name,
            'PY_BUILD_CMAKE_MODULE_NAME:STRING=' +
            self.package_info.module_name,
        ]

    def get_configure_options_python(self) -> List[str]:
        """Flags to help CMake find the right version of Python."""
        opts = ['Python3_EXECUTABLE:FILEPATH=' + sys.executable]
        if not self.cross_compiling():
            opts += [
                'Python3_ROOT_DIR:PATH=' + sys.prefix,
                'Python3_FIND_REGISTRY=NEVER',
                'Python3_FIND_STRATEGY=LOCATION',
            ]
        return opts

    def get_configure_options_env(self, env) -> List[str]:
        """Currently sets CMAKE_OSX_ARCHITECTURES if $ENV{ARCHFLAGS} is set
        on macOS. This ensures compatibility with cibuildwheel."""
        opts = []
        if self.cmake_settings.os == "mac" and "ARCHFLAGS" in env:
            archs = re.findall(r"-arch (\S+)", env["ARCHFLAGS"])
            if archs:
                opts += ['CMAKE_OSX_ARCHITECTURES={}'.format(";".join(archs))]
        return opts

    def get_configure_options_toolchain(self) -> List[str]:
        """Sets CMAKE_TOOLCHAIN_FILE."""
        return [
            'CMAKE_TOOLCHAIN_FILE:FILEPATH=' +
            str(self.conf_settings.toolchain_file)
        ] if self.conf_settings.toolchain_file else []

    def get_configure_options_settings(self) -> List[str]:
        return [k + '=' + v for k, v in self.conf_settings.options.items()]

    def get_configure_options(self, env) -> List[str]:
        return (self.get_configure_options_package() +
                self.get_configure_options_python() +
                self.get_configure_options_env(env) +
                self.get_configure_options_toolchain() +
                self.get_configure_options_settings())

    def get_configure_command(self, env):
        options = self.get_configure_options(env)
        cmd = [str(self.cmake_settings.command)]
        cmd += ['-S', str(self.cmake_settings.source_path)]
        if self.conf_settings.preset:
            cmd += ['--preset', self.conf_settings.preset]
        else:
            cmd += ['-B', str(self.cmake_settings.build_path)]
        if self.conf_settings.generator:
            cmd += ['-G', self.conf_settings.generator]
        cmd += [f for opt in options for f in ('-D', opt)]
        cmd += self.conf_settings.args
        return cmd

    def configure(self):
        env = self.prepare_environment()
        cmd = self.get_configure_command(env)
        cwd = self.cmake_settings.working_dir
        cwd = str(cwd) if cwd is not None else None
        self.run(cmd, cwd=cwd, check=True, env=env)

    def iter_presets_configs(self, settings, func):
        done = False
        for preset in settings.presets:
            yield from func(None, preset)
            done = True
        for config in settings.configs:
            yield from func(config, None)
            done = True
        if not done:
            yield from func(None, None)

    def get_build_command(self, config, preset):
        cmd = [str(self.cmake_settings.command), '--build']
        if preset is not None:
            cmd += ['--preset', preset]
        else:
            cmd += [str(self.cmake_settings.build_path)]
        if config is not None:
            cmd += ['--config', config]
        if self.build_settings.args:
            cmd += self.build_settings.args
        if self.build_settings.tool_args:
            cmd += ['--'] + self.build_settings.tool_args
        yield cmd

    def get_build_commands(self):
        yield from self.iter_presets_configs(self.build_settings,
                                             self.get_build_command)

    def build(self):
        env = self.prepare_environment()
        cwd = self.cmake_settings.working_dir
        cwd = str(cwd) if cwd is not None else None
        for cmd in self.get_build_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)

    def get_install_command(self, config, preset):
        for component in self.install_settings.components:
            cmd = [str(self.cmake_settings.command), '--install']
            if preset is not None:
                cmd += ['--preset', preset]
            else:
                cmd += [str(self.cmake_settings.build_path)]
            if config is not None:
                cmd += ['--config', config]
            if component:
                cmd += ['--component', component]
            if self.install_settings.prefix:
                cmd += ['--prefix', str(self.install_settings.prefix)]
            if self.install_settings.args:
                cmd += self.install_settings.args
            yield cmd

    def get_install_commands(self):
        yield from self.iter_presets_configs(self.install_settings,
                                             self.get_install_command)
    def install(self):
        env = self.prepare_environment()
        cwd = self.cmake_settings.working_dir
        cwd = str(cwd) if cwd is not None else None
        for cmd in self.get_install_commands():
            self.run(cmd, cwd=cwd, check=True, env=env)