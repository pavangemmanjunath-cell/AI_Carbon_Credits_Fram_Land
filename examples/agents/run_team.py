#!/usr/bin/env python3
"""Watch the AgriCarbon agent team work — no server, no network, no API key.

Run from the repository root::

    python3 examples/agents/run_team.py                     # full assessment of PLT-DEMOIN
    python3 examples/agents/run_team.py --plan quick-estimate
    python3 examples/agents/run_team.py --ask "How much carbon if I add 200 trees?"
    python3 examples/agents/run_team.py --ask "मेरे खेत में कितना कार्बन है?" --locale hi
    python3 examples/agents/run_team.py --plot PLT-DEMOUS --json

What happens:

1. the API's application context is built in **demo mode** (synthetic data);
2. the three demo plots are seeded, exactly as the API does on start-up;
3. :class:`app.agents.service.AgentService` runs a plan (or answers a question);
4. the transcript is printed: who said what, which tools they used, which
   guardrails passed, and who wrote what on the blackboard.

Read docs/agents/README.md next to this output.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Works without installing anything: fall back to the source folders when the
# packages are not installed (``make install`` installs them in editable mode).
for folder in (
    "apps/api",
    "packages/agent-framework",
    "packages/carbon-engine",
    "packages/geo-engine",
    "packages/policy-engine",
    "packages/report-engine",
    "integrations",
):
    path = str(ROOT / folder)
    if path not in sys.path:
        sys.path.append(path)

os.environ.setdefault("ATLAS_MODE", "demo")
os.environ.setdefault("ATLAS_LOG_LEVEL", "warning")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AgriCarbon agent team on a demo plot.")
    parser.add_argument("--plot", default="PLT-DEMOIN", help="demo plot id (default PLT-DEMOIN)")
    parser.add_argument(
        "--plan",
        default="full-assessment",
        choices=["full-assessment", "quick-estimate", "tree-age-check"],
    )
    parser.add_argument("--ask", metavar="QUESTION", help="ask a question instead of a plan")
    parser.add_argument("--locale", default="en", help="language code, e.g. en, hi, kn, de")
    parser.add_argument("--json", action="store_true", help="print the stored run as JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    from app.agents.service import AgentService
    from app.context import build_context
    from app.core.config import Settings
    from app.demo_seed import seed_demo_plots
    from atlas_agents import render_transcript

    settings = Settings(ATLAS_MODE="demo", ATLAS_RATE_LIMIT_ENABLED=False)  # type: ignore[call-arg]
    context = build_context(settings)
    seed_demo_plots(context)
    team = AgentService(context)

    if args.ask:
        run = team.ask(args.ask, args.plot, args.locale)
    else:
        run = team.run(args.plot, args.plan, None, args.locale)

    if args.json:
        print(json.dumps(run, indent=2, ensure_ascii=False))
    else:
        print(render_transcript(run))
    return 0 if run["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
