# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""A tiny threaded HTTP server that plays the CarbonCreditBuy API in the plugin tests.

Register canned answers with :meth:`FakeAtlasServer.route`; every request that reaches the
server is recorded in :attr:`FakeAtlasServer.requests` so tests can check headers and bodies.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit


@dataclass
class RecordedRequest:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


@dataclass
class Answer:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    delay_s: float = 0.0


Handler = Callable[[RecordedRequest], Answer]


def json_answer(status: int, payload: Any, headers: Mapping[str, str] | None = None) -> Answer:
    return Answer(
        status=status,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **dict(headers or {})},
    )


def problem_answer(
    status: int,
    title: str,
    detail: str = "",
    slug: str = "",
    errors: list[dict[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Answer:
    """An RFC 7807 ``application/problem+json`` answer shaped like CarbonCreditBuy API's."""
    payload: dict[str, Any] = {
        "type": f"https://carboncreditbuy.example/problems/{slug}" if slug else "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if errors:
        payload["errors"] = errors
    return Answer(
        status=status,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/problem+json", **dict(headers or {})},
    )


class FakeAtlasServer:
    """Threaded server bound to an ephemeral loopback port."""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self._routes: dict[tuple[str, str], Handler | Answer] = {}
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _dispatch(self) -> None:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                request = RecordedRequest(
                    method=self.command,
                    path=parts.path,
                    query=parse_qs(parts.query),
                    headers={k.lower(): v for k, v in self.headers.items()},
                    body=body,
                )
                outer.requests.append(request)
                route = outer._routes.get((self.command, parts.path))
                if route is None:
                    answer = problem_answer(404, "Not Found", f"No route {parts.path}", "no-route")
                else:
                    answer = route(request) if callable(route) else route
                if answer.delay_s:
                    time.sleep(answer.delay_s)
                try:
                    self.send_response(answer.status)
                    for name, value in answer.headers.items():
                        self.send_header(name, value)
                    self.send_header("Content-Length", str(len(answer.body)))
                    self.end_headers()
                    self.wfile.write(answer.body)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the client gave up (timeout tests)

            do_GET = do_POST = do_PUT = do_DELETE = _dispatch  # noqa: N815

            def log_message(self, *_args: Any) -> None:  # keep test output quiet
                return None

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=lambda: self._server.serve_forever(poll_interval=0.01), daemon=True
        )
        self._thread.start()

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def base_url(self) -> str:
        return f"{self.origin}/api/v1"

    def route(
        self,
        method: str,
        path: str,
        answer: Answer | Handler | None = None,
        *,
        status: int = 200,
        payload: Any = None,
    ) -> None:
        """Answer ``method`` + ``/api/v1<path>`` with an :class:`Answer`, a handler or JSON."""
        if answer is None:
            answer = json_answer(status, payload if payload is not None else {})
        self._routes[(method.upper(), f"/api/v1{path}")] = answer

    def requests_to(self, method: str, path: str) -> list[RecordedRequest]:
        return [r for r in self.requests if r.method == method and r.path == f"/api/v1{path}"]

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
