"""AgriCarbon Atlas agents — the domain layer on top of the ``atlas_agents`` framework.

==================  ==============================================================
``tools.py``        tools that wrap the existing services (plots, analysis, trees,
                    carbon, policy, market, simulate, reports, optional features)
``wording.py``      the deterministic sentence templates
``coordinator.py``  opens and closes every run
``land.py`` …       one module per specialist agent
``plans.py``        full-assessment, quick-estimate, tree-age-check
``catalog.py``      the team and its ``GET /agents`` description
``service.py``      :class:`AgentService` — runs plans, stores runs
``schemas.py``      request bodies for the agent endpoints
==================  ==============================================================

The framework (``packages/agent-framework``) must be importable: install it
with ``python3 -m pip install -e packages/agent-framework``. This package never
changes ``sys.path`` itself. Learning guide: ``docs/agents/README.md``.
"""
