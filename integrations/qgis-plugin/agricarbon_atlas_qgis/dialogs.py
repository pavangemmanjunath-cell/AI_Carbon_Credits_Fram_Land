# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""Dialogs of the plugin, built in code with ``qgis.PyQt`` (no .ui files).

The dialogs only collect input and show text. Validation rules, counting and formatting live in
the pure-Python modules; anything that needs the network or a QGIS layer is passed in as a
callback so the dialogs stay small.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from qgis.core import QgsFieldProxyModel, QgsMapLayerProxyModel
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from . import config
from .crowns import DEFAULT_CONFIDENCE_THRESHOLD, CrownCount
from .formatting import describe_confidence_range, describe_crown_count
from .version import PLUGIN_NAME
from .workflows import SpeciesChoice, density_note

MIN_PLANTATION_YEAR = 1900
DEFAULT_PLOT_NAME = "QGIS field"
MAX_NAME_LENGTH = 120

#: ``(ok, message)`` callback used by the Settings dialog to report the connection test.
TestDone = Callable[[bool, str], None]
HealthCheck = Callable[[config.PluginConfig, TestDone], None]


def run_dialog(dialog: QDialog) -> int:
    """Run a dialog modally (``exec`` on current PyQt, ``exec_`` on older builds)."""
    runner = getattr(dialog, "exec", None) or dialog.exec_
    return runner()


def _note(text: str, parent: QWidget | None = None) -> QLabel:
    """A word-wrapped plain-text label for explanations."""
    label = QLabel(text, parent)
    label.setWordWrap(True)
    label.setTextFormat(Qt.PlainText)
    return label


def _selectable(text: str = "", parent: QWidget | None = None) -> QLabel:
    label = _note(text, parent)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


def _fit(dialog: QDialog, width: int) -> None:
    """Give a dialog its first size: word-wrapped labels make the default size hint too short."""
    dialog.setMinimumWidth(width)
    dialog.resize(width, dialog.sizeHint().height())
    _grow(dialog)


def _grow(dialog: QDialog) -> None:
    """Grow (never shrink) a dialog so wrapped text that just changed is not cut off."""
    layout = dialog.layout()
    if layout is None or not layout.hasHeightForWidth():
        return
    needed = layout.heightForWidth(dialog.width())
    if needed > dialog.height():
        dialog.resize(dialog.width(), needed)


def _country_combo(parent: QWidget, detect_label: str | None = None) -> QComboBox:
    """Drop-down with the supported countries; ``detect_label`` adds a "server decides" entry."""
    combo = QComboBox(parent)
    if detect_label:
        combo.addItem(detect_label, None)
    for code in config.SUPPORTED_COUNTRIES:
        combo.addItem(config.country_label(code), code)
    return combo


def _select_country(combo: QComboBox, code: str | None) -> None:
    index = combo.findData(code)
    if index >= 0:
        combo.setCurrentIndex(index)


