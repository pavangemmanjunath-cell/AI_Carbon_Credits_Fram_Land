"""Shared httpx MockTransport helpers for integration adapter tests (no network)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx


class Recorder:
    """Collects requests seen by a MockTransport."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


def make_client(
    handler: Callable[[httpx.Request], httpx.Response], recorder: Recorder | None = None
) -> httpx.Client:
    def wrapped(request: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.requests.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(wrapped))


def json_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, content=json.dumps(payload).encode(), headers={"content-type": "application/json"}
    )
