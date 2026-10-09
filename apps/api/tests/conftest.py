from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ATLAS_MODE", "demo")
os.environ.setdefault("ATLAS_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("ATLAS_API_KEYS", "")
os.environ.setdefault("ATLAS_LOG_LEVEL", "warning")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [[77.53, 13.29], [77.54, 13.29], [77.54, 13.30], [77.53, 13.30], [77.53, 13.29]]
    ],
}


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False, ATLAS_API_KEYS="")  # type: ignore[call-arg]
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def square() -> dict:
    return SQUARE
