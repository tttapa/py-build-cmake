from pathlib import Path
from dataclasses import dataclass
import os
from string import Template
import sys
import sysconfig
from typing import Dict, List, Optional
import re
import warnings

from .datastructures import PackageInfo
from .cmd_runner import CommandRunner
from .quirks.config import python_sysconfig_platform_to_cmake_platform_win

@dataclass
class CMakeSettings:
    working_dir: Path
    source_path: Path
    build_path: Path
    os: str
    find_python: bool
    find_python3: bool
    command: Path = Path("cmake")


@dataclass
class CMakeConfigureSettings:
    environment: dict
    build_type: Optional[str]
    options: Dict[str, str]
    args: List[str]
    preset: Optional[str]
    generator: Optional[str]
    cross_compiling: bool
    toolchain_file: Optional[Path]
    python_prefix: Optional[Path]
    python_library: Optional[Path]


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
                 runner: CommandRunner):
        self.cmake_settings = cmake_settings
        self.conf_settings = conf_settings
        self.build_settings = build_settings
        self.install_settings = install_settings
        self.package_info = package_info
        self.runner = runner
        self.environment: Optional[dict] = None

    def run(self, *args, **kwargs):
        return self.runner.run(*args, **kwargs)

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
        return self.conf_settings.cross_compiling

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
        def get_opts(prefix):
            yield prefix + '_EXECUTABLE:FILEPATH=' + sys.executable
            yield prefix + '_FIND_REGISTRY=NEVER'
            yield prefix + '_FIND_FRAMEWORK=NEVER'
            yield prefix + '_FIND_STRATEGY=LOCATION'
            if not self.cross_compiling():
                pfx = sys.prefix + ';' + sys.base_prefix
                yield prefix + '_ROOT_DIR=' + pfx
            else:
                if self.conf_settings.python_prefix:
                    pfx = str(self.conf_settings.python_prefix)
                    yield prefix + '_ROOT_DIR=' + pfx
                if self.conf_settings.python_library:
                    lib = str(self.conf_settings.python_library)
                    yield prefix + '_LIBRARY=' + lib
        opts = []
        if self.cmake_settings.find_python: opts += list(get_opts('Python'))
        if self.cmake_settings.find_python3: opts += list(get_opts('Python3'))
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
    
    def get_cmake_generator_platform(self) -> List[str]:
        if self.cmake_settings.os == "windows" and not self.cross_compiling():
            plat = sysconfig.get_platform()
            cmake_plat = python_sysconfig_platform_to_cmake_platform_win(plat)
            if cmake_plat:
                return ['-A', cmake_plat]
            else:
                warnings.warn("Unknown platform, CMake generator platform "
                              "option (-A) will not be set")
        return []

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
        cmd += self.get_cmake_generator_platform()
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