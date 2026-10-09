from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from httpmock import Recorder  # noqa: E402


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()
