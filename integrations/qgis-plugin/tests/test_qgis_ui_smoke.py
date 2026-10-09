# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Smoke tests of the dialogs and the plugin object with real PyQt5 widgets (offscreen).

These need PyQt5 (``pip install PyQt5``) and are skipped when it is missing, so they do not
run in the repository's CI. QGIS itself is replaced by the fakes in ``qgis_fakes.py`` and the API
by a local HTTP server, so the whole plugin flow runs: select a field, count crowns, send,
estimate, run the agent team. What these tests cannot prove is the behaviour of the real QGIS:
see "Limitations" in the README.
"""

from __future__ import annotations

import importlib
import json
import logging
import random
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

QtWidgets = pytest.importorskip("PyQt5.QtWidgets", reason="PyQt5 is not installed")

from qgis_fakes import LayerBuilder, make_iface, wgs84_to_mercator  # noqa: E402
from qgis_plugin_fake_server import (  # noqa: E402
    Answer,
    FakeAtlasServer,
    RecordedRequest,
    json_answer,
    problem_answer,
)

from agricarbon_atlas_qgis import config, geometry  # noqa: E402
from agricarbon_atlas_qgis.crowns import CrownCount  # noqa: E402
from agricarbon_atlas_qgis.version import DISCLAIMER  # noqa: E402

QDialog = QtWidgets.QDialog
QMessageBox = QtWidgets.QMessageBox
QApplication = QtWidgets.QApplication

PLOT_ID = "PLT-UI1"
API_KEY = "k-test-123456"
OWNER_SECRET = "OWNER-SECRET-NAME"
FIELD_LONLAT = [(77.1234, 13.6543), (77.1264, 13.6543), (77.1264, 13.6573), (77.1234, 13.6573)]
COORDINATE_DIGITS = ("77.12", "13.65")  # what must never show up in logs or messages

SPECIES = [
    {
        "id": "mango",
        "common_name": "Mango",
        "scientific_name": "Mangifera indica",
        "max_density_per_ha": 600,
    },
    {"id": "teak", "common_name": "Teak", "scientific_name": "Tectona grandis"},
]
ESTIMATE = {
    "estimate_id": "EST-UI1",
    "plot_id": PLOT_ID,
    "estimate": {"low": 4.02, "central": 5.74, "high": 7.46, "unit": "tCO2e/yr"},
    "confidence": "medium",
    "certified": False,
    "disclaimer": "Scenario estimate; not an issued carbon credit.",
    "readiness": {"score": 55, "grade": "medium", "missing_evidence": [{"label": "DBH records"}]},
}
MARKET = {
    "currency": "INR",
    "currency_symbol": "₹",
    "scenarios": [
        {
            "id": "low",
            "label": "Low",
            "price_per_tco2e": 480,
            "value_per_year": {"low": 1930, "central": 2755, "high": 3581},
        }
    ],
    "other_income": [{"id": "fruit", "label": "Fruit sales", "value": None, "unit": "INR/yr"}],
}
POLICY = {
    "programmes": [
        {
            "id": "ccts",
            "name": "Carbon Credit Trading Scheme",
            "kind": "compliance_market",
            "status": "requires_assessment",
        }
    ]
}
AGENT_RUN = {
    "run_id": "RUN-UI1",
    "status": "completed",
    "messages": [
        {"agent_title": "Land analyst", "kind": "finding", "text": "Tree cover is 12 percent."}
    ],
    "certified": False,
    "disclaimer": "Scenario estimate only. This is not an issued carbon credit.",
}


# =========================================================================== the fake API
def install_routes(server: FakeAtlasServer) -> None:
    def create_plot(request: RecordedRequest) -> Answer:
        body = request.json
        return json_answer(
            201,
            {
                "plot_id": PLOT_ID,
                "name": body["name"],
                "country": body.get("country") or "IN",
                "area_hectares": 10.7,
                "area_acres": 26.4,
                "source": body["source"],
                "privacy": "private",
                "geometry": body["geometry"],
            },
        )

    def create_inventory(request: RecordedRequest) -> Answer:
        body = request.json
        return json_answer(
            201,
            {
                "inventory_id": "INV-UI1",
                "plot_id": PLOT_ID,
                "species": {"id": body["species_id"], "common_name": body["species_id"].title()},
                "tree_count": body["tree_count"],
                "plantation_year": body["plantation_year"],
                "measurement_source": body["measurement_source"],
            },
        )

    server.route("POST", "/plots", create_plot)
    server.route("POST", f"/plots/{PLOT_ID}/analyze", payload={"mode": "demo"})
    server.route("GET", "/species", payload=SPECIES)
    server.route("POST", f"/plots/{PLOT_ID}/trees", create_inventory)
    server.route("POST", f"/plots/{PLOT_ID}/carbon-estimate", status=201, payload=ESTIMATE)
    server.route("GET", f"/plots/{PLOT_ID}/market-scenario", payload=MARKET)
    server.route("GET", f"/plots/{PLOT_ID}/policy-eligibility", payload=POLICY)
    server.route("GET", "/health", payload={"status": "ok", "version": "0.1.0", "mode": "demo"})


# =========================================================================== QGIS scene
class Scene:
    """A selected field (EPSG:3857) with an owner attribute, and a layer of crowns around it."""

    def __init__(self, seed: int = 11) -> None:
        build = LayerBuilder()
        ring = [wgs84_to_mercator(lon, lat) for lon, lat in FIELD_LONLAT]
        ring.append(ring[0])
        self.x0, self.y0 = ring[0]
        self.x1, self.y1 = ring[2]
        self.field_layer = build.layer("Fields", crs="EPSG:3857", fields=("owner:string",))
        feature = build.polygon(self.field_layer, ring, attributes=[OWNER_SECRET])
        build.select(self.field_layer, feature)

        self.crown_layer = build.layer(
            "Tree crowns", crs="EPSG:3857", fields=("score:double", "label:string")
        )
        rng = random.Random(seed)
        self.crowns: list[tuple[float, float, float]] = []
        for _ in range(150):
            x = rng.uniform(self.x0 - 60, self.x1 + 60)
            y = rng.uniform(self.y0 - 60, self.y1 + 60)
            score = rng.random()
            self.crowns.append((x, y, score))
            half = 3.0
            crown = [(x - half, y - half), (x + half, y - half), (x + half, y + half)]
            crown += [(x - half, y + half), (x - half, y - half)]
            build.polygon(self.crown_layer, crown, attributes=[score, "crown"])

        closed = [[lon, lat] for lon, lat in [*FIELD_LONLAT, FIELD_LONLAT[0]]]
        self.polygon = geometry.normalize_polygon({"type": "Polygon", "coordinates": [closed]})

    def inside(self, threshold: float | None = None) -> int:
        return sum(
            1
            for x, y, score in self.crowns
            if self.x0 <= x <= self.x1
            and self.y0 <= y <= self.y1
            and (threshold is None or score >= threshold)
        )


# =========================================================================== the test harness
class Env:
    """A plugin instance on a fake QGIS, a fake API, and scripted answers for its dialogs."""

    def __init__(
        self,
        core: ModuleType,
        server: FakeAtlasServer,
        app: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.core, self.server, self.app = core, server, app
        self.helpers = importlib.import_module("agricarbon_atlas_qgis.qgis_helpers")
        self.dialogs = importlib.import_module("agricarbon_atlas_qgis.dialogs")
        self.plugin_mod = importlib.import_module("agricarbon_atlas_qgis.plugin")
        self.iface = make_iface()
        self.helpers.save_config(config.PluginConfig(server.base_url, API_KEY, "IN", 10.0))
        self.plugin = self.plugin_mod.AgriCarbonAtlasPlugin(self.iface)
        self.plugin.initGui()

        #: class name of a dialog -> function that fills it in and returns its result code
        self.scripts: dict[str, Callable[[Any], int]] = {"QMessageBox": lambda box: 0}
        self.seen: list[str] = []  # class names of the dialogs that were run, in order
        self.boxes: list[str] = []  # text of the message boxes that were run
        self.unexpected: list[str] = []
        self.script_errors: list[str] = []
        monkeypatch.setattr(self.plugin_mod, "run_dialog", self.run_dialog)

    def run_dialog(self, dialog: Any) -> int:
        kind = type(dialog).__name__
        self.seen.append(kind)
        if kind == "QMessageBox":
            self.boxes.append(f"{dialog.text()} | {dialog.informativeText()}")
        script = self.scripts.get(kind)
        if script is None:
            self.unexpected.append(kind)
            return int(QDialog.Rejected)
        try:
            return script(dialog)
        except Exception as exc:
            self.script_errors.append(f"{kind}: {exc!r}")
            return int(QDialog.Rejected)

    def pump(self, limit: int = 30) -> int:
        """Run the queued background tasks (and the callbacks they trigger) until none is left."""
        done = 0
        while True:
            ran = self.core.QgsApplication.taskManager().run_all()
            self.app.processEvents()
            if not ran:
                return done
            done += ran
            assert done <= limit, "tasks keep queueing new tasks"

    def bar(self) -> list[str]:
        return [text for _title, text, _level, _duration in self.iface.bar.messages]

    def log(self) -> list[str]:
        return [message for message, _tag, _level in self.core.QgsMessageLog.messages]

    def everything_shown(self) -> str:
        """All text the user or the QGIS log panel got, for privacy checks."""
        dialogs = [d.browser.toPlainText() for d in self.plugin._dialogs]
        return "\n".join([*self.bar(), *self.log(), *self.boxes, *dialogs])

    def find_action(self, text: str) -> Any:
        return next(a for a in self.plugin.actions if a.text() == text)

    def link_plot(self, scene: Scene | None = None, plot_id: str = PLOT_ID) -> None:
        plot: dict[str, Any] = {"plot_id": plot_id, "name": "Linked", "country": "IN"}
        if scene is not None:
            plot["geometry_sha256"] = geometry.fingerprint(scene.polygon)
        self.helpers.write_current_plot(plot)


@pytest.fixture
def env(
    fake_qgis_qt: ModuleType,
    atlas_server: FakeAtlasServer,
    offscreen_qt: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Env]:
    install_routes(atlas_server)
    harness = Env(fake_qgis_qt, atlas_server, offscreen_qt, monkeypatch)
    yield harness
    harness.plugin.unload()
    harness.app.processEvents()
    assert harness.unexpected == [], "a dialog opened that the test did not script"
    assert harness.script_errors == []


@pytest.fixture
def scene(env: Env) -> Scene:
    built = Scene()
    env.iface.active_layer = built.field_layer
    return built


# --------------------------------------------------------------------------- scripted dialogs
def accept_send_dialog(name: str = "North field", country: str | None = "IN") -> Any:
    def script(dialog: Any) -> int:
        dialog.name_edit.setText(name)
        # index 0 is "Let the server detect it"
        index = 0 if country is None else dialog.country_combo.findData(country)
        dialog.country_combo.setCurrentIndex(index)
        return int(QDialog.Accepted)

    return script


def click_button(text: str) -> Any:
    def script(box: Any) -> int:
        buttons = [b.text().replace("&", "") for b in box.buttons()]
        assert text in buttons, buttons
        box.buttons()[buttons.index(text)].click()
        return 0

    return script


def click_cancel(box: Any) -> int:
    box.button(QMessageBox.Cancel).click()
    return 0


def fill_count_dialog(
    crowns: Any, threshold: float | None = 0.5, species: str = "mango", year: int = 2019
) -> Any:
    def script(dialog: Any) -> int:
        dialog.crown_combo.setLayer(crowns)
        assert dialog.confidence_field() == "score"
        if threshold is not None:
            dialog.threshold_spin.setValue(threshold)
        dialog.preview_button.click()
        dialog.species_combo.setCurrentIndex(dialog.species_combo.findData(species))
        dialog.year_spin.setValue(year)
        assert dialog.send_button.isEnabled(), dialog.hint_label.text()
        return int(QDialog.Accepted)

    return script


# =========================================================================== plugin life cycle
def test_menu_toolbar_and_log_handler_are_added_and_removed(env: Env) -> None:
    logger = logging.getLogger("agricarbon_atlas_qgis")
    menu = env.iface.menu_actions["&AgriCarbon Atlas"]
    assert [a.text() for a in menu if not a.isSeparator()] == [
        "Send selected polygon to AgriCarbon Atlas",
        "Count trees from segmentation layer",
        "Estimate carbon (scenario)",
        "Run AI agent team",
        "Set current plot ...",
        "Add current plot as layer",
        "Unlink current plot",
        "Export selected field as GeoJSON ...",
        "Settings ...",
        "About AgriCarbon Atlas",
    ]
    assert env.plugin.toolbar.objectName() == "AgriCarbonAtlasToolbar"
    assert [a.text() for a in env.plugin.toolbar.actions() if not a.isSeparator()] == [
        "Send selected polygon to AgriCarbon Atlas",
        "Count trees from segmentation layer",
        "Estimate carbon (scenario)",
        "Run AI agent team",
        "Settings ...",
    ]
    assert any(isinstance(h, env.helpers.QgsLogHandler) for h in logger.handlers)

    env.plugin.unload()
    assert env.iface.menu_actions == {}
    assert env.plugin.actions == [] and env.plugin.toolbar is None
    assert not any(isinstance(h, env.helpers.QgsLogHandler) for h in logger.handlers)
    env.plugin.unload()  # unloading twice is harmless

    env.plugin.initGui()  # and the plugin can be loaded again (QGIS "reload plugin")
    assert len(env.iface.menu_actions["&AgriCarbon Atlas"]) == 12  # 10 actions + 2 separators


def test_class_factory_returns_the_plugin(env: Env) -> None:
    import agricarbon_atlas_qgis

    created = agricarbon_atlas_qgis.classFactory(env.iface)
    assert isinstance(created, env.plugin_mod.AgriCarbonAtlasPlugin)
    assert created.iface is env.iface


def test_actions_are_wired_to_their_methods(env: Env) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID})
    env.find_action("Unlink current plot").trigger()
    assert env.helpers.read_current_plot() is None
    assert any("no longer linked" in text for text in env.bar())


def test_unexpected_errors_become_a_plain_message_without_details(
    env: Env, scene: Scene, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def explode(_layer: Any) -> Any:
        raise RuntimeError("secret detail 77.1234,13.6543")

    monkeypatch.setattr(env.helpers, "find_field_layer", explode)
    with caplog.at_level(logging.INFO, logger="agricarbon_atlas_qgis"):
        env.find_action("Send selected polygon to AgriCarbon Atlas").trigger()
    assert env.boxes and "Unexpected error (RuntimeError)" in env.boxes[0]
    shown = env.everything_shown() + caplog.text
    assert "secret" not in shown and "77.1234" not in shown
    assert "RuntimeError" in caplog.text


# =========================================================================== 1 + 2: field and trees
def test_count_trees_sends_the_field_then_records_the_inventory(env: Env, scene: Scene) -> None:
    env.scripts["QMessageBox"] = click_button("Send field polygon")
    env.scripts["SendPlotDialog"] = accept_send_dialog("North field", "IN")
    env.scripts["CountTreesDialog"] = fill_count_dialog(scene.crown_layer, 0.5, "mango", 2019)

    env.plugin.count_trees()
    assert env.server.requests == []  # the network calls only start in the background task
    assert len(env.core.QgsApplication.taskManager().queue) == 1
    env.pump()

    assert env.seen == ["QMessageBox", "SendPlotDialog", "CountTreesDialog"]
    assert [(r.method, r.path) for r in env.server.requests] == [
        ("POST", "/api/v1/plots"),
        ("POST", f"/api/v1/plots/{PLOT_ID}/analyze"),
        ("GET", "/api/v1/species"),
        ("POST", f"/api/v1/plots/{PLOT_ID}/trees"),
    ]
    create, _analyze, species, trees = env.server.requests
    assert set(create.json) == {"name", "country", "source", "geometry"}
    assert (create.json["name"], create.json["country"]) == ("North field", "IN")
    assert create.json["source"] == "qgis-plugin"
    assert create.json["geometry"] == scene.polygon  # reprojected from EPSG:3857 to EPSG:4326
    assert species.query == {"country": ["IN"]}
    assert trees.json == {
        "species_id": "mango",
        "tree_count": scene.inside(0.5),
        "plantation_year": 2019,
        "measurement_source": "model-estimated",
    }
    assert 0 < trees.json["tree_count"] < scene.inside()  # the confidence filter had an effect
    assert {r.headers["x-api-key"] for r in env.server.requests} == {API_KEY}

    linked = env.helpers.read_current_plot()
    assert linked is not None and linked["plot_id"] == PLOT_ID
    assert linked["geometry_sha256"] == geometry.fingerprint(scene.polygon)

    results = env.plugin._dialogs[-1]
    page = results.browser.toPlainText()
    assert "Tree inventory" in results.windowTitle()
    assert DISCLAIMER in page and "certified: false" in page
    assert "model-estimated" in page and "Tree crowns" in page
    assert any("Tree inventory recorded" in text for text in env.bar())


def test_nothing_but_the_polygon_leaves_the_machine_and_nothing_private_is_logged(
    env: Env, scene: Scene
) -> None:
    env.scripts["QMessageBox"] = click_button("Send field polygon")
    env.scripts["SendPlotDialog"] = accept_send_dialog()
    env.scripts["CountTreesDialog"] = fill_count_dialog(scene.crown_layer)
    env.plugin.count_trees()
    env.pump()

    sent = "\n".join(r.body.decode("utf-8") for r in env.server.requests)
    assert OWNER_SECRET not in sent and "crown" not in sent
    for request in env.server.requests[1:]:  # only the first request carries the polygon
        body = request.body.decode("utf-8")
        assert not any(digits in body for digits in COORDINATE_DIGITS), request.path

    shown = env.everything_shown()
    assert API_KEY not in shown and OWNER_SECRET not in shown
    for digits in COORDINATE_DIGITS:
        assert digits not in shown
    project_text, _found = env.core.QgsProject.instance().readEntry(
        "AgriCarbonAtlas", "current_plot", ""
    )
    assert not any(digits in project_text for digits in COORDINATE_DIGITS)
    assert "coordinates" not in project_text and API_KEY not in project_text


def test_the_second_count_reuses_the_plot_and_the_species_list(env: Env, scene: Scene) -> None:
    env.scripts["QMessageBox"] = click_button("Send field polygon")
    env.scripts["SendPlotDialog"] = accept_send_dialog()
    env.scripts["CountTreesDialog"] = fill_count_dialog(scene.crown_layer)
    env.plugin.count_trees()
    env.pump()

    env.seen.clear()
    env.server.requests.clear()
    env.plugin.count_trees()
    env.pump()
    assert env.seen == ["CountTreesDialog"]  # no question, no second plot
    assert [(r.method, r.path) for r in env.server.requests] == [
        ("POST", f"/api/v1/plots/{PLOT_ID}/trees")
    ]


def test_a_different_polygon_offers_the_current_plot(env: Env, scene: Scene) -> None:
    env.server.route("GET", "/species", payload=SPECIES)
    env.server.route("POST", "/plots/PLT-OLD/trees", status=201, payload={"inventory_id": "I"})
    env.helpers.write_current_plot(
        {"plot_id": "PLT-OLD", "name": "Old", "geometry_sha256": "0" * 64}
    )
    env.scripts["QMessageBox"] = click_button("Use current plot")
    env.scripts["CountTreesDialog"] = fill_count_dialog(scene.crown_layer)
    env.plugin.count_trees()
    env.pump()
    assert "not the field of the current plot" in env.boxes[0] and "Old (PLT-OLD)" in env.boxes[0]
    assert [r.path for r in env.server.requests] == [
        "/api/v1/species",
        "/api/v1/plots/PLT-OLD/trees",
    ]


def test_cancelling_the_question_sends_nothing(env: Env, scene: Scene) -> None:
    env.scripts["QMessageBox"] = click_cancel
    env.plugin.count_trees()
    env.pump()
    assert env.seen == ["QMessageBox"] and env.server.requests == []
    assert env.helpers.read_current_plot() is None


def test_cancelling_the_send_dialog_sends_nothing(env: Env, scene: Scene) -> None:
    env.scripts["QMessageBox"] = click_button("Send field polygon")
    env.scripts["SendPlotDialog"] = lambda dialog: int(QDialog.Rejected)
    env.plugin.count_trees()
    env.pump()
    assert env.seen == ["QMessageBox", "SendPlotDialog"] and env.server.requests == []


def test_send_selected_polygon_shows_the_new_plot(env: Env, scene: Scene) -> None:
    env.scripts["SendPlotDialog"] = accept_send_dialog("Smoke field", None)
    env.plugin.send_selected_polygon()
    assert env.server.requests == []
    env.pump()
    create, analyze = env.server.requests
    assert "country" not in create.json  # the server detects the country
    assert analyze.path.endswith(f"/plots/{PLOT_ID}/analyze")
    page = env.plugin._dialogs[-1].browser.toPlainText()
    assert PLOT_ID in page and DISCLAIMER in page and "certified: false" in page
    for digits in COORDINATE_DIGITS:
        assert digits not in page


def test_a_server_without_the_plugin_source_value_gets_a_second_try(env: Env, scene: Scene) -> None:
    def only_known_sources(request: RecordedRequest) -> Answer:
        if request.json["source"] == "qgis-plugin":
            return problem_answer(
                422,
                "Unprocessable Entity",
                slug="validation-error",
                errors=[{"field": "source", "message": "Input should be 'api'"}],
            )
        return json_answer(201, {"plot_id": PLOT_ID, "name": "n", "source": "api"})

    env.server.route("POST", "/plots", only_known_sources)
    env.scripts["SendPlotDialog"] = accept_send_dialog()
    env.plugin.send_selected_polygon()
    env.pump()
    sources = [r.json["source"] for r in env.server.requests_to("POST", "/plots")]
    assert sources == ["qgis-plugin", "api"]
    assert "qgis-plugin" in env.plugin._dialogs[-1].browser.toPlainText()


def test_a_server_error_becomes_a_message_and_the_next_action_still_works(
    env: Env, scene: Scene
) -> None:
    env.server.route(
        "POST",
        "/plots",
        problem_answer(401, "Unauthorized", "secret-detail-from-the-server", "api-key-required"),
    )
    env.scripts["SendPlotDialog"] = accept_send_dialog()
    env.plugin.send_selected_polygon()
    env.pump()
    assert len(env.boxes) == 1 and "requires an API key" in env.boxes[0]
    assert "secret-detail-from-the-server" not in env.everything_shown()
    assert env.plugin._busy is False and env.plugin._dialogs == []

    env.server.route("POST", "/plots", problem_answer(500, "Server error"))  # still failing
    env.plugin.send_selected_polygon()
    env.pump()
    assert len(env.boxes) == 2 and "Try again later" in env.boxes[1]


def test_only_one_request_runs_at_a_time(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    env.server.route("GET", f"/plots/{PLOT_ID}", payload={"plot_id": PLOT_ID, "name": "Linked"})
    monkeypatch.setattr(
        env.plugin_mod.QInputDialog, "getText", staticmethod(lambda *a, **k: (PLOT_ID, True))
    )
    env.plugin.set_current_plot()
    env.plugin.set_current_plot()  # the first request has not finished
    assert any("still running" in text for text in env.bar())
    env.pump()
    assert len(env.server.requests_to("GET", f"/plots/{PLOT_ID}")) == 1
    assert env.plugin._busy is False


def test_the_destination_is_confirmed_before_sending_over_plain_http(
    env: Env, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    env.helpers.save_config(config.PluginConfig("http://atlas.example.test:9/api/v1", API_KEY))
    asked: list[str] = []
    answers = [QMessageBox.No, QMessageBox.Yes]

    def question(_parent: Any, _title: str, text: str, *_args: Any) -> Any:
        asked.append(text)
        return answers.pop(0)

    monkeypatch.setattr(env.plugin_mod.QMessageBox, "question", staticmethod(question))
    env.scripts["SendPlotDialog"] = lambda dialog: int(QDialog.Rejected)

    env.plugin.send_selected_polygon()  # answered "No": no dialog
    assert env.seen == []
    env.plugin.send_selected_polygon()  # answered "Yes": the send dialog opens
    assert env.seen == ["SendPlotDialog"]
    assert len(asked) == 2
    assert "http://atlas.example.test:9" in asked[0] and "unencrypted" in asked[0]
    assert env.server.requests == []


def test_field_selection_problems_are_warnings_in_the_message_bar(env: Env) -> None:
    env.plugin.send_selected_polygon()  # no layers at all
    assert env.iface.bar.messages[-1][2] == env.helpers.LEVEL_WARNING
    assert "Select one field polygon" in env.bar()[-1]
    assert env.seen == [] and env.boxes == [] and env.server.requests == []


def test_a_multi_part_field_is_explained(env: Env) -> None:
    build = LayerBuilder()
    layer = build.layer("Fields")
    far = [(78.0, 14.0), (78.01, 14.0), (78.01, 14.01), (78.0, 14.01)]
    near = [(77.0, 13.0), (77.01, 13.0), (77.01, 13.01), (77.0, 13.01)]
    build.select(layer, build.multipolygon(layer, [near], [far]))
    env.iface.active_layer = layer
    env.plugin.send_selected_polygon()
    assert "Multipart to Singleparts" in env.bar()[-1]
    assert env.server.requests == []


# =========================================================================== 3: carbon estimate
def test_the_carbon_estimate_shows_three_separate_values_and_the_disclaimer(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID, "name": "Linked"})
    items: list[list[str]] = []

    def get_item(_parent: Any, _title: str, _label: str, labels: list[str], *_a: Any) -> Any:
        items.append(list(labels))
        return labels[1], True

    monkeypatch.setattr(env.plugin_mod.QInputDialog, "getItem", staticmethod(get_item))
    env.plugin.estimate_carbon()
    env.pump()

    assert items[0] == ["Tree plantation", "Agroforestry (trees with crops or livestock)"]
    assert [(r.method, r.path) for r in env.server.requests] == [
        ("POST", f"/api/v1/plots/{PLOT_ID}/carbon-estimate"),
        ("GET", f"/api/v1/plots/{PLOT_ID}/market-scenario"),
        ("GET", f"/api/v1/plots/{PLOT_ID}/policy-eligibility"),
    ]
    assert env.server.requests[1].query == {"estimate_id": ["EST-UI1"]}
    assert env.server.requests[2].query == {"activity": ["agroforestry"]}

    results = env.plugin._dialogs[-1]
    page = results.browser.toPlainText()
    assert "Carbon estimate" in results.windowTitle()
    assert "certified: false" in page
    assert "Scenario estimate only. This is not an issued carbon credit." in page
    assert "1 · Environmental benefit" in page
    assert "2 · Indicative carbon value" in page
    assert "3 · Other farm income" in page
    assert "never added together" in page
    for shown in ("4.02", "5.74", "7.46", "₹2,755"):
        assert shown in page
    assert "ESG" not in page
    assert any("certified: false" in text for text in env.bar())


def test_cancelling_the_activity_question_runs_nothing(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID})
    monkeypatch.setattr(
        env.plugin_mod.QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False))
    )
    env.plugin.estimate_carbon()
    env.pump()
    assert env.server.requests == []


def test_actions_that_need_a_plot_explain_what_to_do_first(env: Env) -> None:
    for action in (
        env.plugin.estimate_carbon,
        env.plugin.run_agents,
        env.plugin.import_current_plot,
    ):
        action()
        assert "not linked to a plot yet" in env.bar()[-1]
    assert env.server.requests == [] and env.seen == []


# =========================================================================== 4: AI agent team
def test_the_agent_team_transcript_is_shown(env: Env) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID})
    env.server.route("POST", f"/plots/{PLOT_ID}/agents/run", payload=AGENT_RUN)
    env.plugin.run_agents()
    env.pump()
    (request,) = env.server.requests
    assert request.json == {"plan": "full-assessment", "locale": "en"}
    results = env.plugin._dialogs[-1]
    page = results.browser.toPlainText()
    assert "AI agent team" in results.windowTitle()
    assert "Land analyst" in page and "Tree cover is 12 percent." in page
    assert DISCLAIMER in page and "certified: false" in page


def test_an_older_server_without_the_agent_team_gets_a_friendly_message(env: Env) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID})
    env.plugin.run_agents()  # the fake answers 404 for a route it does not know
    env.pump()
    assert len(env.boxes) == 1
    assert "does not offer the AI agent team" in env.boxes[0] and "HTTP 404" in env.boxes[0]
    assert env.plugin._dialogs == [] and env.plugin._busy is False


# =========================================================================== plot link and files
def test_set_import_and_unlink_the_current_plot(
    env: Env, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    server_plot = {
        "plot_id": PLOT_ID,
        "name": "From server",
        "country": "IN",
        "area_hectares": 10.7,
        "geometry": scene.polygon,
    }
    env.server.route("GET", f"/plots/{PLOT_ID}", payload=server_plot)
    monkeypatch.setattr(
        env.plugin_mod.QInputDialog, "getText", staticmethod(lambda *a, **k: (f" {PLOT_ID} ", True))
    )
    env.plugin.set_current_plot()
    env.pump()
    linked = env.helpers.read_current_plot()
    assert linked is not None and linked["plot_id"] == PLOT_ID
    assert linked["geometry_sha256"] == geometry.fingerprint(scene.polygon)

    layers_before = len(env.core.QgsProject.instance().mapLayers())
    env.plugin.import_current_plot()
    env.pump()
    layers = env.core.QgsProject.instance().mapLayers()
    assert len(layers) == layers_before + 1
    assert any(layer.name() == f"AgriCarbon plot {PLOT_ID}" for layer in layers.values())

    env.plugin.clear_current_plot()
    assert env.helpers.read_current_plot() is None
    env.plugin.run_agents()
    assert "not linked to a plot yet" in env.bar()[-1]


def test_a_public_plot_without_geometry_cannot_be_added_as_a_layer(env: Env) -> None:
    env.helpers.write_current_plot({"plot_id": PLOT_ID})
    env.server.route("GET", f"/plots/{PLOT_ID}", payload={"plot_id": PLOT_ID, "name": "public"})
    layers_before = len(env.core.QgsProject.instance().mapLayers())
    env.plugin.import_current_plot()
    env.pump()
    assert len(env.core.QgsProject.instance().mapLayers()) == layers_before
    assert "did not return a usable polygon" in env.bar()[-1]


def test_unknown_plot_ids_are_explained(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    env.server.route(
        "GET", "/plots/PLT-NOPE", problem_answer(404, "Not Found", slug="plot-not-found")
    )
    monkeypatch.setattr(
        env.plugin_mod.QInputDialog, "getText", staticmethod(lambda *a, **k: ("PLT-NOPE", True))
    )
    env.plugin.set_current_plot()
    env.pump()
    assert "does not exist on the server" in env.boxes[0]
    assert env.helpers.read_current_plot() is None


def test_the_selected_field_can_be_exported_as_geojson(
    env: Env, scene: Scene, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "field"  # no extension: the plugin adds .geojson
    monkeypatch.setattr(
        env.plugin_mod.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **k: (str(target), "")),
    )
    env.plugin.export_selected_geojson()
    written = json.loads((tmp_path / "field.geojson").read_text(encoding="utf-8"))
    assert written["type"] == "FeatureCollection"
    (feature,) = written["features"]
    assert feature["geometry"] == scene.polygon
    assert feature["properties"] == {}  # no attribute of the layer is exported
    assert OWNER_SECRET not in json.dumps(written)
    assert "field.geojson" in env.bar()[-1]
    assert env.server.requests == []


def test_export_can_be_cancelled_and_reports_write_errors(
    env: Env, scene: Scene, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = [""]
    monkeypatch.setattr(
        env.plugin_mod.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **k: (chosen[0], "")),
    )
    env.plugin.export_selected_geojson()
    assert list(tmp_path.iterdir()) == [] and env.boxes == []

    chosen[0] = str(tmp_path / "missing-folder" / "field.geojson")
    env.plugin.export_selected_geojson()
    assert len(env.boxes) == 1 and "could not be written" in env.boxes[0]


# =========================================================================== settings and about
def test_the_settings_dialog_tests_the_connection_and_saves(env: Env) -> None:
    def script(dialog: Any) -> int:
        assert dialog.url_edit.text() == env.server.base_url
        assert dialog.key_edit.text() == API_KEY
        dialog._on_test()
        assert dialog.status_label.text().startswith("Testing")
        env.pump()
        assert dialog.status_label.text().startswith("Connected: AgriCarbon Atlas API 0.1.0")
        assert "Demo mode" in dialog.status_label.text()
        dialog.country_combo.setCurrentIndex(dialog.country_combo.findData("DE"))
        dialog.timeout_spin.setValue(45)
        dialog.accept()
        return int(QDialog.Accepted)

    env.scripts["SettingsDialog"] = script
    env.plugin._species[("x", "IN")] = []  # a cached species list
    env.plugin.open_settings()
    saved = env.helpers.load_config()
    assert saved == config.PluginConfig(env.server.base_url, API_KEY, "DE", 45.0)
    assert env.plugin._species == {}  # a new server may have other species
    assert any("Settings saved" in text for text in env.bar())
    assert env.server.requests_to("GET", "/health")[0].headers["x-api-key"] == API_KEY


def test_a_failing_connection_test_says_why(env: Env) -> None:
    def script(dialog: Any) -> int:
        dialog.url_edit.setText("http://127.0.0.1:9/api/v1")  # nothing listens on port 9
        dialog._on_test()
        env.pump()
        assert "Could not connect" in dialog.status_label.text()
        assert dialog.test_button.isEnabled()
        return int(QDialog.Rejected)

    env.scripts["SettingsDialog"] = script
    env.plugin.open_settings()
    assert env.helpers.load_config().base_url == env.server.base_url  # cancelled: unchanged


def test_about_names_the_licences_and_the_disclaimer(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(
        env.plugin_mod.QMessageBox, "about", staticmethod(lambda _p, _t, text: shown.append(text))
    )
    env.plugin.show_about()
    assert "GPL-2.0-or-later" in shown[0] and "Apache-2.0" in shown[0]
    assert DISCLAIMER in shown[0] and "certified: false" in shown[0]


# =========================================================================== the dialogs alone
@pytest.fixture
def dialogs(fake_qgis_qt: ModuleType) -> ModuleType:
    return importlib.import_module("agricarbon_atlas_qgis.dialogs")


@pytest.fixture
def helpers(fake_qgis_qt: ModuleType) -> ModuleType:
    return importlib.import_module("agricarbon_atlas_qgis.qgis_helpers")


@pytest.fixture
def popups(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    """Replace the static message boxes (they would block) and record what they were asked."""
    seen: dict[str, list[str]] = {"warning": [], "information": []}

    def recorder(kind: str) -> Any:
        return staticmethod(lambda _parent, _title, text, *_a: seen[kind].append(text))

    monkeypatch.setattr(QMessageBox, "warning", recorder("warning"))
    monkeypatch.setattr(QMessageBox, "information", recorder("information"))
    return seen


def labels_of(dialog: Any) -> str:
    return "\n".join(label.text() for label in dialog.findChildren(QtWidgets.QLabel))


def test_settings_dialog_validates_before_it_accepts(
    dialogs: ModuleType, popups: dict[str, list[str]]
) -> None:
    dialog = dialogs.SettingsDialog(config.PluginConfig())
    assert dialog.key_edit.echoMode() == QtWidgets.QLineEdit.Password
    dialog.url_edit.setText("ftp://nope")
    dialog.accept()
    assert dialog.result_config() is None and dialog.result() != QDialog.Accepted
    assert len(popups["warning"]) == 1

    dialog.url_edit.setText("https://atlas.example.org")
    dialog.key_edit.setText("  secret-key  ")
    dialog.country_combo.setCurrentIndex(dialog.country_combo.findData("DE"))
    dialog.timeout_spin.setValue(45)
    dialog.accept()
    assert dialog.result() == QDialog.Accepted
    assert dialog.result_config() == config.PluginConfig(
        "https://atlas.example.org/api/v1", "secret-key", "DE", 45.0
    )


def test_settings_dialog_warns_about_plain_http_to_another_computer(dialogs: ModuleType) -> None:
    dialog = dialogs.SettingsDialog(config.PluginConfig())
    assert dialog.warning_label.text() == ""  # the default is localhost
    dialog.url_edit.setText("http://atlas.example.org/api/v1")
    assert "plain http" in dialog.warning_label.text()
    dialog.url_edit.setText("https://atlas.example.org/api/v1")
    assert dialog.warning_label.text() == ""
    dialog.url_edit.setText("http://192.168.1.20:8000")
    assert "plain http" in dialog.warning_label.text()
    dialog.url_edit.setText("not a url")
    assert dialog.warning_label.text() == ""


def test_settings_dialog_connection_test_flow(dialogs: ModuleType) -> None:
    calls: list[tuple[config.PluginConfig, Callable[[bool, str], None]]] = []
    dialog = dialogs.SettingsDialog(
        config.PluginConfig(), health_check=lambda c, d: calls.append((c, d))
    )
    assert dialog.test_button.isEnabled()

    dialog.url_edit.setText("ftp://nope")
    dialog.test_button.click()
    assert calls == [] and "http" in dialog.status_label.text()

    dialog.url_edit.setText("http://localhost:8000")
    dialog.test_button.click()
    assert len(calls) == 1 and calls[0][0].base_url == "http://localhost:8000/api/v1"
    assert not dialog.test_button.isEnabled()
    assert dialog.status_label.text() == "Testing the connection ..."

    calls[0][1](True, "Connected: AgriCarbon Atlas API 1.0.")
    assert dialog.status_label.text().startswith("Connected") and dialog.test_button.isEnabled()


def test_settings_dialog_without_a_health_check_has_no_test_button(dialogs: ModuleType) -> None:
    assert not dialogs.SettingsDialog(config.PluginConfig()).test_button.isEnabled()


def test_a_connection_result_after_the_dialog_was_deleted_is_ignored(dialogs: ModuleType) -> None:
    from PyQt5 import sip

    dialog = dialogs.SettingsDialog(config.PluginConfig(), health_check=lambda c, d: None)
    sip.delete(dialog)
    dialog._test_done(True, "late answer")  # must not raise


def test_send_dialog_values_and_explanations(dialogs: ModuleType) -> None:
    dialog = dialogs.SendPlotDialog(
        "http://127.0.0.1:8000", "Layer 'Fields', 1 selected polygon with 4 vertices", "IN", "why"
    )
    assert dialog.values() == ("QGIS field", "IN")
    dialog.name_edit.setText("   ")
    assert dialog.values()[0] == "QGIS field"
    dialog.name_edit.setText("x" * 500)
    assert len(dialog.values()[0]) == 120
    dialog.country_combo.setCurrentIndex(0)
    assert dialog.country_combo.itemText(0) == "Let the server detect it"
    assert dialog.values()[1] is None
    text = labels_of(dialog)
    assert "http://127.0.0.1:8000 and nowhere else" in text
    assert "No other attribute of your layer is sent" in text
    assert "not a carbon credit" in text and "why" in text
    assert dialog.windowTitle().endswith("Send field polygon")


def make_count_dialog(
    env_dialogs: ModuleType,
    helpers: ModuleType,
    scene: Scene,
    count: Callable[[Any, Any, Any], CrownCount],
    species: list[Any] | None = None,
    area: Any = 10.0,
) -> Any:
    return env_dialogs.CountTreesDialog(
        field_summary="Layer 'Fields', 1 selected polygon",
        plot_summary="Linked (PLT-UI1)",
        species=species if species is not None else [],
        area_hectares=area,
        excluded_layers=[scene.field_layer],
        count_callback=count,
        suggest_callback=helpers.suggest_confidence_field,
        range_callback=helpers.field_value_range,
    )


def crown_count(counted: int, threshold: float | None = None, below: int = 0) -> CrownCount:
    return CrownCount(
        examined=counted + below,
        invalid=0,
        outside=0,
        inside=counted + below,
        counted=counted,
        below_threshold=below,
        missing_confidence=0,
        threshold=threshold,
    )


@pytest.fixture
def choices() -> list[Any]:
    from agricarbon_atlas_qgis.workflows import SpeciesChoice

    return [
        SpeciesChoice("mango", "Mango (Mangifera indica)", 600.0),
        SpeciesChoice("teak", "Teak"),
    ]


def test_count_dialog_guides_the_user_step_by_step(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    scene = Scene()
    calls: list[tuple[str, str | None, float | None]] = []

    def count(layer: Any, field: str | None, threshold: float | None) -> CrownCount:
        calls.append((layer.name(), field, threshold))
        return crown_count(120, threshold, below=30)

    dialog = make_count_dialog(dialogs, helpers, scene, count, choices)
    combo_items = [dialog.crown_combo.itemText(i) for i in range(dialog.crown_combo.count())]
    assert combo_items == ["", "Tree crowns"]  # the field layer is not offered
    assert dialog.crown_combo.currentLayer() is None
    assert not dialog.send_button.isEnabled()
    assert "preview the count" in dialog.hint_label.text()
    assert "choose the year" in dialog.hint_label.text()
    assert "choose the species" not in dialog.hint_label.text()

    dialog.crown_combo.setLayer(scene.crown_layer)
    assert dialog.confidence_field() == "score"  # auto-detected
    assert dialog.threshold_spin.isEnabled() and dialog.threshold_spin.value() == 0.5
    assert "Values in this field range from" in dialog.range_label.text()

    dialog.preview_button.click()
    assert calls == [("Tree crowns", "score", 0.5)]
    assert "Trees counted: 120" in dialog.result_label.text()
    assert not dialog.send_button.isEnabled()  # the year is still missing
    assert dialog.hint_label.text() == "To continue: choose the year the trees were planted."

    dialog.year_spin.setValue(2018)
    assert dialog.send_button.isEnabled() and dialog.hint_label.text() == ""
    assert "Trees counted: 120" in dialog.result_label.text()  # the year keeps the preview
    dialog.species_combo.setCurrentIndex(dialog.species_combo.findData("teak"))
    assert dialog.send_button.isEnabled()

    values = dialog.values()
    assert values["species_id"] == "teak" and values["plantation_year"] == 2018
    assert values["tree_count"] == 120 and values["confidence_field"] == "score"
    assert values["layer_name"] == "Tree crowns" and values["crown_count"].below_threshold == 30


def test_changing_the_threshold_or_the_layer_makes_the_preview_stale(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    scene = Scene()
    dialog = make_count_dialog(
        dialogs, helpers, scene, lambda layer, field, threshold: crown_count(50, threshold), choices
    )
    dialog.crown_combo.setLayer(scene.crown_layer)
    dialog.year_spin.setValue(2018)
    dialog.preview_button.click()
    assert dialog.send_button.isEnabled()

    dialog.threshold_spin.setValue(0.8)
    assert not dialog.send_button.isEnabled()
    assert "Press 'Preview count'" in dialog.result_label.text()
    with pytest.raises(ValueError):
        dialog.values()

    dialog.preview_button.click()
    assert dialog.send_button.isEnabled()
    dialog.crown_combo.setCurrentIndex(0)  # back to "no layer"
    assert not dialog.send_button.isEnabled()


def test_without_a_confidence_field_the_threshold_is_off(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    scene = Scene()
    calls: list[tuple[Any, Any]] = []

    def count(_layer: Any, field: Any, threshold: Any) -> CrownCount:
        calls.append((field, threshold))
        return crown_count(10)

    dialog = make_count_dialog(dialogs, helpers, scene, count, choices)
    dialog.crown_combo.setLayer(scene.crown_layer)
    dialog.field_combo.setCurrentIndex(0)  # the empty entry
    assert dialog.confidence_field() is None and not dialog.threshold_spin.isEnabled()
    assert dialog.threshold() is None and dialog.range_label.text() == ""
    dialog.preview_button.click()
    assert calls == [(None, None)]


def test_a_count_of_zero_cannot_be_sent(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    scene = Scene()
    dialog = make_count_dialog(
        dialogs,
        helpers,
        scene,
        lambda layer, field, threshold: crown_count(0, threshold, 40),
        choices,
    )
    dialog.crown_combo.setLayer(scene.crown_layer)
    dialog.year_spin.setValue(2018)
    dialog.preview_button.click()
    assert not dialog.send_button.isEnabled()
    assert "no crown was counted" in dialog.hint_label.text()


def test_count_problems_are_shown_and_do_not_leave_a_preview(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any], popups: dict[str, list[str]]
) -> None:
    scene = Scene()

    def broken(_layer: Any, _field: Any, _threshold: Any) -> CrownCount:
        raise ValueError("The crown layer has no field called 'score'.")

    dialog = make_count_dialog(dialogs, helpers, scene, broken, choices)
    dialog.preview_button.click()  # no layer chosen yet
    assert popups["information"] == ["Choose the layer that holds the detected tree crowns first."]
    dialog.crown_combo.setLayer(scene.crown_layer)
    dialog.preview_button.click()
    assert popups["warning"] == ["The crown layer has no field called 'score'."]
    assert "Press 'Preview count'" in dialog.result_label.text()
    assert QApplication.overrideCursor() is None  # the busy cursor was restored


def test_without_a_species_list_the_id_can_be_typed(
    dialogs: ModuleType, helpers: ModuleType
) -> None:
    scene = Scene()
    dialog = make_count_dialog(
        dialogs, helpers, scene, lambda layer, field, threshold: crown_count(5, threshold)
    )
    assert dialog.species_combo.isEditable() and dialog.species_id() == ""
    assert "choose the species" in dialog.hint_label.text()
    dialog.species_combo.setEditText("  mango ")
    assert dialog.species_id() == "mango"
    assert "choose the species" not in dialog.hint_label.text()


def test_a_density_above_the_species_maximum_is_flagged(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    scene = Scene()
    dialog = make_count_dialog(
        dialogs,
        helpers,
        scene,
        lambda layer, field, threshold: crown_count(7000, threshold),
        choices,
        area=10.0,
    )
    dialog.crown_combo.setLayer(scene.crown_layer)
    dialog.preview_button.click()
    assert "About 700 trees per hectare on 10.00 ha." in dialog.result_label.text()
    assert "above the 600 trees/ha" in dialog.result_label.text()  # mango, the first species
    dialog.species_combo.setCurrentIndex(dialog.species_combo.findData("teak"))
    assert "above the" not in dialog.result_label.text()  # teak has no maximum on file


def test_the_dialog_explains_that_the_year_is_an_input(
    dialogs: ModuleType, helpers: ModuleType, choices: list[Any]
) -> None:
    dialog = make_count_dialog(dialogs, helpers, Scene(), lambda *a: crown_count(1), choices)
    text = labels_of(dialog)
    assert "model-estimated" in text and "cannot be read from the crowns" in text
    assert dialog.plantation_year() is None


# =========================================================================== results window
def test_the_results_window_copies_and_saves(
    dialogs: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = "<html><body><h2>Carbon estimate</h2><p>certified: false</p></body></html>"
    window = dialogs.ResultsDialog("Carbon estimate", page)
    assert window.windowTitle() == "AgriCarbon Atlas - Carbon estimate"
    assert not window.isModal()
    buttons = {b.text(): b for b in window.findChildren(QtWidgets.QPushButton)}
    assert set(buttons) == {"Copy as text", "Save as HTML ...", "Close"}

    buttons["Copy as text"].click()
    assert "certified: false" in QApplication.clipboard().text()

    target = tmp_path / "results"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), ""))
    )
    buttons["Save as HTML ..."].click()
    assert (tmp_path / "results.html").read_text(encoding="utf-8") == page


def test_the_results_window_survives_cancel_and_write_errors(
    dialogs: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    popups: dict[str, list[str]],
) -> None:
    window = dialogs.ResultsDialog("x", "<html><body>x</body></html>")
    save = next(b for b in window.findChildren(QtWidgets.QPushButton) if "Save" in b.text())
    chosen = [""]
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (chosen[0], ""))
    )
    save.click()
    assert list(tmp_path.iterdir()) == [] and popups["warning"] == []
    chosen[0] = str(tmp_path / "nope" / "out.html")
    save.click()
    assert len(popups["warning"]) == 1 and "could not be saved" in popups["warning"][0]
