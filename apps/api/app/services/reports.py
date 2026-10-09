"""Report assembly: gathers plot, inventory, analysis, estimate, policy and market data."""

from __future__ import annotations

from typing import Any

from app.core.errors import ProblemError
from app.repositories.base import Repository
from app.services.carbon import CarbonService
from app.services.common import API_VERSION, now_iso
from app.services.market import MarketService
from app.services.policy import PolicyService
from app.services.regions import RegionConfig
from app.services.trees import TreeService
from report_engine import MEDIA_TYPES, PdfNotAvailableError, ReportIdSequencer, ReportRenderer

DISCLAIMER = (
    "This assessment is a modelled scenario estimate. It is not a certification, not an issued "
    "carbon or green credit, and not investment advice. Credit issuance depends on an applicable "
    "methodology, baseline and additionality, monitoring, verification, permanence and market "
    "conditions. Validation and third-party verification are required where applicable."
)


class ReportService:
    def __init__(
        self,
        repo: Repository,
        regions: RegionConfig,
        trees: TreeService,
        carbon: CarbonService,
        policy: PolicyService,
        market: MarketService,
        mode: str,
    ) -> None:
        self.repo = repo
        self.regions = regions
        self.trees = trees
        self.carbon = carbon
        self.policy = policy
        self.market = market
        self.mode = mode
        self.renderer = ReportRenderer()
        self.sequencer = ReportIdSequencer()
        for existing in repo.report_ids():
            self.sequencer.observe(existing)

    def context(
        self, plot: dict[str, Any], estimate_id: str | None, language: str
    ) -> dict[str, Any]:
        estimate = self.carbon.require(plot["plot_id"], estimate_id)
        inventory = self.trees.require(plot["plot_id"], estimate.get("inventory_id"))
        analysis = self.repo.get_analysis(plot["plot_id"]) or {}
        region_id = self.regions.resolve(plot.get("country")) or "IN"
        policy = self.policy.screen(
            plot["country"], "tree_plantation", area_ha=plot["area_hectares"]
        )
        market = self.market.scenarios_for(region_id, estimate["estimate"])
        sources = list(estimate.get("provenance", {}).get("sources", []))
        return {
            "report_id": None,
            "generated_at": now_iso(),
            "language": language,
            "mode": self.mode,
            "api_version": API_VERSION,
            "plot": {
                "plot_id": plot["plot_id"],
                "name": plot.get("name"),
                "country": plot.get("country"),
                "region": plot.get("region"),
                "area_hectares": plot["area_hectares"],
                "area_acres": plot["area_acres"],
                "perimeter_m": plot.get("perimeter_m"),
                "public_centroid": plot.get("public_centroid"),
                "source": plot.get("source"),
            },
            "inventory": inventory,
            "analysis": {
                "landcover": analysis.get("landcover"),
                "vegetation": analysis.get("vegetation"),
                "climate": analysis.get("climate"),
                "soil": analysis.get("soil"),
                "data_quality": analysis.get("data_quality", {"warnings": []}),
            },
            "estimate": estimate,
            "policy": policy,
            "market": market,
            "sources": sources,
            "disclaimer": DISCLAIMER,
        }

    def create(
        self, plot: dict[str, Any], fmt: str, language: str, estimate_id: str | None
    ) -> dict[str, Any]:
        context = self.context(plot, estimate_id, language)
        report_id = self.sequencer.next_id()
        context["report_id"] = report_id
        try:
            content = self.renderer.render(context, fmt)
        except PdfNotAvailableError as exc:
            raise ProblemError(
                501,
                "PDF rendering requires the optional WeasyPrint dependency.",
                type_slug="pdf-unavailable",
            ) from exc
        meta = {
            "report_id": report_id,
            "plot_id": plot["plot_id"],
            "estimate_id": context["estimate"]["estimate_id"],
            "format": fmt,
            "media_type": MEDIA_TYPES[fmt],
            "language": language,
            "generated_at": context["generated_at"],
        }
        self.repo.save_report(report_id, meta, content)
        self.repo.audit("report.created", plot["plot_id"], {"report_id": report_id, "format": fmt})
        return meta

    def fetch(self, report_id: str) -> tuple[dict[str, Any], bytes]:
        item = self.repo.get_report(report_id)
        if item is None:
            raise ProblemError(
                404, f"Report {report_id} was not found.", type_slug="report-not-found"
            )
        return item
