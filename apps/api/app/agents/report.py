"""Report agent: writes the assessment report with the report engine."""

from __future__ import annotations

from app.agents import wording
from app.agents.tools import create_report
from carboncreditbuy_agents import Agent, AgentMessage, Evidence, RunContext


class ReportAgent(Agent):
    id = "report"
    title = "Report agent"
    role = "Writes the HTML assessment report for the current estimate with the report engine."
    says = "That a report was written, its id and where to open it."
    tools = (create_report,)
    reads = ("plot_id", "estimate", "locale")
    writes = ("report",)

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        estimate = ctx.read("estimate")
        result = ctx.use(
            create_report,
            plot_id=ctx.read("plot_id"),
            estimate_id=estimate["estimate_id"],
            language=ctx.read("locale") or "en",
        )
        if not result.ok:
            return [ctx.warn(f"I could not write the report ({result.reason}).")]
        report = result.value
        ctx.write("report", report)
        return [
            ctx.say(
                "finding",
                wording.report_sentence(report),
                facts={"report_id": report["report_id"], "format": report["format"]},
                evidence=[
                    Evidence(
                        f"Assessment report {report['report_id']}", "report-engine", report["url"]
                    )
                ],
            )
        ]
