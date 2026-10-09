"""Keep the agent docs honest: every agent, tool and key documented; links and anchors resolve."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.agents.catalog import build_team, who_says_what

ROOT = Path(__file__).resolve().parents[3]
GUIDE = ROOT / "docs" / "agents" / "README.md"
CATALOG = ROOT / "docs" / "agents" / "catalog.md"
DOCS = [
    GUIDE,
    CATALOG,
    ROOT / "docs" / "architecture" / "adr" / "0006-agentic-framework.md",
    ROOT / "packages" / "agent-framework" / "README.md",
]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def _slug(heading: str) -> str:
    """GitHub-style anchor for a Markdown heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def test_catalog_page_documents_every_agent_tool_and_key():
    page = CATALOG.read_text(encoding="utf-8")
    missing: list[str] = []
    for agent in build_team():
        needles = [f"{agent.title} (`{agent.id}`)", *(f"`{t.name}`" for t in agent.tools)]
        needles += [f"`{key}`" for key in (*agent.reads, *agent.writes) if key != "*"]
        missing += [f"{agent.id}: {n}" for n in needles if n not in page]
    assert not missing, f"docs/agents/catalog.md is missing: {missing}"


def test_who_says_what_table_matches_the_code():
    guide = GUIDE.read_text(encoding="utf-8")
    stale = [row for row in who_says_what().splitlines() if row not in guide]
    assert not stale, (
        "Update section 5 of docs/agents/README.md with who_says_what():\n" + "\n".join(stale)
    )


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_and_anchors_resolve(doc: Path):
    text = doc.read_text(encoding="utf-8")
    headings = {_slug(h) for h in re.findall(r"^#{1,6} (.+)$", text, flags=re.M)}
    broken: list[str] = []
    for target in LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path_part, _, anchor = target.partition("#")
        if not path_part:
            if anchor not in headings:
                broken.append(target)
            continue
        if not (doc.parent / path_part).resolve().exists():
            broken.append(target)
    assert not broken, f"broken links in {doc.name}: {broken}"


def test_framework_readme_example_runs(capsys):
    readme = (ROOT / "packages" / "agent-framework" / "README.md").read_text(encoding="utf-8")
    example = re.search(r"## A team in forty lines\n\n```python\n(.*?)```", readme, re.S)
    assert example, "the README example block moved"
    exec(compile(example.group(1), "agent-framework-readme", "exec"), {})
    out = capsys.readouterr().out
    assert "status: completed" in out and "Field north has 420 trees." in out
