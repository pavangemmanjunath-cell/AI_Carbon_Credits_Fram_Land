# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""CarbonCreditBuy QGIS plugin.

QGIS calls :func:`classFactory` when it loads the plugin. The import of ``plugin`` is deferred
so the pure-Python modules in this package (``api_client``, ``geometry``, ``crowns``,
``formatting``, ``workflows``, ``config``) can be imported - and unit-tested - without QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # noqa: N802 - the name is fixed by the QGIS plugin API
    """Return the plugin instance (called by QGIS with the ``QgisInterface``)."""
    from .plugin import CarbonCreditBuyPlugin

    return CarbonCreditBuyPlugin(iface)
