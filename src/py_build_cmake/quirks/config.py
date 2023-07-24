import configparser
import os
import platform
import sys
import sysconfig
import warnings
from typing import Optional, Union, List
from ..config_options import ConfigNode, pth


def python_sysconfig_platform_to_cmake_platform_win(
        plat_name: Optional[str]) -> Optional[str]:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_GENERATOR_PLATFORM.html"""
    cmake_platform = {
        None: None,
        'win32': 'Win32',
        'win-amd64': 'x64',
        'win-arm32': 'ARM',
        'win-arm64': 'ARM64',
    }.get(plat_name)
    return cmake_platform


def python_sysconfig_platform_to_cmake_processor_win(
        plat_name: Optional[str]) -> Optional[str]:
    """Convert a sysconfig platform string to the corresponding value of
    https://cmake.org/cmake/help/latest/variable/CMAKE_HOST_SYSTEM_PROCESSOR.html"""
    # The value of %PROCESSOR_ARCHITECTURE% on Windows
    cmake_proc = {
        None: None,
        'win32': 'x86',
        'win-amd64': 'AMD64',
        'win-arm32': 'ARM',
        'win-arm64': 'ARM64',
    }.get(plat_name)
    return cmake_proc


def platform_to_platform_tag(plat: str) -> str:
    """https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#platform-tag"""
    return plat.replace('.', '_').replace('-', '_')


def get_python_lib_impl(libdir: str):
    """Return the path to python<major><minor>.lib or
    python<major>.lib if it exists in libdir. None otherwise."""
    v = sys.version_info
    python3xlib = os.path.join(libdir, f'python{v.major}{v.minor}.lib')
    if os.path.exists(python3xlib):
        return python3xlib
    python3lib = os.path.join(libdir, f'python{v.major}.lib')
    if os.path.exists(python3lib):
        return python3lib
    return None


def get_python_lib(
        library_dirs: Optional[Union[str, List[str]]]) -> Optional[str]:
    """Return the path the the first python<major><minor>.lib or
    python<major>.lib file in any of the library_dirs.
    Returns None if no such file exists."""
    if library_dirs is None:
        return None
    if isinstance(library_dirs, str):
        library_dirs = [library_dirs]
    not_none = lambda x: x is not None
    try:
        return next(filter(not_none, map(get_python_lib_impl, library_dirs)))
    except StopIteration:
        return None


def cross_compile_win(config: ConfigNode, plat_name, library_dirs,
                      cmake_platform, cmake_proc):
    """Update the configuration to include a cross-compilation configuration
    that builds for the given platform and processor. If library_dirs contains
    a compatible Python library, it is also included in the configuration, as
    well as the path to the Python installation's root directory, so CMake is
    able to locate Python correctly."""
    warnings.warn(
        f"DIST_EXTRA_CONFIG.build_ext specified plat_name that is different from the current platform. Automatically enabling cross-compilation for {cmake_platform}"
    )
    assert not config.contains('cross')
    cross_cfg = {
        'os': 'windows',
        'arch': platform_to_platform_tag(plat_name),
        'cmake': {
            'options': {
                'CMAKE_SYSTEM_NAME': 'Windows',
                'CMAKE_SYSTEM_PROCESSOR': cmake_proc,
                'CMAKE_GENERATOR_PLATFORM': cmake_platform,
            }
        },
    }
    python_lib = get_python_lib(library_dirs)
    if python_lib is not None:
        cross_cfg['library'] = python_lib
        python_root = os.path.dirname(os.path.dirname(python_lib))
        if os.path.exists(os.path.join(python_root, 'include')):
            cross_cfg['root'] = python_root
    else:
        warnings.warn(
            "Python library was not found in DIST_EXTRA_CONFIG.build_ext.library_dirs."
        )
    config.setdefault(pth('cross'), ConfigNode.from_dict(cross_cfg))


def handle_cross_win(config: ConfigNode, plat_name: str,
                     library_dirs: Optional[Union[str, List[str]]]):
    """Try to configure cross-compilation for the given Windows platform.
    library_dirs should contain the directory with the Python library."""
    plat_proc = (python_sysconfig_platform_to_cmake_platform_win(plat_name),
                 python_sysconfig_platform_to_cmake_processor_win(plat_name))
    if all(plat_proc):
        cross_compile_win(config, plat_name, library_dirs, *plat_proc)
    else:
        warnings.warn(
            f"Cross-compilation setup skipped because the platform {plat_name} is unknown"
        )


def handle_dist_extra_config_win(config: ConfigNode, dist_extra_conf: str):
    """Read the given distutils configuration file and use it to configure
    cross-compilation if appropriate."""
    distcfg = configparser.ConfigParser()
    distcfg.read(dist_extra_conf)

    library_dirs = distcfg.get('build_ext', 'library_dirs', fallback='')
    plat_name = distcfg.get('build_ext', 'plat_name', fallback='')

    if plat_name and plat_name != sysconfig.get_platform():
        handle_cross_win(config, plat_name, library_dirs)


def config_quirks_win(config: ConfigNode):
    """
    Explanation:
    The cibuildwheel tool sets the DIST_EXTRA_CONFIG environment variable when
    cross-compiling. It points to a configuration file that contains the path
    to the correct Python library (.lib), as well as the name of the platform
    to compile for.
    If the user did not specify a custom cross-compilation configuration,
    we will automatically add a minimal cross-compilation configuration that
    points CMake to the right Python library, and that selects the right
    CMake/Visual Studio platform.
    """
    dist_extra_conf = os.getenv('DIST_EXTRA_CONFIG')
    if dist_extra_conf is not None:
        if config.contains('cross'):
            warnings.warn(
                "Cross-compilation configuration was not empty, so I'm ignoring DIST_EXTRA_CONFIG"
            )
        elif not config.contains('cmake'):
            warnings.warn(
                "CMake configuration was empty, so I'm ignoring DIST_EXTRA_CONFIG"
            )
        else:
            handle_dist_extra_config_win(config, dist_extra_conf)


def config_quirks(config: ConfigNode):
    dispatch = {"Windows": config_quirks_win}.get(platform.system())
    if dispatch is not None:
        dispatch(config)
