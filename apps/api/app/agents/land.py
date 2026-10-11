"""Land agent: the plot itself — size, place, boundary, land cover and climate zone."""

from __future__ import annotations

from typing import Any

from app.agents import wording
from app.agents.tools import climate_zone, land_cover_shares, measure_plot
from carboncreditbuy_agents import Agent, AgentMessage, Evidence, RunContext


class LandAgent(Agent):
    id = "land"
    title = "Land agent"
    role = "Checks the plot itself: size, location, boundary, land cover and climate zone."
    says = (
        "How big the plot is and where it lies (state, country), whether the boundary is "
        "valid, the land-cover shares and the climate zone."
    )
    tools = (measure_plot, land_cover_shares, climate_zone)
    reads = ("plot_id",)
    writes = ("plot_summary", "landcover", "climate")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        plot_id = ctx.read("plot_id")
        measured = ctx.use(measure_plot, plot_id=plot_id)
        if not measured.ok:
            return [ctx.warn(f"I could not measure the plot ({measured.reason}).")]
        plot = measured.value
        ctx.write("plot_summary", plot)

        sentences = [wording.plot_sentence(plot), wording.boundary_sentence(plot)]
        facts: dict[str, Any] = {
            "area_hectares": round(float(plot["area_hectares"]), 2),
            "area_acres": round(float(plot["area_acres"]), 2),
            "state": plot.get("state"),
            "country": plot.get("country"),
            "boundary_valid": plot["boundary_valid"],
            "boundary_quality": plot.get("boundary_quality"),
        }
        evidence = [Evidence("Geodesic area of your plot boundary (geo-engine)", "geo-engine")]
        gaps: list[str] = []

        cover = ctx.use(land_cover_shares, plot_id=plot_id)
        if cover.ok:
            ctx.write("landcover", cover.value)
            sentences.append(wording.landcover_sentence(cover.value))
            facts["cropland_share"] = cover.value["cropland_share"]
            facts["tree_cover_share"] = cover.value["tree_cover_share"]
            evidence += wording.evidence_from_sources(cover.value["sources"])
        else:
            gaps.append(f"land cover is not available right now ({cover.reason})")

        climate = ctx.use(climate_zone, plot_id=plot_id)
        if climate.ok:
            ctx.write("climate", climate.value)
            sentences.append(wording.climate_sentence(climate.value))
            facts["climate_zone"] = climate.value["zone"]
            evidence += wording.evidence_from_sources(climate.value["sources"])
        else:
            gaps.append(f"the climate zone is not available right now ({climate.reason})")

        messages = [ctx.say("finding", " ".join(sentences), facts=facts, evidence=evidence)]
        if not plot["boundary_valid"]:
            messages.append(
                ctx.warn(
                    "The plot boundary failed validation "
                    f"({plot.get('boundary_problem')}); results for this plot are unreliable "
                    "until it is redrawn.",
                    facts={"boundary_problem": plot.get("boundary_problem")},
                )
            )
        if gaps:
            messages.append(ctx.warn(f"I could not finish the land check: {'; '.join(gaps)}."))
        return messages
