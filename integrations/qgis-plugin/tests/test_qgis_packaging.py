# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Tests of the plugin package: metadata, licence headers, import rules, ZIP and documentation."""

from __future__ import annotations

import ast
import configparser
import importlib.util
import re
import shutil
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = PLUGIN_ROOT / "agricarbon_atlas_qgis"
REPO_ROOT = PLUGIN_ROOT.parents[1]
README = PLUGIN_ROOT / "README.md"
USER_GUIDE = REPO_ROOT / "docs" / "user-guide" / "qgis-plugin.md"

PURE_MODULES = (
    "version",
    "config",
    "geometry",
    "crowns",
    "api_client",
    "formatting",
    "workflows",
    "diagnostics",
)
QGIS_MODULES = ("qgis_helpers", "tasks", "dialogs", "plugin")
SKIPPED_DIRS = {"__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache", "dist"}
DISCLAIMER = "Scenario estimate only. This is not an issued carbon credit."


def project_files(pattern: str) -> Iterator[Path]:
    for path in sorted(PLUGIN_ROOT.rglob(pattern)):
        if not SKIPPED_DIRS.intersection(path.relative_to(PLUGIN_ROOT).parts):
            yield path


def package_files(pattern: str = "*.py") -> list[Path]:
    return [p for p in sorted(PACKAGE_DIR.rglob(pattern)) if "__pycache__" not in p.parts]


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_names(tree: ast.AST) -> set[str]:
    """Top-level module names, and sibling module names for relative imports."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                names.add((node.module or "").split(".")[0])
            elif node.module:
                names.add(node.module.split(".")[0])
            else:
                names.update(alias.name for alias in node.names)
    return names


@pytest.fixture(scope="module")
def packager() -> ModuleType:
    """``scripts/package.py`` loaded by path (``scripts`` is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "agricarbon_atlas_qgis_package_script", PLUGIN_ROOT / "scripts" / "package.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def metadata() -> dict[str, str]:
    parser = configparser.ConfigParser()
    parser.read(PACKAGE_DIR / "metadata.txt", encoding="utf-8")
    return dict(parser["general"])


# =========================================================================== metadata
def test_metadata_has_the_documented_identity(metadata: dict[str, str]) -> None:
    assert metadata["name"] == "AgriCarbon Atlas"
    assert metadata["qgisminimumversion"] == "3.28"
    assert re.fullmatch(r"\d+\.\d+\.\d+", metadata["version"])
    assert metadata["experimental"].lower() == "true"
    assert metadata["icon"] == "icon.svg" and (PACKAGE_DIR / "icon.svg").is_file()
    assert metadata["repository"].startswith("https://github.com/")
    assert metadata["tracker"].startswith("https://github.com/")
    assert "carbon" in metadata["tags"] and "agriculture" in metadata["tags"]
    assert metadata["author"] and metadata["email"]


def test_metadata_says_estimates_not_credits(metadata: dict[str, str]) -> None:
    assert "estimates, not credits" in metadata["description"].lower()
    about = metadata["about"].lower()
    assert "not issued carbon credits" in about and "certified: false" in about
    assert "never added together" in about
    assert "gpl-2.0-or-later" in about and "apache-2.0" in about


def test_metadata_text_is_safe_for_qgis() -> None:
    text = (PACKAGE_DIR / "metadata.txt").read_text(encoding="utf-8")
    assert "%" not in text  # configparser interpolation would reject it
    assert text.startswith("[general]")


def test_the_version_in_metadata_matches_the_code(
    packager: ModuleType, metadata: dict[str, str]
) -> None:
    from agricarbon_atlas_qgis import version

    assert packager.check_sources(PACKAGE_DIR) == metadata["version"] == version.__version__
    assert version.REPOSITORY_URL == metadata["repository"]
    assert version.DISCLAIMER == DISCLAIMER
    assert version.USER_AGENT.endswith(version.__version__)


def test_the_icons_are_valid_svg_in_the_brand_colour() -> None:
    icons = [PACKAGE_DIR / "icon.svg", *sorted((PACKAGE_DIR / "icons").glob("*.svg"))]
    assert len(icons) == 5
    for icon in icons:
        root = ET.parse(icon).getroot()
        assert root.tag.endswith("svg"), icon
        assert "#1e6b41" in icon.read_text(encoding="utf-8").lower(), icon


# =========================================================================== licence
def test_every_python_file_carries_the_gpl_header() -> None:
    files = list(project_files("*.py"))
    assert len(files) > 15
    for path in files:
        head = path.read_text(encoding="utf-8").splitlines()[:4]
        assert any("SPDX-License-Identifier: GPL-2.0-or-later" in line for line in head), path


def test_license_file_is_gpl_2_or_later_and_explains_its_scope() -> None:
    text = (PLUGIN_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: GPL-2.0-or-later" in text.splitlines()[0]
    assert "GNU GENERAL PUBLIC LICENSE" in text and "Version 2, June 1991" in text
    assert "Apache" in text  # the scope note: the rest of the repository is Apache-2.0
    assert text.rstrip().endswith("Public License instead of this License.")


def test_the_zip_is_ignored_by_git() -> None:
    assert "dist/" in (PLUGIN_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


# =========================================================================== import rules
@pytest.mark.parametrize("module", PURE_MODULES)
def test_pure_modules_do_not_import_qgis_qt_or_the_qgis_modules(module: str) -> None:
    forbidden = {"qgis", "PyQt5", "PyQt6", "sip", *QGIS_MODULES}
    found = imported_names(parse(PACKAGE_DIR / f"{module}.py")) & forbidden
    assert found == set(), f"{module}.py imports {sorted(found)}"


@pytest.mark.parametrize("module", QGIS_MODULES)
def test_qgis_modules_use_qgis_pyqt_and_not_pyqt_directly(module: str) -> None:
    found = imported_names(parse(PACKAGE_DIR / f"{module}.py")) & {"PyQt5", "PyQt6", "sip"}
    assert found == set()


def test_the_package_init_imports_the_plugin_lazily() -> None:
    tree = parse(PACKAGE_DIR / "__init__.py")
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "classFactory"
    )
    assert [arg.arg for arg in factory.args.args] == ["iface"]


def test_pure_modules_import_in_an_interpreter_without_qgis() -> None:
    code = textwrap.dedent(
        f"""
        import importlib, sys
        sys.modules["qgis"] = None  # "import qgis" now raises ImportError
        sys.path.insert(0, {str(PLUGIN_ROOT)!r})
        import agricarbon_atlas_qgis
        for name in {PURE_MODULES!r}:
            importlib.import_module("agricarbon_atlas_qgis." + name)
        print("ok")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


# =========================================================================== code hygiene
_NEWER_THAN_39 = {"pairwise", "TypeAlias", "ParamSpec", "StrEnum", "ExceptionGroup", "Self", "UTC"}
_TYPE_NAMES = {"int", "str", "float", "bool", "bytes", "dict", "list", "tuple", "set", "None"}


def _annotation_nodes(tree: ast.AST) -> set[int]:
    """ids of all nodes inside annotations (evaluated lazily thanks to ``__future__``)."""
    inside: set[int] = set()

    def mark(annotation: ast.AST | None) -> None:
        if annotation is not None:
            inside.update(id(n) for n in ast.walk(annotation))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mark(node.returns)
            for arg in [*node.args.args, *node.args.kwonlyargs, *node.args.posonlyargs]:
                mark(arg.annotation)
            for arg in (node.args.vararg, node.args.kwarg):
                mark(arg.annotation if arg else None)
        elif isinstance(node, ast.AnnAssign):
            mark(node.annotation)
    return inside


def _type_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    return node.id if isinstance(node, ast.Name) else None


@pytest.mark.parametrize("path", list(project_files("*.py")), ids=lambda p: p.name)
def test_code_runs_on_python_3_9(path: Path) -> None:
    """QGIS 3.28 LTR can ship Python 3.9; the CI interpreter is newer and would not notice."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path), feature_version=(3, 9))
    annotations = _annotation_nodes(tree)
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            keywords = {kw.arg for kw in node.keywords}
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name == "zip" and "strict" in keywords:
                problems.append(f"line {node.lineno}: zip(strict=...) needs 3.10")
            if name == "dataclass" and keywords & {"slots", "kw_only"}:
                problems.append(f"line {node.lineno}: dataclass slots/kw_only need 3.10")
        if isinstance(node, ast.Attribute) and node.attr in _NEWER_THAN_39:
            problems.append(f"line {node.lineno}: {node.attr} needs a newer Python")
        if isinstance(node, ast.Import) and any(a.name == "tomllib" for a in node.names):
            problems.append(f"line {node.lineno}: tomllib needs 3.11")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            names = {_type_name(node.left), _type_name(node.right)} - {None}
            if names & _TYPE_NAMES and id(node) not in annotations:
                problems.append(f"line {node.lineno}: 'X | Y' outside an annotation needs 3.10")
        if isinstance(node, ast.ImportFrom):
            problems += [
                f"line {node.lineno}: {a.name} needs a newer Python"
                for a in node.names
                if a.name in _NEWER_THAN_39
            ]
    assert problems == [], f"{path.name}: {problems}"


_SENSITIVE = {
    "polygon",
    "geometry",
    "coordinates",
    "geom",
    "rings",
    "ring",
    "centroid",
    "body",
    "payload",
    "lon",
    "lat",
    "api_key",
    "_api_key",
    "headers",
}


@pytest.mark.parametrize("path", package_files(), ids=lambda p: p.name)
def test_log_calls_never_receive_coordinates_bodies_or_keys(path: Path) -> None:
    levels = {"debug", "info", "warning", "error", "exception", "critical", "log"}
    offenders: list[str] = []
    for node in ast.walk(parse(path)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in levels:
            continue
        owner = node.func.value
        if not (isinstance(owner, ast.Name) and owner.id in {"log", "logger", "logging"}):
            continue
        for argument in [*node.args, *(kw.value for kw in node.keywords)]:
            for inner in ast.walk(argument):
                ident = inner.id if isinstance(inner, ast.Name) else getattr(inner, "attr", None)
                if ident in _SENSITIVE:
                    offenders.append(f"line {node.lineno}: {ident}")
        if node.func.attr == "exception":
            offenders.append(f"line {node.lineno}: log.exception prints the exception message")
    assert offenders == []


@pytest.mark.parametrize("path", package_files(), ids=lambda p: p.name)
def test_the_package_never_prints(path: Path) -> None:
    prints = [
        node.lineno
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert prints == []


def test_no_secrets_are_hard_coded() -> None:
    pattern = re.compile(
        r"""(?ix)(api[_-]?key|secret|token|password)\s*[:=]\s*["'][A-Za-z0-9_\-+/=]{16,}["']"""
    )
    for path in package_files():
        assert not pattern.search(path.read_text(encoding="utf-8")), path
    for path in package_files("*.txt") + package_files("*.svg"):
        assert "BEGIN PRIVATE KEY" not in path.read_text(encoding="utf-8"), path


# =========================================================================== the ZIP
def build_zip(packager: ModuleType, out: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1767225600")  # 2026-01-01
    return packager.build(out)


def test_the_zip_has_one_top_level_folder_and_the_expected_files(
    packager: ModuleType, tmp_path: Path, metadata: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = build_zip(packager, tmp_path, monkeypatch)
    assert archive.name == f"agricarbon_atlas_qgis-{metadata['version']}.zip"
    with zipfile.ZipFile(archive) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
    assert {name.split("/")[0] for name in names} == {"agricarbon_atlas_qgis"}
    expected = {
        f"agricarbon_atlas_qgis/{path.relative_to(PACKAGE_DIR).as_posix()}"
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    } | {"agricarbon_atlas_qgis/LICENSE", "agricarbon_atlas_qgis/README.md"}
    assert set(names) == expected
    assert names == sorted(names)
    for needed in ("metadata.txt", "__init__.py", "plugin.py", "icon.svg", "icons/send.svg"):
        assert f"agricarbon_atlas_qgis/{needed}" in names
    forbidden = ("tests/", "scripts/", "Makefile", "ruff.toml", ".pyc", "__pycache__", "dist/")
    assert not [n for n in names if any(part in n for part in forbidden)]


def test_the_zip_is_reproducible(
    packager: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = build_zip(packager, tmp_path / "one", monkeypatch).read_bytes()
    second = build_zip(packager, tmp_path / "two", monkeypatch).read_bytes()
    assert first == second


def test_the_zip_files_use_plain_permissions(
    packager: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with zipfile.ZipFile(build_zip(packager, tmp_path, monkeypatch)) as zf:
        assert {info.external_attr >> 16 for info in zf.infolist()} == {0o644}
        assert {info.date_time[0] for info in zf.infolist()} == {2026}


def test_the_unpacked_zip_imports_without_the_source_tree(
    packager: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = build_zip(packager, tmp_path, monkeypatch)
    target = tmp_path / "plugins"
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target)
    code = textwrap.dedent(
        f"""
        import sys
        sys.modules["qgis"] = None
        sys.path.insert(0, {str(target)!r})
        from agricarbon_atlas_qgis import api_client, version
        print(version.__version__, api_client.__file__)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    assert str(target) in result.stdout


def copy_sources(tmp_path: Path) -> Path:
    """A throw-away copy of the plugin directory to break on purpose."""
    root = tmp_path / "copy"
    shutil.copytree(
        PACKAGE_DIR, root / "agricarbon_atlas_qgis", ignore=shutil.ignore_patterns("__pycache__")
    )
    for name in ("LICENSE", "README.md"):
        shutil.copy(PLUGIN_ROOT / name, root / name)
    return root


def test_caches_and_editor_files_are_left_out(
    packager: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_sources(tmp_path)
    package = root / "agricarbon_atlas_qgis"
    (package / "__pycache__").mkdir()
    (package / "__pycache__" / "x.cpython-312.pyc").write_bytes(b"x")
    (package / ".DS_Store").write_bytes(b"x")
    (package / "plugin.py~").write_text("backup", encoding="utf-8")
    (package / "notes.orig").write_text("merge leftover", encoding="utf-8")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1767225600")
    with zipfile.ZipFile(packager.build(tmp_path / "out", root=root)) as zf:
        names = zf.namelist()
    assert not [n for n in names if "pycache" in n or n.endswith(("~", ".orig", ".DS_Store"))]
    assert "agricarbon_atlas_qgis/plugin.py" in names


def test_a_version_mismatch_stops_the_build(packager: ModuleType, tmp_path: Path) -> None:
    root = copy_sources(tmp_path)
    version_file = root / "agricarbon_atlas_qgis" / "version.py"
    version_file.write_text(
        version_file.read_text(encoding="utf-8").replace('__version__ = "', '__version__ = "9.'),
        encoding="utf-8",
    )
    with pytest.raises(packager.PackagingError, match="metadata.txt says version"):
        packager.build(tmp_path / "out", root=root)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("key", ["name", "version", "description", "about", "author", "repository"])
def test_missing_metadata_keys_stop_the_build(
    packager: ModuleType, tmp_path: Path, key: str
) -> None:
    root = copy_sources(tmp_path)
    metadata_file = root / "agricarbon_atlas_qgis" / "metadata.txt"
    lines = metadata_file.read_text(encoding="utf-8").splitlines()
    metadata_file.write_text(
        "\n".join(line for line in lines if not line.startswith(f"{key}=")), encoding="utf-8"
    )
    with pytest.raises(packager.PackagingError, match=f"missing: .*{key}"):
        packager.build(tmp_path / "out", root=root)


def test_a_missing_icon_or_class_factory_stops_the_build(
    packager: ModuleType, tmp_path: Path
) -> None:
    root = copy_sources(tmp_path)
    (root / "agricarbon_atlas_qgis" / "icon.svg").unlink()
    with pytest.raises(packager.PackagingError, match="icon"):
        packager.build(tmp_path / "out", root=root)
    root = copy_sources(tmp_path / "again")
    (root / "agricarbon_atlas_qgis" / "__init__.py").write_text("", encoding="utf-8")
    with pytest.raises(packager.PackagingError, match="classFactory"):
        packager.build(tmp_path / "out2", root=root)


def test_the_command_line_builds_into_the_chosen_folder(
    packager: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert packager.main(["--out", str(tmp_path)]) == 0
    assert list(tmp_path.glob("agricarbon_atlas_qgis-*.zip"))
    assert "Install from ZIP" in capsys.readouterr().out


# =========================================================================== documentation
def markdown_links(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    return re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", text)


def heading_slugs(path: Path) -> set[str]:
    slugs: set[str] = set()
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and re.match(r"#{1,6} ", line):
            text = re.sub(r"[`*_]", "", re.sub(r"^#{1,6} ", "", line)).strip().lower()
            slugs.add(re.sub(r"[^\w\- ]", "", text).replace(" ", "-"))
    return slugs


def documents() -> list[Path]:
    return [path for path in (README, USER_GUIDE) if path.is_file()]


def test_the_readme_exists_and_covers_what_users_must_know() -> None:
    text = README.read_text(encoding="utf-8")
    for needle in (
        DISCLAIMER,
        "certified: false",
        "Install from ZIP",
        "http://localhost:8000/api/v1",
        "X-API-Key",
        "authentication manager",
        "AI segmentation",
        "Select Features",
        "Count trees from segmentation layer",
        "Estimate carbon",
        "Run AI agent team",
        "Google, Bing and Esri",
        "automated feature extraction",
        "Sentinel-2",
        "GPL-2.0-or-later",
        "Apache-2.0",
        "estimated annual carbon removal",
        "never added together",
        "model-estimated",
    ):
        assert needle in text, needle
    assert "ESG amount" not in text


@pytest.mark.skipif(not USER_GUIDE.is_file(), reason="the plugin is not inside the repository")
def test_the_user_guide_page_links_to_the_readme_and_repeats_the_rules() -> None:
    text = USER_GUIDE.read_text(encoding="utf-8")
    assert "../../integrations/qgis-plugin/README.md" in text
    for needle in (DISCLAIMER, "certified: false", "Install from ZIP", "Google, Bing and Esri"):
        assert needle in text, needle
    assert "ESG amount" not in text


@pytest.mark.parametrize("document", documents(), ids=lambda p: p.name)
def test_relative_links_and_anchors_resolve(document: Path) -> None:
    broken: list[str] = []
    for target in markdown_links(document):
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue  # external links are checked by the repository's link checker
        name, _, anchor = target.partition("#")
        destination = (document.parent / name).resolve() if name else document
        if not destination.exists():
            broken.append(target)
        elif anchor and destination.suffix == ".md" and anchor not in heading_slugs(destination):
            broken.append(target)
    assert broken == []


def test_documents_keep_to_the_markdown_line_length() -> None:
    for document in documents():
        in_code = False
        for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("```"):
                in_code = not in_code
            elif not (in_code or line.startswith(("|", "#"))):
                assert len(line) <= 120, f"{document.name}:{number}"
                assert line == line.rstrip(), f"{document.name}:{number} has trailing spaces"
