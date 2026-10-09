# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Run blocking API calls in a background ``QgsTask`` so the QGIS window stays responsive.

``work`` runs in a worker thread and must not touch widgets, layers or the project; it should
only call the pure-Python client. ``on_success`` / ``on_error`` run on the main thread (QGIS
calls ``QgsTask.finished()`` there), so they may update the user interface.

The task is deliberately *not* cancellable: a request that already left the machine cannot be
recalled, and a "cancelled" label would suggest the server did nothing. Every request has a
timeout instead (Settings).

Privacy: only the task description is logged, never the result or the error text (server error
messages can echo user input).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from qgis.core import QgsApplication, QgsTask

from .diagnostics import exception_summary

log = logging.getLogger(__name__)

# Python must keep the task alive until QGIS has called ``finished``.
_ACTIVE: set[ApiTask] = set()


class ApiTask(QgsTask):
    """A background task that runs ``work()`` and reports back on the main thread."""

    def __init__(
        self,
        description: str,
        work: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        try:
            super().__init__(description, QgsTask.Flags())  # no cancel button, see module doc
        except (AttributeError, TypeError):  # a QGIS 3 build with a different flags API
            super().__init__(description)
        self._work = work
        self._on_success = on_success
        self._on_error = on_error
        self._result: Any = None
        self._error: BaseException | None = None

    def run(self) -> bool:  # worker thread
        try:
            self._result = self._work()
        except Exception as exc:  # reported to the user in finished()
            self._error = exc
            return False
        return True

    def finished(self, result: bool) -> None:  # main thread
        _ACTIVE.discard(self)
        try:
            if self._error is not None:
                self._on_error(self._error)
            elif result:
                self._on_success(self._result)
            else:  # the task manager stopped the task (QGIS is closing)
                self._on_error(RuntimeError("The request was stopped before it finished."))
        except Exception as exc:  # a failing callback must not end up as a traceback popup
            log.error(
                "unexpected failure while showing the result of '%s': %s",
                self.description(),
                exception_summary(exc),
            )


def submit(
    description: str,
    work: Callable[[], Any],
    on_success: Callable[[Any], None],
    on_error: Callable[[BaseException], None],
) -> ApiTask:
    """Queue ``work`` in the QGIS task manager and return the task."""
    task = ApiTask(description, work, on_success, on_error)
    _ACTIVE.add(task)
    QgsApplication.taskManager().addTask(task)
    log.info("started task: %s", description)
    return task


def active_count() -> int:
    """Number of tasks whose result has not been delivered yet."""
    return len(_ACTIVE)
