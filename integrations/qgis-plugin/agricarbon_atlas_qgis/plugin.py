# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""The plugin object QGIS loads: toolbar, menu and the actions of AgriCarbon Atlas.

Flow of a typical session (see the README):

1. select the field polygon, run *Count trees from segmentation layer* (the plugin offers to
   send the polygon first);
2. *Estimate carbon (scenario)*;
3. *Run AI agent team*.

Every network call runs in a background task (``tasks.py``); the pure-Python modules do the
validation, counting and formatting. Nothing here logs coordinates, geometries, attribute values
or server error text.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QFileDialog, QInputDialog, QLineEdit, QMessageBox

from . import config, formatting, geometry, tasks, workflows
from . import qgis_helpers as helpers
from .api_client import AtlasClient
from .diagnostics import exception_summary
from .dialogs import CountTreesDialog, ResultsDialog, SendPlotDialog, SettingsDialog, run_dialog
from .version import DISCLAIMER, PLUGIN_NAME, REPOSITORY_URL, __version__

log = logging.getLogger(__name__)

#: Programme-screening activities offered for a tree inventory: ``(API value, label)``.
ACTIVITIES = (
    ("tree_plantation", "Tree plantation"),
    ("agroforestry", "Agroforestry (trees with crops or livestock)"),
)


def _origin(base_url: str) -> str:
    parts = urlsplit(base_url)
    return f"{parts.scheme}://{parts.netloc}"


def _log_unexpected(context: str, exc: BaseException) -> None:
    """Log an unexpected failure by type and code location (the message may hold field data)."""
    log.error("unexpected failure while %s: %s", context, exception_summary(exc))


