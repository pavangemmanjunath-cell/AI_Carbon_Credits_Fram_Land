"""Identifier generation.

Plot ids are ``"PLT-"`` followed by 6 characters from the RFC 4648 base32
alphabet (A–Z, 2–7), drawn from ``secrets`` so they are unguessable. This
matches ``data/schemas/plot.schema.json`` (``^PLT-[A-Z0-9]{4,12}$``).
"""

from __future__ import annotations

import base64
import secrets

PLOT_ID_PREFIX = "PLT-"
PLOT_ID_LENGTH = 6


def new_plot_id(length: int = PLOT_ID_LENGTH) -> str:
    """Return a fresh plot id such as ``PLT-7F3K2Q``."""
    raw = secrets.token_bytes(10)
    alphabet = base64.b32encode(raw).decode("ascii").rstrip("=")
    return PLOT_ID_PREFIX + alphabet[:length]
