# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Plugin identity constants shared by the pure-Python modules (no QGIS imports)."""

from __future__ import annotations

# Keep in sync with ``metadata.txt`` (a test enforces this).
__version__ = "0.1.0"

PLUGIN_NAME = "AgriCarbon Atlas"
#: Placeholder until the project has its final home; keep in sync with ``metadata.txt``.
REPOSITORY_URL = "https://github.com/agricarbon-atlas/agricarbon-atlas"
USER_AGENT = f"AgriCarbonAtlas-QGIS/{__version__}"

#: Shown next to every estimate. Wording is fixed by the project's CLAUDE.md rules.
DISCLAIMER = "Scenario estimate only. This is not an issued carbon credit."