class AgriCarbonAtlasPlugin:
    """QGIS plugin entry point (created by ``classFactory``)."""

    MENU = "&AgriCarbon Atlas"
    TOOLBAR_TITLE = "AgriCarbon Atlas"
    TOOLBAR_OBJECT_NAME = "AgriCarbonAtlasToolbar"

    def __init__(self, iface: Any) -> None:
        self.iface = iface
        self.actions: list[Any] = []
        self.toolbar: Any = None
        self._log_handler: Any = None
        self._dialogs: list[Any] = []
        self._busy = False
        self._species: dict[tuple[str, str], list[workflows.SpeciesChoice]] = {}
        self._plugin_dir = os.path.dirname(__file__)

    # ================================================================== QGIS plugin API
    def initGui(self) -> None:  # noqa: N802 - the name is fixed by the QGIS plugin API
        self._log_handler = helpers.install_log_handler()
        self.toolbar = self.iface.addToolBar(self.TOOLBAR_TITLE)
        self.toolbar.setObjectName(self.TOOLBAR_OBJECT_NAME)

        self._add_action(
            "Send selected polygon to AgriCarbon Atlas",
            self.send_selected_polygon,
            icon="icons/send.svg",
            toolbar=True,
            tip="Send the selected field polygon to your AgriCarbon Atlas API and analyse it.",
        )
        self._add_action(
            "Count trees from segmentation layer",
            self.count_trees,
            icon="icons/count.svg",
            toolbar=True,
            tip="Count detected tree crowns inside the selected field and record a tree inventory.",
        )
        self._add_action(
            "Estimate carbon (scenario)",
            self.estimate_carbon,
            icon="icons/carbon.svg",
            toolbar=True,
            tip="Estimated annual carbon removal, value scenarios and programme screening.",
        )
        self._add_action(
            "Run AI agent team",
            self.run_agents,
            icon="icons/agents.svg",
            toolbar=True,
            tip="Let the AI agent team assess the current plot and show its transcript.",
        )
        self._add_separator()
        self._add_action(
            "Set current plot ...",
            self.set_current_plot,
            tip="Link this project to a plot that already exists on the server.",
        )
        self._add_action(
            "Add current plot as layer",
            self.import_current_plot,
            tip="Fetch the plot polygon from the server and add it to the project.",
        )
        self._add_action(
            "Unlink current plot",
            self.clear_current_plot,
            tip="Forget which plot this project is linked to (the plot stays on the server).",
        )
        self._add_action(
            "Export selected field as GeoJSON ...",
            self.export_selected_geojson,
            tip="Save the selected field in the form that is sent to the API (EPSG:4326).",
        )
        self._add_separator()
        self._add_action(
            "Settings ...",
            self.open_settings,
            toolbar=True,
            tip="API address, API key, default country and timeout.",
        )
        self._add_action("About AgriCarbon Atlas", self.show_about, tip="Version and licence.")

    def unload(self) -> None:
        for dialog in list(self._dialogs):
            try:
                dialog.close()
            except RuntimeError:  # already deleted by Qt
                pass
        self._dialogs.clear()
        for action in self.actions:
            self.iface.removePluginMenu(self.MENU, action)
            action.deleteLater()
        self.actions.clear()
        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None
        if self._log_handler is not None:
            helpers.remove_log_handler(self._log_handler)
            self._log_handler = None

    # ================================================================== 1. send the polygon
    def send_selected_polygon(self) -> None:
        selection = self._selected_field()
        if selection is None:
            return
        layer, polygon = selection
        self._send_flow(layer, polygon, reason="", show_results=True, done=None)

    def _send_flow(
        self,
        layer: Any,
        polygon: dict[str, Any],
        reason: str,
        show_results: bool,
        done: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        """Confirm and send ``polygon``: ``POST /plots`` then ``POST /plots/{id}/analyze``."""
        cfg = helpers.load_config()
        if not self._confirm_destination(cfg):
            return
        dialog = SendPlotDialog(
            destination=_origin(cfg.base_url),
            field_summary=self._field_summary(layer, polygon),
            default_country=cfg.default_country,
            reason=reason,
            parent=self.iface.mainWindow(),
        )
        if run_dialog(dialog) != QDialog.Accepted:
            return
        name, country = dialog.values()
        digest = geometry.fingerprint(polygon)
        client = self._client(cfg)

        def work() -> workflows.SendResult:
            return workflows.send_field_polygon(client, polygon, name, country)

        def success(result: workflows.SendResult) -> None:
            plot = dict(result.plot)
            plot["geometry_sha256"] = digest
            helpers.write_current_plot(plot)
            self._success(f"Plot {plot.get('plot_id')} created and linked to this project.")
            if result.analysis_error:
                self._warn(
                    f"The plot was created, but the analysis failed: {result.analysis_error}"
                )
            if show_results:
                self._show_results(
                    "Field sent",
                    formatting.format_plot_page(
                        plot, result.analysis, result.analysis_error, result.notes
                    ),
                )
            if done is not None:
                done(plot)

        self._run("AgriCarbon Atlas: sending the field polygon", work, success)

    # ================================================================== 2. count trees
    def count_trees(self) -> None:
        selection = self._selected_field()
        if selection is None:
            return
        layer, polygon = selection
        plot = helpers.read_current_plot()
        if plot is not None and plot.get("geometry_sha256") == geometry.fingerprint(polygon):
            self._open_count_dialog(layer, plot)
            return
        choice = self._ask_how_to_continue(plot)
        if choice == "use" and plot is not None:
            self._open_count_dialog(layer, plot)
        elif choice == "send":
            self._send_flow(
                layer,
                polygon,
                reason="The tree count is recorded on a plot. Send the selected field first.",
                show_results=False,
                done=lambda new_plot: self._open_count_dialog(layer, new_plot),
            )

    def _ask_how_to_continue(self, plot: dict[str, Any] | None) -> str | None:
        """Ask what to do when the selected field is not the current plot: ``send``/``use``/None."""
        box = QMessageBox(self.iface.mainWindow())
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(PLUGIN_NAME)
        box.setTextFormat(Qt.PlainText)
        use = None
        if plot is None:
            box.setText("This field has not been sent to AgriCarbon Atlas yet.")
            box.setInformativeText(
                "The tree count is stored with a plot on the server. Send the field polygon now?"
            )
            send = box.addButton("Send field polygon", QMessageBox.AcceptRole)
        else:
            label = f"{plot.get('name') or 'Plot'} ({plot.get('plot_id')})"
            box.setText("The selected polygon is not the field of the current plot.")
            box.setInformativeText(
                f"Current plot: {label}. Send the selected polygon as a new plot, or record "
                "the count on the current plot anyway?"
            )
            send = box.addButton("Send as new plot", QMessageBox.AcceptRole)
            use = box.addButton("Use current plot", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Cancel)
        run_dialog(box)
        clicked = box.clickedButton()
        if clicked is send:
            return "send"
        if use is not None and clicked is use:
            return "use"
        return None

    def _open_count_dialog(self, field_layer: Any, plot: dict[str, Any]) -> None:
        cfg = helpers.load_config()
        country = str(plot.get("country") or cfg.default_country)
        key = (cfg.base_url, country)
        cached = self._species.get(key)
        if cached is not None:
            self._show_count_dialog(cfg, field_layer, plot, cached)
            return
        client = self._client(cfg)

        def work() -> list[workflows.SpeciesChoice]:
            return workflows.species_choices(client.list_species(country))

        def success(choices: list[workflows.SpeciesChoice]) -> None:
            if choices:
                self._species[key] = choices
            else:
                self._warn("The server listed no species for this country; type a species id.")
            self._show_count_dialog(cfg, field_layer, plot, choices)

        def failure(exc: BaseException) -> None:
            reason = formatting.describe_error(exc)
            self._warn(f"The species list could not be loaded. {reason} You can type a species id.")
            self._show_count_dialog(cfg, field_layer, plot, [])

        self._run("AgriCarbon Atlas: loading species", work, success, on_error=failure)

    def _show_count_dialog(
        self,
        cfg: config.PluginConfig,
        field_layer: Any,
        plot: dict[str, Any],
        choices: list[workflows.SpeciesChoice],
    ) -> None:
        def count(crown_layer: Any, field: str | None, threshold: float | None) -> Any:
            return helpers.count_crowns_in_field(field_layer, crown_layer, field, threshold)

        dialog = CountTreesDialog(
            field_summary=f"Layer '{field_layer.name()}', 1 selected polygon",
            plot_summary=f"{plot.get('name') or 'Plot'} ({plot.get('plot_id')})",
            species=choices,
            area_hectares=plot.get("area_hectares"),
            excluded_layers=[field_layer],
            count_callback=count,
            suggest_callback=helpers.suggest_confidence_field,
            range_callback=helpers.field_value_range,
            parent=self.iface.mainWindow(),
        )
        if run_dialog(dialog) != QDialog.Accepted:
            return
        values = dialog.values()
        client = self._client(cfg)
        plot_id = str(plot["plot_id"])

        def work() -> dict[str, Any]:
            return workflows.post_tree_inventory(
                client,
                plot_id,
                values["species_id"],
                values["tree_count"],
                values["plantation_year"],
            )

        def success(inventory: dict[str, Any]) -> None:
            self._success(
                f"Tree inventory recorded on plot {plot_id}: {values['tree_count']:,} trees."
            )
            self._show_results(
                "Tree inventory",
                formatting.format_inventory_page(
                    inventory,
                    values["crown_count"],
                    values["confidence_field"],
                    values["layer_name"],
                ),
            )

        self._run("AgriCarbon Atlas: recording the tree inventory", work, success)

    # ================================================================== 3. estimate carbon
    def estimate_carbon(self) -> None:
        plot = self._require_plot()
        if plot is None:
            return
        activity = self._ask_activity()
        if activity is None:
            return
        client = self._client(helpers.load_config())
        plot_id = str(plot["plot_id"])

        def work() -> workflows.CarbonResult:
            return workflows.estimate_carbon(client, plot_id, activity=activity)

        def success(result: workflows.CarbonResult) -> None:
            self._info(
                "Carbon estimate ready. Scenario estimate only, not an issued carbon credit "
                "(certified: false).",
                duration=10,
            )
            self._show_results(
                "Carbon estimate",
                formatting.format_carbon_results(
                    result.estimate,
                    result.market,
                    result.policy,
                    result.market_error,
                    result.policy_error,
                ),
            )

        self._run("AgriCarbon Atlas: estimating carbon", work, success)

    def _ask_activity(self) -> str | None:
        labels = [label for _value, label in ACTIVITIES]
        label, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            f"{PLUGIN_NAME} - Programme screening",
            "Activity to screen carbon and environmental programmes for:",
            labels,
            0,
            False,
        )
        if not ok:
            return None
        return next((value for value, text in ACTIVITIES if text == label), ACTIVITIES[0][0])

    # ================================================================== 4. AI agent team
    def run_agents(self) -> None:
        plot = self._require_plot()
        if plot is None:
            return
        client = self._client(helpers.load_config())
        plot_id = str(plot["plot_id"])

        def work() -> dict[str, Any]:
            return workflows.run_agent_team(client, plot_id, "full-assessment", "en")

        def success(run: dict[str, Any]) -> None:
            self._info("The AI agent team has finished. Review the transcript before using it.")
            self._show_results("AI agent team", formatting.format_agent_run(run))

        self._run("AgriCarbon Atlas: running the AI agent team", work, success, context="agents")

    # ================================================================== plot link and files
    def set_current_plot(self) -> None:
        current = helpers.read_current_plot() or {}
        text, ok = QInputDialog.getText(
            self.iface.mainWindow(),
            f"{PLUGIN_NAME} - Set current plot",
            "Plot id (for example copied from the web app):",
            QLineEdit.Normal,
            str(current.get("plot_id") or ""),
        )
        plot_id = text.strip() if ok else ""
        if not plot_id:
            return
        client = self._client(helpers.load_config())

        def work() -> dict[str, Any]:
            return workflows.fetch_plot(client, plot_id)

        def success(plot: dict[str, Any]) -> None:
            linked = dict(plot)
            linked["geometry_sha256"] = workflows.plot_fingerprint(plot)
            helpers.write_current_plot(linked)
            self._success(f"This project is now linked to plot {linked.get('plot_id')}.")

        self._run("AgriCarbon Atlas: loading the plot", work, success)

    def import_current_plot(self) -> None:
        plot = self._require_plot()
        if plot is None:
            return
        client = self._client(helpers.load_config())
        plot_id = str(plot["plot_id"])

        def work() -> dict[str, Any]:
            return workflows.fetch_plot(client, plot_id)

        def success(fetched: dict[str, Any]) -> None:
            try:
                helpers.add_plot_layer(fetched)
            except geometry.GeometryError:
                self._warn(
                    "The server did not return a usable polygon for this plot (public views "
                    "hide the exact boundary)."
                )
                return
            self._success(f"Plot {plot_id} added to the project as a layer.")

        self._run("AgriCarbon Atlas: loading the plot", work, success)

    def clear_current_plot(self) -> None:
        helpers.write_current_plot(None)
        self._info("This project is no longer linked to a plot. The plot stays on the server.")

    def export_selected_geojson(self) -> None:
        selection = self._selected_field()
        if selection is None:
            return
        _layer, polygon = selection
        path, _selected = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            f"{PLUGIN_NAME} - Export selected field",
            "field.geojson",
            "GeoJSON (*.geojson *.json)",
        )
        if not path:
            return
        if not path.lower().endswith((".geojson", ".json")):
            path += ".geojson"
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(geometry.feature_collection(polygon), handle, indent=2)
                handle.write("\n")
        except OSError as exc:
            self._alert(f"The file could not be written: {exc.strerror}")
            return
        self._success(f"Field written to {os.path.basename(path)} (EPSG:4326, as sent to the API).")

    # ================================================================== settings and about
    def open_settings(self) -> None:
        dialog = SettingsDialog(
            helpers.load_config(), health_check=self._health_check, parent=self.iface.mainWindow()
        )
        if run_dialog(dialog) != QDialog.Accepted:
            return
        cfg = dialog.result_config()
        if cfg is None:
            return
        helpers.save_config(cfg)
        self._species.clear()
        self._info("Settings saved.", duration=4)

    def _health_check(
        self, cfg: config.PluginConfig, on_result: Callable[[bool, str], None]
    ) -> None:
        """Test ``GET /health`` in the background for the Settings dialog."""
        try:
            client = AtlasClient(cfg.base_url, cfg.api_key, min(cfg.timeout_s, 10.0))
        except Exception as exc:
            on_result(False, formatting.describe_error(exc))
            return

        def work() -> Any:
            return client.health()

        tasks.submit(
            "AgriCarbon Atlas: testing the connection",
            work,
            lambda payload: on_result(True, formatting.describe_health(payload)),
            lambda exc: on_result(False, formatting.describe_error(exc)),
        )

    def show_about(self) -> None:
        text = (
            f"<h3>{PLUGIN_NAME} for QGIS {__version__}</h3>"
            "<p>Sends the field polygon you select and a tree count from a segmentation layer "
            "to your AgriCarbon Atlas API, and shows the scenario estimates it returns.</p>"
            f"<p><b>{DISCLAIMER}</b> (certified: false)</p>"
            "<p>This plugin is free software under the GPL-2.0-or-later. The AgriCarbon Atlas "
            "API and web application are separate software under the Apache-2.0 licence.</p>"
            f'<p><a href="{REPOSITORY_URL}">{REPOSITORY_URL}</a></p>'
        )
        QMessageBox.about(self.iface.mainWindow(), f"About {PLUGIN_NAME}", text)

    # ================================================================== shared plumbing
    def _add_action(
        self,
        text: str,
        callback: Callable[[], None],
        icon: str = "icon.svg",
        toolbar: bool = False,
        tip: str = "",
    ) -> Any:
        action = QAction(QIcon(os.path.join(self._plugin_dir, icon)), text, self.iface.mainWindow())
        action.setToolTip(tip or text)
        action.setStatusTip(tip or text)
        action.triggered.connect(lambda _checked=False, cb=callback: self._invoke(cb))
        self.iface.addPluginToMenu(self.MENU, action)
        if toolbar and self.toolbar is not None:
            self.toolbar.addAction(action)
        self.actions.append(action)
        return action

    def _add_separator(self) -> None:
        separator = QAction(self.iface.mainWindow())
        separator.setSeparator(True)
        self.iface.addPluginToMenu(self.MENU, separator)
        self.actions.append(separator)
        if self.toolbar is not None:
            self.toolbar.addSeparator()

    def _invoke(self, callback: Callable[[], None]) -> None:
        """Run an action; an unexpected error becomes a message instead of a traceback popup."""
        try:
            callback()
        except Exception as exc:
            _log_unexpected(f"running {getattr(callback, '__name__', 'an action')}", exc)
            self._alert(formatting.describe_error(exc))

    def _run(
        self,
        description: str,
        work: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None] | None = None,
        context: str | None = None,
    ) -> bool:
        """Run ``work`` in a background task; one request at a time."""
        if self._busy:
            self._warn("Another AgriCarbon Atlas request is still running; please wait for it.")
            return False
        self._busy = True

        def succeeded(result: Any) -> None:
            self._busy = False
            on_success(result)

        def failed(exc: BaseException) -> None:
            self._busy = False
            if on_error is not None:
                on_error(exc)
            else:
                self._alert(formatting.describe_error(exc, context))

        try:
            tasks.submit(description, work, succeeded, failed)
        except Exception as exc:
            self._busy = False
            _log_unexpected("starting a background task", exc)
            self._alert(formatting.describe_error(exc))
            return False
        self._info(description.replace("AgriCarbon Atlas: ", "") + " ...", duration=3)
        return True

    def _client(self, cfg: config.PluginConfig) -> AtlasClient:
        return AtlasClient(cfg.base_url, cfg.api_key, cfg.timeout_s)

    def _selected_field(self) -> tuple[Any, dict[str, Any]] | None:
        """The field layer and the selected polygon in EPSG:4326, or ``None`` after a message."""
        try:
            layer = helpers.find_field_layer(self.iface.activeLayer())
            feature = helpers.selected_field_feature(layer)
            polygon = helpers.feature_to_wgs84_polygon(feature, layer.crs())
        except (helpers.HelperError, geometry.GeometryError) as exc:
            self._warn(str(exc))
            return None
        return layer, polygon

    def _field_summary(self, layer: Any, polygon: dict[str, Any]) -> str:
        vertices = geometry.vertex_count(polygon)
        return f"Layer '{layer.name()}', 1 selected polygon with {vertices} vertices"

    def _require_plot(self) -> dict[str, Any] | None:
        plot = helpers.read_current_plot()
        if plot is None:
            self._warn(
                "This project is not linked to a plot yet. Select your field and run 'Count trees "
                "from segmentation layer' (or 'Send selected polygon'), or use 'Set current plot'."
            )
        return plot

    def _confirm_destination(self, cfg: config.PluginConfig) -> bool:
        """Ask before sending a polygon (and the API key) over plain http to another computer."""
        if not config.is_insecure_remote(cfg.base_url):
            return True
        answer = QMessageBox.question(
            self.iface.mainWindow(),
            PLUGIN_NAME,
            f"The API address {_origin(cfg.base_url)} uses plain http to another computer. Your "
            "field polygon (and the API key, if you set one) would be sent unencrypted.\n\n"
            "Send anyway?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    # -- messages -------------------------------------------------------------------------
    def _push(self, level: Any, text: str, duration: int) -> None:
        self.iface.messageBar().pushMessage(PLUGIN_NAME, text, level, duration)

    def _info(self, text: str, duration: int = 6) -> None:
        self._push(helpers.LEVEL_INFO, text, duration)

    def _success(self, text: str, duration: int = 8) -> None:
        self._push(helpers.LEVEL_SUCCESS, text, duration)

    def _warn(self, text: str, duration: int = 12) -> None:
        self._push(helpers.LEVEL_WARNING, text, duration)

    def _alert(self, text: str) -> None:
        """A message box for failures the user has to read (plain text, never rich text)."""
        box = QMessageBox(self.iface.mainWindow())
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(PLUGIN_NAME)
        box.setTextFormat(Qt.PlainText)
        box.setText(text)
        run_dialog(box)

    def _show_results(self, title: str, html_page: str) -> None:
        dialog = ResultsDialog(title, html_page, self.iface.mainWindow())
        self._dialogs.append(dialog)
        dialog.destroyed.connect(lambda _obj=None, d=dialog: self._forget(d))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _forget(self, dialog: Any) -> None:
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)
