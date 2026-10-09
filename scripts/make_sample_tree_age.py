#!/usr/bin/env python3
"""Regenerate the v0.2 sample responses for Tree age and Imagery from the real API.

Usage (from the repository root)::

    python3 scripts/make_sample_tree_age.py          # write the files
    python3 scripts/make_sample_tree_age.py --check  # exit 1 when the files are out of date

Writes ``data/sample/responses/tree-age-{IN,US,EU}.json`` and
``imagery-providers-{IN,US}.json`` by calling the endpoints in-process (FastAPI ``TestClient``;
nothing listens on a port and nothing leaves the machine).

The output is deterministic, so a re-run only changes the files when behaviour or data changed:

* the clock is pinned: ``as_of_year`` is 2026 and every ``generated_at`` is
  ``2026-10-05T00:00:00Z``;
* the Esri key is forced empty, so ``esri-world-imagery`` is listed as unavailable and no key can
  end up in a committed file (CLAUDE.md principle 6);
* the requests describe synthetic trees only: no coordinates and no plot are involved.

``scripts/make_sample_responses.py`` writes the v0.1 samples and is not touched by this script.
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
os.environ.setdefault("ATLAS_LOG_LEVEL", "warning")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

OUT = ROOT / "data" / "sample" / "responses"
AS_OF_YEAR = 2026
PINNED_TIME = "2026-10-05T00:00:00Z"
TIME_KEYS = {"generated_at", "created_at", "time"}

#: sample name -> request body of ``POST /api/v1/tree-age/assess``
ASSESSMENTS: dict[str, dict[str, Any]] = {
    # the headline example: old mango trees on a Haryana farm, no measurements (Tier 1 by age)
    "IN": {
        "country": "IN",
        "subdivision": "IN-HR",
        "setting": "farm",
        "species_id": "mango",
        "age_years": 60,
        "tree_count": 25,
    },
    # mature black walnut in a Portland yard, no measurements
    "US": {
        "country": "US",
        "subdivision": "US-OR",
        "setting": "urban",
        "species_id": "black_walnut",
        "age_years": 45,
        "tree_count": 3,
    },
    # oaks in Berlin with a measured girth and height (Tier 2 allometry, with the age as context)
    "EU": {
        "country": "DE",
        "subdivision": "DE-BE",
        "setting": "urban",
        "species_id": "oak",
        "age_years": 80,
        "tree_count": 4,
        "girth_cm": 190,
        "height_m": 22,
    },
}
#: sample name -> ``country`` query parameter of ``GET /api/v1/imagery/providers``
IMAGERY: dict[str, str] = {"IN": "IN", "US": "US"}


def render(document: Any) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def fetch(response: Any, name: str) -> Any:
    """The JSON body of a successful response; otherwise stop and show the problem document."""
    if response.status_code != 200:
        raise SystemExit(f"{name}: HTTP {response.status_code} {response.text[:500]}")
    return response.json()


def check_deterministic(name: str, document: Any, text: str) -> None:
    """Refuse to write anything that depends on the clock or carries a key."""
    if "${" in text:
        raise SystemExit(f"{name}: an unsubstituted ${{...}} placeholder reached the output")

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in TIME_KEYS and value != PINNED_TIME:
                    raise SystemExit(f"{name}: {key}={value!r} is not pinned")
                if key == "as_of_year" and value != AS_OF_YEAR:
                    raise SystemExit(f"{name}: as_of_year={value!r} is not pinned")
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)


def build() -> dict[str, str]:
    """Call the API in-process and return ``{file name: file text}``."""
    settings = Settings(  # type: ignore[call-arg]
        ATLAS_ENV="development",
        ATLAS_MODE="demo",
        ATLAS_RATE_LIMIT_ENABLED=False,
        ATLAS_API_KEYS="",
        ATLAS_ALLOW_PENDING_PARAMETERS=True,
        ESRI_API_KEY="",
    )
    files: dict[str, str] = {}
    with ExitStack() as stack:
        # pin the clock the services read (the tree-age service imports ``current_year`` by name)
        stack.enter_context(mock.patch("app.services.common.now_iso", return_value=PINNED_TIME))
        stack.enter_context(
            mock.patch("app.services.tree_age.current_year", return_value=AS_OF_YEAR)
        )
        client = stack.enter_context(TestClient(create_app(settings)))
        for name, body in ASSESSMENTS.items():
            response = client.post("/api/v1/tree-age/assess", json=body)
            files[f"tree-age-{name}.json"] = render(fetch(response, f"tree-age-{name}"))
        for name, country in IMAGERY.items():
            response = client.get("/api/v1/imagery/providers", params={"country": country})
            files[f"imagery-providers-{name}.json"] = render(fetch(response, f"imagery-{name}"))
    for file_name, text in files.items():
        check_deterministic(file_name, json.loads(text), text)
    return files


def main(argv: list[str]) -> int:
    files = build()
    if "--check" in argv:
        stale = [
            name
            for name, text in files.items()
            if not (OUT / name).exists() or (OUT / name).read_text(encoding="utf-8") != text
        ]
        for name in stale:
            print(f"out of date: data/sample/responses/{name}", file=sys.stderr)
        if stale:
            print("run: python3 scripts/make_sample_tree_age.py", file=sys.stderr)
        return 1 if stale else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