# =========================================================================== settings
class SettingsDialog(QDialog):
    """API base URL, API key, default country and timeout, with a connection test."""

    def __init__(
        self,
        cfg: config.PluginConfig,
        health_check: HealthCheck | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{PLUGIN_NAME} - Settings")
        self._health_check = health_check
        self._result: config.PluginConfig | None = None

        self.url_edit = QLineEdit(cfg.base_url, self)
        self.url_edit.setPlaceholderText(config.DEFAULT_BASE_URL)
        self.key_edit = QLineEdit(cfg.api_key, self)
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Optional")
        self.country_combo = _country_combo(self)
        _select_country(self.country_combo, cfg.default_country)
        self.timeout_spin = QSpinBox(self)
        self.timeout_spin.setRange(int(config.MIN_TIMEOUT_S), int(config.MAX_TIMEOUT_S))
        self.timeout_spin.setSuffix(" s")
        self.timeout_spin.setValue(int(round(cfg.timeout_s)))

        form = QFormLayout()
        form.addRow("API base URL", self.url_edit)
        form.addRow("API key", self.key_edit)
        form.addRow("Default country", self.country_combo)
        form.addRow("Request timeout", self.timeout_spin)

        self.warning_label = _note("", self)
        self.status_label = _selectable("", self)
        self.test_button = QPushButton("Test connection", self)
        self.test_button.setEnabled(health_check is not None)
        self.test_button.clicked.connect(self._on_test)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        test_row = QHBoxLayout()
        test_row.addWidget(self.test_button)
        test_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(
            _note(
                "Address of your AgriCarbon Atlas API, for example "
                f"{config.DEFAULT_BASE_URL}. Field polygons are sent only to this server.",
                self,
            )
        )
        layout.addLayout(form)
        layout.addWidget(self.warning_label)
        layout.addLayout(test_row)
        layout.addWidget(self.status_label)
        layout.addWidget(
            _note(
                "The API key is optional and is stored as plain text in your QGIS user profile. "
                "Use a key that only has the access you need, and leave the field empty if the "
                "server does not ask for one.",
                self,
            )
        )
        layout.addWidget(buttons)

        self.url_edit.textChanged.connect(self._update_warning)
        self._update_warning()
        _fit(self, 520)

    # -- behaviour --------------------------------------------------------------------------
    def collect(self) -> tuple[config.PluginConfig | None, list[str]]:
        """Validate the form: ``(config, [])`` or ``(None, [message, ...])``."""
        return config.validate_settings(
            self.url_edit.text(),
            self.key_edit.text(),
            self.country_combo.currentData(),
            self.timeout_spin.value(),
        )

    def result_config(self) -> config.PluginConfig | None:
        """The validated settings after the dialog was accepted."""
        return self._result

    def _update_warning(self, *_args: Any) -> None:
        try:
            insecure = config.is_insecure_remote(config.normalize_base_url(self.url_edit.text()))
        except config.ConfigError:
            insecure = False
        self.warning_label.setText(
            "Warning: this address uses plain http to another computer. The API key and your "
            "field polygon would travel unencrypted. Use an https:// address."
            if insecure
            else ""
        )
        _grow(self)

    def _on_test(self) -> None:
        cfg, errors = self.collect()
        if cfg is None:
            self.status_label.setText("\n".join(errors))
            _grow(self)
            return
        if self._health_check is None:
            return
        self.test_button.setEnabled(False)
        self.status_label.setText("Testing the connection ...")
        _grow(self)
        self._health_check(cfg, self._test_done)

    def _test_done(self, ok: bool, message: str) -> None:
        try:
            self.status_label.setText(message)
            self.test_button.setEnabled(True)
            _grow(self)
        except RuntimeError:  # the dialog was closed while the test was running
            pass

    def accept(self) -> None:
        cfg, errors = self.collect()
        if cfg is None:
            QMessageBox.warning(self, PLUGIN_NAME, "\n".join(errors))
            return
        self._result = cfg
        super().accept()


# =========================================================================== send polygon
class SendPlotDialog(QDialog):
    """Confirm what is sent: the polygon of the selected field, a name and the country."""

    def __init__(
        self,
        destination: str,
        field_summary: str,
        default_country: str | None,
        reason: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{PLUGIN_NAME} - Send field polygon")

        self.name_edit = QLineEdit(DEFAULT_PLOT_NAME, self)
        self.name_edit.setMaxLength(MAX_NAME_LENGTH)
        self.country_combo = _country_combo(self, detect_label="Let the server detect it")
        _select_country(self.country_combo, default_country)

        form = QFormLayout()
        form.addRow("Field", _selectable(field_summary, self))
        form.addRow("Plot name", self.name_edit)
        form.addRow("Country", self.country_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("Send polygon")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        if reason:
            layout.addWidget(_note(reason, self))
        layout.addLayout(form)
        layout.addWidget(
            _note(
                f"The polygon, the name and the country are sent to {destination} and nowhere "
                "else. No other attribute of your layer is sent. The result is a scenario "
                "estimate, not a carbon credit.",
                self,
            )
        )
        layout.addWidget(buttons)
        _fit(self, 520)

    def values(self) -> tuple[str, str | None]:
        """``(name, country)``; the country is ``None`` when the server should detect it."""
        name = self.name_edit.text().strip() or DEFAULT_PLOT_NAME
        return name, self.country_combo.currentData()


# =========================================================================== count trees
class CountTreesDialog(QDialog):
    """Pick the crown layer, preview the count inside the field and enter species and year.

    ``count_callback(crown_layer, confidence_field, threshold)`` returns a :class:`CrownCount`
    (or raises ``ValueError``); ``suggest_callback(crown_layer)`` names the likely confidence
    field; ``range_callback(crown_layer, field)`` returns ``(min, max)`` of a field or ``None``.
    """

    def __init__(
        self,
        field_summary: str,
        plot_summary: str,
        species: Sequence[SpeciesChoice],
        area_hectares: Any,
        excluded_layers: Iterable[Any],
        count_callback: Callable[[Any, str | None, float | None], CrownCount],
        suggest_callback: Callable[[Any], str | None],
        range_callback: Callable[[Any, str | None], tuple[float, float] | None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{PLUGIN_NAME} - Count trees from segmentation layer")
        self._species = list(species)
        self._area = area_hectares
        self._count_callback = count_callback
        self._suggest_callback = suggest_callback
        self._range_callback = range_callback
        self._preview: CrownCount | None = None
        self._preview_layer_name = ""
        self._preview_field: str | None = None
        self._max_year = datetime.date.today().year

        # -- crown layer and confidence filter
        self.crown_combo = QgsMapLayerComboBox(self)
        self.crown_combo.setFilters(
            QgsMapLayerProxyModel.PolygonLayer | QgsMapLayerProxyModel.PointLayer
        )
        self.crown_combo.setAllowEmptyLayer(True)
        self.crown_combo.setExceptedLayerList(list(excluded_layers))
        self.crown_combo.setCurrentIndex(0)  # the empty entry: the user must choose a layer

        self.field_combo = QgsFieldComboBox(self)
        self.field_combo.setFilters(QgsFieldProxyModel.Numeric)
        self.field_combo.setAllowEmptyFieldName(True)

        self.threshold_spin = QDoubleSpinBox(self)
        self.threshold_spin.setDecimals(3)
        self.threshold_spin.setRange(0.0, 1_000_000.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(DEFAULT_CONFIDENCE_THRESHOLD)
        self.threshold_spin.setEnabled(False)

        self.range_label = _note("", self)

        # -- inventory inputs
        self.species_combo = QComboBox(self)
        for choice in self._species:
            self.species_combo.addItem(choice.label, choice.id)
        if not self._species:
            self.species_combo.setEditable(True)
            self.species_combo.lineEdit().setPlaceholderText("type a species id")

        self.year_spin = QSpinBox(self)
        self.year_spin.setRange(MIN_PLANTATION_YEAR - 1, self._max_year)
        self.year_spin.setSpecialValueText("choose the year")
        self.year_spin.setValue(MIN_PLANTATION_YEAR - 1)

        form = QFormLayout()
        form.addRow("Field", _selectable(field_summary, self))
        form.addRow("Plot", _selectable(plot_summary, self))
        form.addRow("Tree-crown layer", self.crown_combo)
        form.addRow("Confidence field", self.field_combo)
        form.addRow("Minimum confidence", self.threshold_spin)
        form.addRow("", self.range_label)
        form.addRow("Species", self.species_combo)
        form.addRow("Year planted", self.year_spin)

        self.result_label = _selectable("", self)
        self.hint_label = _note("", self)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.send_button = self.buttons.button(QDialogButtonBox.Ok)
        self.send_button.setText("Send inventory")
        self.preview_button = self.buttons.addButton("Preview count", QDialogButtonBox.ActionRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(
            _note(
                "A crown counts as one tree when its centre lies inside the selected field. "
                "Choose the layer with the detected crowns (for example the output of an AI "
                "segmentation plugin), preview the count and check it against the imagery.",
                self,
            )
        )
        layout.addLayout(form)
        layout.addWidget(self.result_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(
            _note(
                "The planting year cannot be read from the crowns: enter the year the trees "
                "were planted (an estimate is fine). The inventory is stored with measurement "
                "source 'model-estimated'.",
                self,
            )
        )
        layout.addWidget(self.buttons)

        self.crown_combo.layerChanged.connect(self._on_layer_changed)
        self.field_combo.fieldChanged.connect(self._on_field_changed)
        self.threshold_spin.valueChanged.connect(self._on_threshold_changed)
        # Species and year do not change the count, so they keep the preview.
        self.species_combo.currentIndexChanged.connect(self._refresh)
        self.species_combo.editTextChanged.connect(self._refresh)
        self.year_spin.valueChanged.connect(self._refresh)
        self.preview_button.clicked.connect(self._on_preview)
        self._refresh()
        _fit(self, 620)

    # -- inputs -----------------------------------------------------------------------------
    def species_id(self) -> str:
        if self.species_combo.isEditable():
            return self.species_combo.currentText().strip()
        data = self.species_combo.currentData()
        return str(data) if data else ""

    def confidence_field(self) -> str | None:
        return self.field_combo.currentField() or None

    def threshold(self) -> float | None:
        return self.threshold_spin.value() if self.confidence_field() else None

    def plantation_year(self) -> int | None:
        year = self.year_spin.value()
        return year if year >= MIN_PLANTATION_YEAR else None

    def _selected_species(self) -> SpeciesChoice | None:
        chosen = self.species_id()
        return next((s for s in self._species if s.id == chosen), None)

    # -- events -----------------------------------------------------------------------------
    def _on_layer_changed(self, layer: Any) -> None:
        self.field_combo.setLayer(layer)  # resets to the empty entry
        suggestion = self._suggest_callback(layer) if layer is not None else None
        if suggestion:
            self.field_combo.setField(suggestion)
        self._on_field_changed()

    def _on_field_changed(self, *_args: Any) -> None:
        name = self.confidence_field()
        self.threshold_spin.setEnabled(bool(name))
        self._update_range_hint()
        self._on_inputs_changed()

    def _on_threshold_changed(self, *_args: Any) -> None:
        self._update_range_hint()
        self._on_inputs_changed()

    def _on_inputs_changed(self, *_args: Any) -> None:
        """The layer, the confidence field or the threshold changed: the preview is stale."""
        self._preview = None
        self._refresh()

    def _update_range_hint(self) -> None:
        layer, name = self.crown_combo.currentLayer(), self.confidence_field()
        span = self._range_callback(layer, name) if layer is not None and name else None
        low, high = span if span else (None, None)
        self.range_label.setText(describe_confidence_range(low, high, self.threshold()))
        _grow(self)

    def _on_preview(self) -> None:
        layer = self.crown_combo.currentLayer()
        if layer is None:
            QMessageBox.information(
                self, PLUGIN_NAME, "Choose the layer that holds the detected tree crowns first."
            )
            return
        field, threshold = self.confidence_field(), self.threshold()
        count: CrownCount | None = None
        problem = ""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            count = self._count_callback(layer, field, threshold)
        except ValueError as exc:  # HelperError and invalid thresholds are ValueErrors
            problem = str(exc)
        finally:
            QApplication.restoreOverrideCursor()
        if count is None:
            QMessageBox.warning(self, PLUGIN_NAME, problem or "The crowns could not be counted.")
            return
        self._preview = count
        self._preview_layer_name = layer.name()
        self._preview_field = field
        self._refresh()

    def _refresh(self, *_args: Any) -> None:
        preview = self._preview
        if preview is None:
            self.result_label.setText("Press 'Preview count' to count the crowns inside the field.")
        else:
            lines = [
                f"Trees counted: {preview.counted:,}",
                describe_crown_count(preview, self._preview_field),
            ]
            species = self._selected_species()
            note = density_note(
                preview.counted, self._area, species.max_density_per_ha if species else None
            )
            if note:
                lines.append(note)
            self.result_label.setText("\n".join(lines))

        problems = []
        if preview is None:
            problems.append("preview the count")
        elif preview.counted < 1:
            problems.append("adjust the layer or the confidence filter: no crown was counted")
        if not self.species_id():
            problems.append("choose the species")
        if self.plantation_year() is None:
            problems.append("choose the year the trees were planted")
        self.hint_label.setText("To continue: " + "; ".join(problems) + "." if problems else "")
        self.send_button.setEnabled(not problems)
        _grow(self)

    # -- result -----------------------------------------------------------------------------
    def values(self) -> dict[str, Any]:
        """The accepted inputs; only meaningful after the dialog was accepted."""
        preview = self._preview
        if preview is None:
            raise ValueError("The count has not been previewed.")
        year = self.plantation_year()
        if year is None:
            raise ValueError("The planting year has not been chosen.")
        return {
            "species_id": self.species_id(),
            "plantation_year": year,
            "tree_count": preview.counted,
            "crown_count": preview,
            "confidence_field": self._preview_field,
            "layer_name": self._preview_layer_name,
        }


# =========================================================================== results
class ResultsDialog(QDialog):
    """A non-modal window with an HTML page and buttons to copy or save it."""

    def __init__(self, title: str, html_page: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{PLUGIN_NAME} - {title}")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(False)
        self.resize(800, 680)
        self._html = html_page

        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(html_page)

        copy_button = QPushButton("Copy as text", self)
        copy_button.clicked.connect(self._copy_text)
        save_button = QPushButton("Save as HTML ...", self)
        save_button.clicked.connect(self._save_html)
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)

        row = QHBoxLayout()
        row.addWidget(copy_button)
        row.addWidget(save_button)
        row.addStretch(1)
        row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        layout.addLayout(row)

    def _copy_text(self) -> None:
        QApplication.clipboard().setText(self.browser.toPlainText())

    def _save_html(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self, "Save results as HTML", "agricarbon-atlas-results.html", "HTML (*.html)"
        )
        if not path:
            return
        if not path.lower().endswith((".html", ".htm")):
            path += ".html"
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._html)
        except OSError as exc:
            QMessageBox.warning(self, PLUGIN_NAME, f"The file could not be saved: {exc.strerror}")
