# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 AgriCarbon Atlas contributors
"""QGIS-dependent helpers: settings, project state, geometry transforms, layer access, logging.

Everything that needs ``qgis.core`` lives here (and in ``plugin.py`` / ``dialogs.py`` /
``tasks.py``); the pure-Python modules do the validation, counting and formatting.

Privacy: nothing in this module logs coordinates, geometries or attribute values.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMessageLog,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)

from . import config, crowns, geometry
from .version import PLUGIN_NAME

SETTINGS_PREFIX = "AgriCarbonAtlas/"
PROJECT_SCOPE = "AgriCarbonAtlas"
PROJECT_KEY_PLOT = "current_plot"
WGS84_AUTHID = "EPSG:4326"

Ring = list[tuple[float, float]]
Polygon = list[Ring]  # outer ring first, then holes

# Message levels: ``Qgis.MessageLevel.Info`` on newer 3.x builds, ``Qgis.Info`` on older ones.
_LEVELS = getattr(Qgis, "MessageLevel", Qgis)
LEVEL_INFO = _LEVELS.Info
LEVEL_SUCCESS = _LEVELS.Success
LEVEL_WARNING = _LEVELS.Warning
LEVEL_CRITICAL = _LEVELS.Critical


class HelperError(ValueError):
    """A precondition failed (no selection, wrong layer type, ...). The message is for users."""


# --------------------------------------------------------------------------- settings
def _stored(settings: Any, key: str, default: Any, kind: type) -> Any:
    """One stored setting read as ``kind``; a value that cannot be read that way counts as unset.

    PyQt raises ``TypeError`` when a hand-edited value cannot be converted (for instance text in
    the timeout), and that must not stop the Settings dialog or an action from opening.
    """
    try:
        return settings.value(SETTINGS_PREFIX + key, default, type=kind)
    except (TypeError, ValueError):
        return default


def load_config() -> config.PluginConfig:
    """Read the plugin settings from ``QgsSettings`` (invalid stored values use the defaults)."""
    settings = QgsSettings()
    return config.coerce_config(
        base_url=_stored(settings, "api_base_url", config.DEFAULT_BASE_URL, str),
        api_key=_stored(settings, "api_key", "", str),
        default_country=_stored(settings, "default_country", config.DEFAULT_COUNTRY, str),
        timeout=_stored(settings, "timeout_s", config.DEFAULT_TIMEOUT_S, float),
    )


def save_config(cfg: config.PluginConfig) -> None:
    """Store the settings. The API key is kept in clear text in the QGIS profile (see README)."""
    settings = QgsSettings()
    settings.setValue(SETTINGS_PREFIX + "api_base_url", cfg.base_url)
    settings.setValue(SETTINGS_PREFIX + "api_key", cfg.api_key)
    settings.setValue(SETTINGS_PREFIX + "default_country", cfg.default_country)
    settings.setValue(SETTINGS_PREFIX + "timeout_s", cfg.timeout_s)


# --------------------------------------------------------------------------- project state
def read_current_plot() -> dict[str, Any] | None:
    """The plot linked to the open QGIS project (id, name, country, area), or ``None``.

    Only a few non-spatial fields are stored in the project file - never coordinates. The
    ``geometry_sha256`` digest lets the plugin recognise the field that was already sent.
    """
    text, found = QgsProject.instance().readEntry(PROJECT_SCOPE, PROJECT_KEY_PLOT, "")
    if not found or not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, dict) and isinstance(data.get("plot_id"), str) and data["plot_id"]:
        return data
    return None


def write_current_plot(plot: dict[str, Any] | None) -> None:
    project = QgsProject.instance()
    if plot is None:
        project.removeEntry(PROJECT_SCOPE, PROJECT_KEY_PLOT)
        return
    keep = {
        key: plot[key]
        for key in ("plot_id", "name", "country", "area_hectares", "geometry_sha256")
        if plot.get(key) is not None
    }
    project.writeEntry(PROJECT_SCOPE, PROJECT_KEY_PLOT, json.dumps(keep))


# --------------------------------------------------------------------------- field layer
def is_polygon_layer(layer: Any) -> bool:
    return isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry


def find_field_layer(active_layer: Any) -> Any:
    """The polygon layer that holds the user's field (the one with a selected feature).

    The active layer wins when it is a polygon layer with a selection; otherwise the only
    polygon layer with a selection is used. Anything ambiguous raises :class:`HelperError` with
    advice on what to do.
    """
    if is_polygon_layer(active_layer) and active_layer.selectedFeatureCount() > 0:
        return active_layer
    candidates = [
        layer
        for layer in QgsProject.instance().mapLayers().values()
        if is_polygon_layer(layer) and layer.selectedFeatureCount() > 0
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise HelperError(
            "Select one field polygon first: choose the layer that holds your field in the "
            "Layers panel, then click the field with the Select Features tool."
        )
    names = ", ".join(f"'{layer.name()}'" for layer in candidates[:4])
    raise HelperError(
        f"Features are selected in several polygon layers ({names}). Make the layer with your "
        "field the active layer in the Layers panel, or clear the other selections."
    )


# --------------------------------------------------------------------------- geometry
def selected_field_feature(layer: Any) -> Any:
    """Return the single selected polygon feature of ``layer`` or raise :class:`HelperError`."""
    if not isinstance(layer, QgsVectorLayer):
        raise HelperError("Select a polygon layer in the Layers panel first.")
    if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        raise HelperError(f"Layer '{layer.name()}' does not contain polygons.")
    count = layer.selectedFeatureCount()
    if count == 0:
        raise HelperError(
            f"Select one field polygon in layer '{layer.name()}' first (Select Features tool)."
        )
    if count > 1:
        raise HelperError(
            f"{count} features are selected in layer '{layer.name()}'; select exactly one field."
        )
    return layer.selectedFeatures()[0]


def _closed(ring: Ring) -> Ring:
    """GeoJSON rings repeat the first position at the end; QGIS normally does so already."""
    return ring if ring[0] == ring[-1] else [*ring, ring[0]]


def _polygons_of(feature: Any) -> list[Polygon]:
    """Polygons of a feature as plain ``(x, y)`` rings in the layer CRS (curves are segmented)."""
    geom = QgsGeometry(feature.geometry())
    if geom.isNull() or geom.isEmpty():
        raise HelperError("The selected feature has no geometry.")
    if QgsWkbTypes.isCurvedType(geom.wkbType()):
        geom.convertToStraightSegment()
    if geom.type() != QgsWkbTypes.PolygonGeometry:
        raise HelperError("The selected feature is not a polygon.")
    polygons = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
    result: list[Polygon] = []
    for polygon in polygons:
        rings = [[(p.x(), p.y()) for p in ring] for ring in polygon]
        if rings and rings[0]:  # an outer ring is needed; empty holes are dropped
            result.append([_closed(ring) for ring in rings if ring])
    if not result:
        raise HelperError("The selected feature has no polygon rings.")
    return result


def _reproject(polygons: list[Polygon], source: Any, target: Any) -> list[Polygon]:
    if not source.isValid():
        raise HelperError("The layer has no valid coordinate reference system (CRS).")
    if source == target:
        return polygons
    transform = QgsCoordinateTransform(source, target, QgsProject.instance().transformContext())
    try:
        return [
            [
                [(q.x(), q.y()) for q in (transform.transform(QgsPointXY(x, y)) for x, y in ring)]
                for ring in polygon
            ]
            for polygon in polygons
        ]
    except QgsCsException:
        raise HelperError(
            "The geometry could not be transformed between the layer CRS and the target CRS."
        ) from None


def feature_to_wgs84_polygon(feature: Any, source_crs: Any) -> dict[str, Any]:
    """Selected field -> validated GeoJSON ``Polygon`` in EPSG:4326 (raises on anything else)."""
    target = QgsCoordinateReferenceSystem(WGS84_AUTHID)
    polygons = _reproject(_polygons_of(feature), source_crs, target)
    coordinates = [[[[x, y] for x, y in ring] for ring in polygon] for polygon in polygons]
    if len(coordinates) == 1:
        raw = {"type": "Polygon", "coordinates": coordinates[0]}
    else:
        raw = {"type": "MultiPolygon", "coordinates": coordinates}
    return geometry.normalize_polygon(raw)  # may raise GeometryError (multi-part, >500, ...)


# --------------------------------------------------------------------------- crown counting
def numeric_field_names(layer: Any) -> list[str]:
    return [field.name() for field in layer.fields() if field.isNumeric()]


def suggest_confidence_field(layer: Any) -> str | None:
    """Auto-detect a confidence field (score / confidence / prob / probability ...)."""
    return crowns.detect_confidence_field(numeric_field_names(layer))


def field_value_range(layer: Any, field_name: str | None) -> tuple[float, float] | None:
    """Smallest and largest value of a numeric field (to spot a 0-1 versus 0-100 scale)."""
    if not field_name:
        return None
    index = layer.fields().indexFromName(field_name)
    if index < 0:
        return None
    try:
        low = crowns.to_float(layer.minimumValue(index))
        high = crowns.to_float(layer.maximumValue(index))
    except Exception:  # a provider that cannot compute statistics: the hint is optional
        return None
    return (low, high) if low is not None and high is not None else None


def _bounds(polygons: list[Polygon]) -> QgsRectangle:
    xs = [x for polygon in polygons for x, _ in polygon[0]]
    ys = [y for polygon in polygons for _, y in polygon[0]]
    return QgsRectangle(min(xs), min(ys), max(xs), max(ys))


def _crown_stream(
    layer: Any, polygons: list[Polygon], confidence_field: str | None
) -> Iterator[tuple[Any, Any, Any]]:
    """Yield ``(x, y, confidence)`` per crown feature near the field, centroid in the layer CRS."""
    request = QgsFeatureRequest().setFilterRect(_bounds(polygons))
    request.setSubsetOfAttributes([confidence_field] if confidence_field else [], layer.fields())
    for feature in layer.getFeatures(request):
        geom = feature.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            yield (None, None, None)
            continue
        centroid = geom.centroid()
        if centroid.isNull():
            yield (None, None, None)
            continue
        point = centroid.asPoint()
        yield (point.x(), point.y(), feature[confidence_field] if confidence_field else None)


def count_crowns_in_field(
    field_layer: Any,
    crown_layer: Any,
    confidence_field: str | None,
    threshold: float | None,
) -> crowns.CrownCount:
    """Count crown centroids of ``crown_layer`` inside the selected feature of ``field_layer``.

    The field is reprojected into the CRS of the crown layer once, so no crown geometry has to be
    transformed. With a confidence field and a threshold, only crowns with ``confidence >=
    threshold`` are counted.
    """
    if not isinstance(crown_layer, QgsVectorLayer):
        raise HelperError("Choose the layer that holds the detected tree crowns.")
    if crown_layer.geometryType() not in (QgsWkbTypes.PolygonGeometry, QgsWkbTypes.PointGeometry):
        raise HelperError("The crown layer must contain polygons or points.")
    if confidence_field and confidence_field not in crown_layer.fields().names():
        raise HelperError(f"The crown layer has no field called '{confidence_field}'.")
    feature = selected_field_feature(field_layer)
    polygons = _reproject(_polygons_of(feature), field_layer.crs(), crown_layer.crs())
    stream = _crown_stream(crown_layer, polygons, confidence_field)
    return crowns.count_crowns(stream, polygons, threshold if confidence_field else None)


# --------------------------------------------------------------------------- plot layer
def add_plot_layer(plot: dict[str, Any]) -> Any:
    """Add the plot returned by the API to the project as a memory polygon layer (EPSG:4326)."""
    polygon = geometry.normalize_polygon(plot.get("geometry"))
    plot_id = str(plot.get("plot_id") or "plot")
    uri = (
        "Polygon?crs=EPSG:4326&field=plot_id:string&field=name:string"
        "&field=country:string&field=area_ha:double"
    )
    layer = QgsVectorLayer(uri, f"AgriCarbon plot {plot_id}", "memory")
    feature = QgsFeature(layer.fields())
    rings = [[QgsPointXY(x, y) for x, y in ring] for ring in polygon["coordinates"]]
    feature.setGeometry(QgsGeometry.fromPolygonXY(rings))
    area = plot.get("area_hectares")
    feature.setAttributes(
        [
            plot_id,
            str(plot.get("name") or ""),
            str(plot.get("country") or ""),
            float(area) if isinstance(area, (int, float)) else None,
        ]
    )
    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()
    QgsProject.instance().addMapLayer(layer)
    return layer


# --------------------------------------------------------------------------- logging
class QgsLogHandler(logging.Handler):
    """Forward the plugin's log records to the QGIS log panel (tab "AgriCarbon Atlas")."""

    _LEVEL_MAP = {
        logging.DEBUG: LEVEL_INFO,
        logging.INFO: LEVEL_INFO,
        logging.WARNING: LEVEL_WARNING,
        logging.ERROR: LEVEL_CRITICAL,
        logging.CRITICAL: LEVEL_CRITICAL,
    }

    def emit(self, record: logging.LogRecord) -> None:
        level = self._LEVEL_MAP.get(record.levelno, LEVEL_INFO)
        try:
            text = self.format(record)
            try:
                # notifyUser=False: the plugin shows its own message-bar notices.
                QgsMessageLog.logMessage(text, PLUGIN_NAME, level, False)
            except TypeError:
                QgsMessageLog.logMessage(text, PLUGIN_NAME, level)
        except Exception:  # logging must never break the plugin
            pass


def install_log_handler() -> QgsLogHandler:
    handler = QgsLogHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("agricarbon_atlas_qgis")
    logger.addHandler(handler)
    if logger.level == logging.NOTSET or logger.level > logging.INFO:
        logger.setLevel(logging.INFO)
    return handler


def remove_log_handler(handler: logging.Handler) -> None:
    logging.getLogger("agricarbon_atlas_qgis").removeHandler(handler)
