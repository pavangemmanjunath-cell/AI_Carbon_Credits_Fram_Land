"""Jinja2-based renderer.

Formats: ``html`` (print-ready, self-contained CSS), ``markdown``, ``json``
(the context itself, canonical), ``pdf`` (HTML → PDF through WeasyPrint when
installed; otherwise :class:`PdfNotAvailableError`, which the API maps to 501).

Two Jinja2 environments are used: an autoescaping one for HTML and a plain
one for Markdown, so rendering is thread-safe.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
FORMATS = ("html", "json", "markdown", "pdf")
MEDIA_TYPES = {
    "html": "text/html; charset=utf-8",
    "json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "pdf": "application/pdf",
}


class PdfNotAvailableError(RuntimeError):
    """WeasyPrint (optional dependency) is not installed."""


def pdf_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except Exception:  # pragma: no cover - depends on the environment
        return False
    return True


def _fmt_number(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if digits == 0:
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}"


def _fmt_pct(value: Any, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.{digits}f}%"


def _humanize(value: Any) -> str:
    return str(value).replace("_", " ").capitalize() if value is not None else "—"


def _make_env(templates_dir: Path, autoescape: bool) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(enabled_extensions=("j2", "html"), default=True)
        if autoescape
        else False,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = _fmt_number
    env.filters["pct"] = _fmt_pct
    env.filters["humanize"] = _humanize
    return env


class ReportRenderer:
    def __init__(self, templates_dir: Path | None = None) -> None:
        directory = templates_dir or TEMPLATES_DIR
        self.html_env = _make_env(directory, autoescape=True)
        self.text_env = _make_env(directory, autoescape=False)

    def render(self, context: Mapping[str, Any], fmt: str) -> bytes:
        if fmt == "html":
            return self.render_html(context).encode("utf-8")
        if fmt == "markdown":
            return self.render_markdown(context).encode("utf-8")
        if fmt == "json":
            return self.render_json(context).encode("utf-8")
        if fmt == "pdf":
            return self.render_pdf(context)
        raise ValueError(f"unknown report format {fmt!r}; expected one of {FORMATS}")

    def render_html(self, context: Mapping[str, Any]) -> str:
        return self.html_env.get_template("report.html.j2").render(**context)

    def render_markdown(self, context: Mapping[str, Any]) -> str:
        return self.text_env.get_template("report.md.j2").render(**context)

    @staticmethod
    def render_json(context: Mapping[str, Any]) -> str:
        return json.dumps(context, indent=2, ensure_ascii=False, default=str)

    def render_pdf(self, context: Mapping[str, Any]) -> bytes:
        try:
            from weasyprint import HTML
        except Exception as exc:  # ImportError or OSError for missing cairo/pango
            raise PdfNotAvailableError(
                "PDF output requires the optional WeasyPrint dependency "
                "(pip install weasyprint, plus system Pango/Cairo)"
            ) from exc
        html = self.render_html(context)
        return bytes(HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf())
