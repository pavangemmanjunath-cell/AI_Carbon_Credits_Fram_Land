"""Tree agent: the tree inventory, and trees counted in imported files."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.agents import wording
from app.agents.tools import imported_trees, tree_inventory
from atlas_agents import Agent, AgentMessage, Evidence, RunContext


def _import_sentence(item: Mapping[str, Any]) -> str:
    fmt = str(item.get("format") or "file").upper()
    if item.get("count_in_plot") is not None:
        text = (
            f"An imported {fmt} file ({item.get('import_id')}) counted "
            f"{int(item['count_in_plot']):,} trees inside this plot"
        )
    else:
        text = (
            f"An imported {fmt} file ({item.get('import_id')}) counted "
            f"{int(item.get('count') or 0):,} trees (not matched to this plot)"
        )
    if item.get("mean_height_m") is not None:
        text += f", mean height {wording.num(item['mean_height_m'])} m"
    return text + "."


class TreesAgent(Agent):
    id = "trees"
    title = "Tree agent"
    role = "Reads the tree inventory and any tree counts detected in imported files."
    says = (
        "How many trees of which species, when they were planted, their age and survival, "
        "which measurements are still missing — and trees counted in imported files."
    )
    tools = (tree_inventory, imported_trees)
    reads = ("plot_id",)
    writes = ("inventory", "imported_trees")

    def run(self, ctx: RunContext) -> list[AgentMessage]:
        plot_id = ctx.read("plot_id")
        inventory = ctx.use(tree_inventory, plot_id=plot_id)
        imports = ctx.use(imported_trees, plot_id=plot_id)

        import_notes: list[str] = []
        import_evidence: list[Evidence] = []
        if imports.ok and imports.value["with_trees"]:
            ctx.write("imported_trees", imports.value)
            for item in imports.value["with_trees"][:3]:
                import_notes.append(_import_sentence(item))
                import_evidence.append(Evidence(f"Imported file {item.get('import_id')}", "import"))

        messages: list[AgentMessage] = []
        if not inventory.ok:
            messages.append(ctx.warn(f"I could not read the tree inventory ({inventory.reason})."))
        elif not inventory.value["found"]:
            messages.append(
                ctx.warn(
                    "There is no tree inventory for this plot yet. Add the species, the number "
                    "of trees and the planting year so the Carbon agent can estimate removal."
                    + (" " + " ".join(import_notes) if import_notes else "")
                )
            )
        else:
            inv = inventory.value
            ctx.write("inventory", inv)
            facts = {
                "inventory_id": inv["inventory_id"],
                "species": inv["species"],
                "tree_count": inv["tree_count"],
                "density_per_ha": inv["density_per_ha"],
                "plantation_year": inv["plantation_year"],
                "age_years": inv["age_years"],
                "survival_rate": inv["survival_rate"],
                "measurement_source": inv["measurement_source"],
                "missing_fields": inv["missing_fields"],
            }
            evidence = [
                Evidence(
                    f"Tree inventory {inv['inventory_id']} ({inv['measurement_source']})",
                    "inventory",
                ),
                *import_evidence,
            ]
            text = " ".join([wording.inventory_sentence(inv), *import_notes])
            messages.append(
                ctx.say(
                    "finding", text, facts=facts, evidence=evidence, confidence=inv["confidence"]
                )
            )
            if "carbon" in ctx.later_agents:
                survival = (
                    f" (survival {wording.pct(inv['survival_rate'])})"
                    if inv.get("survival_rate") is not None
                    else ""
                )
                messages.append(
                    ctx.handoff(
                        "carbon",
                        f"Carbon agent: please estimate removal for {int(inv['tree_count']):,} "
                        f"{str(inv['species']).lower()} trees planted in "
                        f"{inv['plantation_year']}{survival}.",
                        facts={"inventory_id": inv["inventory_id"]},
                    )
                )
        if imports.status == "error":
            messages.append(ctx.warn(f"Imported files could not be read ({imports.reason})."))
        return messages
