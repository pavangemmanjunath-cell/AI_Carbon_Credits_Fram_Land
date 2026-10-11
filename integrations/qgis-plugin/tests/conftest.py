# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Shared fixtures of the QGIS plugin tests.

The plugin package is imported as ``carboncreditbuy_qgis``; its parent directory
(``integrations/qgis-plugin``) goes on ``sys.path`` here because that directory name contains a
hyphen and cannot be a package. QGIS itself is never needed: the pure-Python modules are
tested directly and the QGIS-dependent ones run against the fakes in ``qgis_fakes.py``.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

TESTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = TESTS_DIR.parent
PACKAGE_DIR = PLUGIN_ROOT / "carboncreditbuy_qgis"

for entry in (str(PLUGIN_ROOT), str(TESTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import qgis_fakes  # noqa: E402
from qgis_plugin_fake_server import FakeAtlasServer  # noqa: E402


@pytest.fixture
def fake_qgis(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    """A fake ``qgis.core`` (no Qt): enough for ``qgis_helpers`` and ``tasks``."""
    core = qgis_fakes.install(monkeypatch)
    try:
        yield core
    finally:
        qgis_fakes.forget_plugin_modules()


@pytest.fixture
def fake_qgis_qt(monkeypatch: pytest.MonkeyPatch, offscreen_qt: object) -> Iterator[ModuleType]:
    """The fakes plus real PyQt5 widgets on the offscreen platform (skipped without PyQt5)."""
    core = qgis_fakes.install(monkeypatch, qt=True)
    try:
        yield core
    finally:
        qgis_fakes.forget_plugin_modules()


@pytest.fixture
def atlas_server() -> Iterator[FakeAtlasServer]:
    """A local HTTP server that plays the CarbonCreditBuy API."""
    server = FakeAtlasServer()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def plugin_root() -> Path:
    return PLUGIN_ROOT


@pytest.fixture
def package_dir() -> Path:
    return PACKAGE_DIR


_QT_APP: list[object] = []  # one QApplication for the whole test run (Qt allows only one)


@pytest.fixture
def offscreen_qt(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """A ``QApplication`` on Qt's offscreen platform, or skip when PyQt5 is not installed."""
    pytest.importorskip("PyQt5.QtWidgets")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["carboncreditbuy-tests"])
        _QT_APP.append(app)  # keep it alive: a garbage-collected QApplication cannot be reused
    yield app
    app.processEvents()
