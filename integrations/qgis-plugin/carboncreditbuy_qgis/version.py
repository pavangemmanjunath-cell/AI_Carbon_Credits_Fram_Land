# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Plugin identity constants shared by the pure-Python modules (no QGIS imports)."""

from __future__ import annotations

# Keep in sync with ``metadata.txt`` (a test enforces this).
__version__ = "0.1.0"

PLUGIN_NAME = "CarbonCreditBuy"
#: Placeholder until the project has its final home; keep in sync with ``metadata.txt``.
REPOSITORY_URL = "https://github.com/pavangemmanjunath-cell/Carbon_Credits_Fram_Land"
USER_AGENT = f"CarbonCreditBuy-QGIS/{__version__}"

#: Shown next to every estimate. Wording is fixed by the project's CLAUDE.md rules.
DISCLAIMER = "Scenario estimate only. This is not an issued carbon credit."
