#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Build ``dist/carboncreditbuy_qgis-<version>.zip`` for QGIS "Install from ZIP".

The archive has one top-level folder, ``carboncreditbuy_qgis/``, which is what QGIS expects.
It contains the plugin package plus the LICENSE and README of this directory. Bytecode caches
and editor files are left out. The archive is not meant to be committed (``dist/`` is ignored).

Usage::

    python scripts/package.py [--out DIR]

Set ``SOURCE_DATE_EPOCH`` to get byte-identical archives for the same sources.
"""

from __future__ import annotations

import argparse
import configparser
import os
import re
import sys
import time
import zipfile
from pathlib import Path

PACKAGE = "carboncreditbuy_qgis"
ROOT = Path(__file__).resolve().parent.parent
REQUIRED_METADATA = (
    "name",
    "qgisMinimumVersion",
    "description",
    "about",
    "version",
    "author",
    "email",
    "repository",
)
EXTRA_FILES = ("LICENSE", "README.md")
_SKIP_DIRS = {"__pycache__", ".git", ".ruff_cache", ".pytest_cache", ".mypy_cache"}
_SKIP_SUFFIXES = (".pyc", ".pyo", ".orig", ".rej", ".swp", "~")
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}


class PackagingError(Exception):
    """The plugin sources are not in a state that can be packaged."""


def read_metadata(package_dir: Path) -> dict[str, str]:
    """Read ``metadata.txt`` the way QGIS does and check the required keys."""
    parser = configparser.ConfigParser()
    metadata_file = package_dir / "metadata.txt"
    if not metadata_file.is_file():
        raise PackagingError(f"{metadata_file} is missing")
    with metadata_file.open(encoding="utf-8") as handle:
        parser.read_file(handle)
    if not parser.has_section("general"):
        raise PackagingError("metadata.txt has no [general] section")
    general = dict(parser["general"])
    missing = [key.lower() for key in REQUIRED_METADATA if not general.get(key.lower())]
    if missing:
        raise PackagingError("metadata.txt is missing: " + ", ".join(missing))
    return general


def read_code_version(package_dir: Path) -> str:
    """``__version__`` from ``version.py`` (parsed, not imported)."""
    text = (package_dir / "version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise PackagingError("version.py does not define __version__")
    return match.group(1)


def check_sources(package_dir: Path) -> str:
    """Validate the sources and return the plugin version."""
    metadata = read_metadata(package_dir)
    version = metadata["version"]
    code_version = read_code_version(package_dir)
    if version != code_version:
        raise PackagingError(
            f"metadata.txt says version {version} but version.py says {code_version}"
        )
    init_text = (package_dir / "__init__.py").read_text(encoding="utf-8")
    if "def classFactory" not in init_text:
        raise PackagingError("__init__.py does not define classFactory(iface)")
    icon = metadata.get("icon")
    if icon and not (package_dir / icon).is_file():
        raise PackagingError(f"the icon {icon} named in metadata.txt does not exist")
    return version


def _wanted(path: Path, package_dir: Path) -> bool:
    relative = path.relative_to(package_dir)
    if any(part in _SKIP_DIRS for part in relative.parts[:-1]):
        return False
    name = path.name
    return name not in _SKIP_NAMES and not name.endswith(_SKIP_SUFFIXES)


def collect_files(package_dir: Path, root: Path) -> list[tuple[Path, str]]:
    """``(source path, archive name)`` pairs, sorted by archive name."""
    entries = [
        (path, f"{PACKAGE}/{path.relative_to(package_dir).as_posix()}")
        for path in package_dir.rglob("*")
        if path.is_file() and _wanted(path, package_dir)
    ]
    for name in EXTRA_FILES:
        source = root / name
        if source.is_file():
            entries.append((source, f"{PACKAGE}/{name}"))
    return sorted(entries, key=lambda entry: entry[1])


def _timestamp() -> tuple[int, int, int, int, int, int]:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
    stamp = time.gmtime(max(epoch, 315532800))  # zip cannot store dates before 1980
    return (stamp.tm_year, stamp.tm_mon, stamp.tm_mday, stamp.tm_hour, stamp.tm_min, stamp.tm_sec)


def build(out_dir: Path | None = None, root: Path = ROOT) -> Path:
    """Create the archive and return its path."""
    package_dir = root / PACKAGE
    if not package_dir.is_dir():
        raise PackagingError(f"{package_dir} does not exist")
    version = check_sources(package_dir)
    target_dir = Path(out_dir) if out_dir is not None else root / "dist"
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / f"{PACKAGE}-{version}.zip"
    stamp = _timestamp()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source, name in collect_files(package_dir, root):
            info = zipfile.ZipInfo(name, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, source.read_bytes())
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=None, help="output directory (default: dist/)")
    args = parser.parse_args(argv)
    try:
        archive = build(args.out)
    except PackagingError as exc:
        print(f"package.py: {exc}", file=sys.stderr)
        return 1
    print(f"{archive} ({archive.stat().st_size / 1024:.1f} KiB)")
    print("Install it in QGIS: Plugins > Manage and Install Plugins > Install from ZIP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
