from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageInfo:
    version: str
    package_name: str
    module_name: str


@dataclass
class BuildPaths:
    source_dir: Path
    wheel_dir: Path
    temp_dir: Path
    staging_dir: Path
    pkg_staging_dir: Path