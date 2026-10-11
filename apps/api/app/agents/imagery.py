"""Imagery agent: what the satellites say — vegetation indices, trend and detected tree cover."""

from __future__ import annotations

from typing import Any

from app.agents import wording
from app.agents.tools import detect_tree_cover, vegetation_summary
from carboncreditbuy_agents import Agent, AgentMessage, Evidence, RunContext


class ImageryAgent(Agent):
    id = "imagery"
    title = "Imagery agent"
    role = (
        "Reads the satellite vegetation indices for the plot and, when the detection module "
        "is installed, the detected tree cover."
    )
    says = (
        "How green the plot looks from space (NDVI, moisture NDMI), how that changed over the "
        "years, and the detected tree-cover patches when detection is available."
    )
    tools = (vegetation_summary, detect_tree_cover)
    reads = ("plot_id",)
    writes = ("vegetation", "detection")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        plot_id = ctx.read("plot_id")
        vegetation = ctx.use(vegetation_summary, plot_id=plot_id)
        detection = ctx.use(detect_tree_cover, plot_id=plot_id)

        sentences: list[str] = []
        facts: dict[str, Any] = {}
        evidence: list[Evidence] = []
        if vegetation.ok:
            veg = vegetation.value
            ctx.write("vegetation", veg)
            sentences += wording.vegetation_sentences(veg)
            facts.update(
                {
                    "ndvi": veg["ndvi"],
                    "ndvi_class": veg["ndvi_class"],
                    "ndmi": veg["ndmi"],
                    "trend_pct": veg["trend_pct"],
                    "observation_date": veg["date"],
                }
            )
            evidence += wording.evidence_from_sources(veg["sources"])
        if detection.ok:
            det = detection.value
            ctx.write("detection", det)
            sentences.append(wording.detection_sentence(det))
            facts.update(
                {
                    "detected_patches": det["patches"],
                    "detected_cover_fraction": det["covered_fraction"],
                    "detected_area_hectares": det["area_hectares"],
                }
            )
            evidence += wording.evidence_from_sources(det["sources"]) or [
                Evidence(f"Tree-cover detection {det.get('detection_id')}", "detection")
            ]
        elif detection.status == "skipped":
            sentences.append(f"{str(detection.reason).rstrip('.')}.")

        messages: list[AgentMessage] = []
        if evidence:
            messages.append(ctx.say("finding", " ".join(sentences), facts=facts, evidence=evidence))
        if not vegetation.ok:
            note = "" if evidence else " " + " ".join(sentences)
            messages.append(
                ctx.warn(
                    f"No satellite vegetation reading is available ({vegetation.reason}).{note}"
                )
            )
        if detection.status == "error":
            messages.append(ctx.warn(f"Tree-cover detection failed ({detection.reason})."))
        return messages
