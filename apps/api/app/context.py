"""Application context: builds repositories, adapters and services once."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.repositories.base import Repository
from app.repositories.memory import MemoryRepository
from app.services.adapters import ModeRouter
from app.services.analysis import AnalysisService
from app.services.carbon import CarbonService
from app.services.cube import CubeService
from app.services.explain import ExplainService
from app.services.market import MarketService
from app.services.plots import PlotService
from app.services.policy import PolicyService
from app.services.regions import RegionConfig, get_region_config
from app.services.reports import ReportService
from app.services.simulate import SimulationService
from app.services.trees import TreeService
from carbon_engine import ParameterStore, get_store
from policy_engine import PolicyEngine

log = logging.getLogger("carboncreditbuy.context")


@dataclass
class AppContext:
    settings: Settings
    repo: Repository
    router: ModeRouter
    regions: RegionConfig
    store: ParameterStore
    policy_engine: PolicyEngine
    plots: PlotService
    analysis: AnalysisService
    cube: CubeService
    trees: TreeService
    carbon: CarbonService
    policy: PolicyService
    market: MarketService
    simulate: SimulationService
    reports: ReportService
    explain: ExplainService
    # Feature modules (agents, imports, tree age, imagery …) keep their lazily built
    # services here — see ``app.services.registry.service``.
    extras: dict[str, Any] = field(default_factory=dict)


def _build_repository(settings: Settings) -> Repository:
    if settings.atlas_repository == "postgres":
        from app.repositories.postgres import PostgresRepository

        log.info("using PostgreSQL repository")
        return PostgresRepository(settings.database_url)
    return MemoryRepository()


def build_context(settings: Settings | None = None) -> AppContext:
    settings = settings or get_settings()
    config_dir = str(settings.config_dir)
    repo = _build_repository(settings)
    router = ModeRouter(settings)
    regions = get_region_config(config_dir)
    store = get_store(config_dir)
    policy_engine = PolicyEngine(settings.config_dir)

    plots = PlotService(repo, settings, router, regions)
    analysis = AnalysisService(repo, router, regions)
    cube = CubeService(repo, router)
    trees = TreeService(repo, store)
    carbon = CarbonService(repo, settings, store, regions, analysis)
    policy = PolicyService(policy_engine)
    market = MarketService(regions)
    simulate = SimulationService(regions, carbon, market, policy, router)
    reports = ReportService(repo, regions, trees, carbon, policy, market, settings.atlas_mode)
    explain = ExplainService(settings.atlas_explain_provider)
    return AppContext(
        settings=settings,
        repo=repo,
        router=router,
        regions=regions,
        store=store,
        policy_engine=policy_engine,
        plots=plots,
        analysis=analysis,
        cube=cube,
        trees=trees,
        carbon=carbon,
        policy=policy,
        market=market,
        simulate=simulate,
        reports=reports,
        explain=explain,
    )
