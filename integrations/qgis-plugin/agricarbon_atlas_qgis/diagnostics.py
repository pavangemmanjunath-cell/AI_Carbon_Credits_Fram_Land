# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Privacy-safe descriptions of unexpected exceptions for the QGIS log (pure Python).

The message of an exception can contain the data that was being processed (a coordinate in a
``ValueError``, a server error text), and a full traceback prints it. The plugin therefore logs
only the exception type and the code location.
"""

from __future__ import annotations

import os
import traceback


def exception_summary(exc: BaseException, depth: int = 3) -> str:
    """``TypeName (file.py:12 function <- other.py:40 caller)``: never the exception message."""
    frames = traceback.extract_tb(exc.__traceback__)[-depth:]
    where = " <- ".join(
        f"{os.path.basename(frame.filename)}:{frame.lineno} {frame.name}"
        for frame in reversed(frames)
    )
    return f"{type(exc).__name__} ({where or 'no frame'})"
