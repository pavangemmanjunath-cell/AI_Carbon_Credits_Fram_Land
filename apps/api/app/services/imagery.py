"""Imagery providers for the web map's "Satellite" view (``config/imagery/providers.yaml``).

The YAML holds URL templates with ``${NAME}`` placeholders for keys that must never be committed
(CLAUDE.md principle 6). This service substitutes them at run time:

* ``ESRI_API_KEY`` comes from ``Settings.esri_api_key`` (which also reads ``.env``);
* any other ``${…_KEY}`` / ``${…_TOKEN}`` comes from the process environment — but never a
  variable the application owns for another integration (``LLM_API_KEY``, ``USDA_NASS_API_KEY``
  …), so a typo or a bad pull request cannot publish those secrets.

A provider whose key is missing is returned with ``available: false``, a reason and ``url: null``:
an unsubstituted ``${…}`` is never sent to a client. The substituted key is part of the tile URL
the browser needs, so deployers should use a referrer-restricted, basemap-only key; it is never
logged here.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import yaml

from app.core.config import Settings
from app.core.errors import ProblemError

if TYPE_CHECKING:  # pragma: no cover
    from app.context import AppContext

log = logging.getLogger("atlas.imagery")

PROVIDERS_FILE = Path("imagery") / "providers.yaml"
_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_KEY_NAME = re.compile(r"^[A-Z][A-Z0-9_]*_(?:KEY|TOKEN)$")
#: fields served for every provider (docs/architecture/api-contract.md §v0.2 plus notes/sources)
_PASS_THROUGH = (
    "id",
    "name",
    "kind",
    "tile_size",
    "max_zoom",
    "coverage",
    "resolution",
    "license",
    "license_url",
    "attribution",
    "requires_key",
    "commercial_use",
    "analysis_allowed",
    "open_data",
    "verification_status",
    "notes",
    "sources",
)
#: names the application itself uses for other integrations — never substituted from the environment
_RESERVED_NAMES = frozenset(
    str(field.alias) for field in Settings.model_fields.values() if field.alias
) - {"ESRI_API_KEY"}


class ImageryService:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self._doc = self._load(ctx.settings.config_dir)

    # ------------------------------------------------------------------------ public
    def providers(self, country: str | None = None) -> dict[str, Any]:
        """Providers for ``country`` (covering ones first), with the recommended id."""
        code = country.strip().upper() if country else None
        prepared = [self._prepare(entry, code) for entry in self._doc["providers"]]
        # stable: providers that cover the country first, file order otherwise
        ordered = sorted(prepared, key=lambda p: p["covers_country"] is False)
        return {
            "recommended": self._recommended(ordered, code),
            "providers": ordered,
            "notes": str(self._doc.get("notes", "")).strip(),
            "country": code,
            "version": self._doc["version"],
            "updated": self._doc["updated"],
        }

    # ----------------------------------------------------------------------- internals
    @staticmethod
    def _load(config_dir: Path) -> dict[str, Any]:
        path = config_dir / PROVIDERS_FILE
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            if not isinstance(data, dict) or not isinstance(data.get("providers"), list):
                raise ValueError("providers.yaml must contain a 'providers' list")
            data["version"] = str(data.get("version", ""))
            data["updated"] = str(data.get("updated", ""))
            return data
        except (OSError, ValueError, yaml.YAMLError) as exc:
            log.error("imagery providers could not be loaded: %s", type(exc).__name__)
            raise ProblemError(
                500,
                "The imagery provider list is missing or invalid; see the server log.",
                type_slug="imagery-providers-unavailable",
            ) from exc

    def _prepare(self, entry: dict[str, Any], country: str | None) -> dict[str, Any]:
        provider = {key: entry.get(key) for key in _PASS_THROUGH}
        url, missing = self._resolve_url(str(entry.get("url", "")))
        available = url is not None
        provider.update(
            {
                "url": url,
                "available": available,
                "unavailable_reason": None
                if available
                else "Set " + " and ".join(missing or ["its key"]) + " to enable",
                "covers_country": self._covers(entry.get("coverage") or {}, country),
            }
        )
        return provider

    def _resolve_url(self, template: str) -> tuple[str | None, list[str]]:
        """Substitute ``${NAME}``; ``(None, missing names)`` when any value is unavailable."""
        missing: list[str] = []

        def substitute(match: re.Match[str]) -> str:
            name = match.group(1)
            value = self._secret(name)
            if value is None:
                missing.append(name)
                return match.group(0)
            return quote(value, safe="")

        url = _PLACEHOLDER.sub(substitute, template)
        if missing or "${" in url or not url:
            return None, sorted(set(missing))
        return url, []

    def _secret(self, name: str) -> str | None:
        if name == "ESRI_API_KEY":
            value = self.ctx.settings.esri_api_key
        elif _KEY_NAME.match(name) and name not in _RESERVED_NAMES:
            value = os.environ.get(name, "")
        else:
            value = ""
        value = value.strip()
        return value or None

    def _covers(self, coverage: dict[str, Any], country: str | None) -> bool | None:
        """Does the provider's coverage include ``country``? ``None`` when no country is given."""
        if country is None:
            return None
        if coverage.get("type") == "global":
            return True
        if coverage.get("type") != "countries":
            return False
        listed = {str(c).upper() for c in coverage.get("countries", [])}
        if country in listed:
            return True
        # ``EU`` is a region, not an ISO country: covered when any member state is listed
        members = (self.ctx.regions.regions.get(country) or {}).get("member_states") or []
        return bool(listed & {str(m).upper() for m in members})

    def _recommended(self, ordered: list[dict[str, Any]], country: str | None) -> str | None:
        defaults = self._doc.get("default_by_country") or {}
        wanted = defaults.get(country) if country else None
        wanted = wanted or defaults.get("default")
        by_id = {p["id"]: p for p in ordered}
        if wanted in by_id and by_id[wanted]["available"]:
            return str(wanted)
        first = next((p["id"] for p in ordered if p["available"]), None)
        return str(first) if first else None
