# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 CarbonCreditBuy contributors
"""Minimal stand-ins for the parts of PyQGIS that the plugin uses.

QGIS is not installed in CI, so these fakes let the tests import and run the QGIS-dependent
modules (``qgis_helpers``, ``tasks``, ``dialogs``, ``plugin``). They implement only the subset of
the API the plugin calls, with the behaviour documented by the PyQGIS reference. They check the
plugin's own logic (counting, reprojection order, project state, flows); they cannot prove that
the real QGIS behaves identically, so the plugin still needs a manual run in QGIS 3.28+.

``install()`` registers the fake ``qgis`` package in ``sys.modules`` (pure Python for
``qgis.core``; real PyQt5 plus Qt-based fakes for ``qgis.gui`` when ``qt=True``).
"""

from __future__ import annotations

import copy
import math
import sys
import types
from typing import Any

PLUGIN_MODULES = ("qgis_helpers", "tasks", "dialogs", "plugin")


# =========================================================================== qgis.core
class _NullType:
    """PyQGIS's ``NULL``: falsy, and ``float(NULL)`` raises ``TypeError``."""

    def __bool__(self) -> bool:
        return False

    def __float__(self) -> float:
        raise TypeError("float() argument must be a string or a number, not 'QVariant'")

    def __repr__(self) -> str:
        return "NULL"


NULL = _NullType()


class _MessageLevel:
    Info, Warning, Critical, Success = 0, 1, 2, 3


class Qgis:
    MessageLevel = _MessageLevel
    Info, Warning, Critical, Success = 0, 1, 2, 3


class QgsCsException(Exception):
    pass


class QgsPointXY:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self._x, self._y = x, y

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y


class QgsRectangle:
    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
        self.xmin, self.ymin, self.xmax, self.ymax = xmin, ymin, xmax, ymax

    def contains_point(self, x: float, y: float) -> bool:
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def intersects_box(self, xmin: float, ymin: float, xmax: float, ymax: float) -> bool:
        return not (xmax < self.xmin or xmin > self.xmax or ymax < self.ymin or ymin > self.ymax)


class QgsWkbTypes:
    PointGeometry, LineGeometry, PolygonGeometry = 0, 1, 2

    @staticmethod
    def isCurvedType(_wkb_type: Any) -> bool:
        return False


class QgsMapLayerProxyModel:
    PolygonLayer = 1
    PointLayer = 2


class QgsFieldProxyModel:
    Numeric = 1


class QgsGeometry:
    """Polygons, multipolygons and points; enough for centroids and ring access."""

    def __init__(self, other: QgsGeometry | None = None) -> None:
        self.kind: str | None = None
        self.data: Any = None
        if isinstance(other, QgsGeometry):
            self.kind, self.data = other.kind, copy.deepcopy(other.data)

    @staticmethod
    def fromPolygonXY(rings: list[list[QgsPointXY]]) -> QgsGeometry:
        geom = QgsGeometry()
        geom.kind, geom.data = "polygon", [list(ring) for ring in rings]
        return geom

    @staticmethod
    def fromMultiPolygonXY(polygons: list[list[list[QgsPointXY]]]) -> QgsGeometry:
        geom = QgsGeometry()
        geom.kind, geom.data = "multipolygon", [[list(r) for r in poly] for poly in polygons]
        return geom

    @staticmethod
    def fromPointXY(point: QgsPointXY) -> QgsGeometry:
        geom = QgsGeometry()
        geom.kind, geom.data = "point", point
        return geom

    def isNull(self) -> bool:
        return self.kind is None

    def isEmpty(self) -> bool:
        return self.kind is None or not self.data

    def wkbType(self) -> str | None:
        return self.kind

    def convertToStraightSegment(self) -> None:
        return None

    def type(self) -> int:
        return QgsWkbTypes.PointGeometry if self.kind == "point" else QgsWkbTypes.PolygonGeometry

    def isMultipart(self) -> bool:
        return self.kind == "multipolygon"

    def asPolygon(self) -> list[list[QgsPointXY]]:
        return self.data if self.kind == "polygon" else []

    def asMultiPolygon(self) -> list[list[list[QgsPointXY]]]:
        return self.data if self.kind == "multipolygon" else []

    def asPoint(self) -> QgsPointXY:
        return self.data

    def _outer_rings(self) -> list[list[QgsPointXY]]:
        if self.kind == "polygon":
            return [self.data[0]]
        if self.kind == "multipolygon":
            return [poly[0] for poly in self.data]
        return []

    def bbox(self) -> tuple[float, float, float, float]:
        points = (
            [self.data]
            if self.kind == "point"
            else [p for ring in self._outer_rings() for p in ring]
        )
        xs, ys = [p.x() for p in points], [p.y() for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    def centroid(self) -> QgsGeometry:
        if self.kind == "point":
            return QgsGeometry.fromPointXY(self.data)
        if self.isEmpty():
            return QgsGeometry()
        ring = self._outer_rings()[0]
        # Work relative to the first vertex: with map coordinates in the millions, the plain
        # shoelace sums lose all precision (GEOS does the same shift).
        ox, oy = ring[0].x(), ring[0].y()
        shifted = [(p.x() - ox, p.y() - oy) for p in ring]
        area2 = cx = cy = 0.0
        for (ax, ay), (bx, by) in zip(shifted, shifted[1:] + shifted[:1]):
            cross = ax * by - bx * ay
            area2 += cross
            cx += (ax + bx) * cross
            cy += (ay + by) * cross
        if math.isclose(area2, 0.0):
            n = len(ring)
            return QgsGeometry.fromPointXY(
                QgsPointXY(sum(p.x() for p in ring) / n, sum(p.y() for p in ring) / n)
            )
        return QgsGeometry.fromPointXY(QgsPointXY(ox + cx / (3 * area2), oy + cy / (3 * area2)))


class QgsField:
    def __init__(self, name: str, numeric: bool = False) -> None:
        self._name, self._numeric = name, numeric

    def name(self) -> str:
        return self._name

    def isNumeric(self) -> bool:
        return self._numeric


class QgsFields:
    def __init__(self, fields: list[QgsField] | None = None) -> None:
        self._fields = list(fields or [])

    def names(self) -> list[str]:
        return [f.name() for f in self._fields]

    def indexFromName(self, name: str) -> int:
        names = self.names()
        return names.index(name) if name in names else -1

    def __iter__(self) -> Any:
        return iter(self._fields)

    def __len__(self) -> int:
        return len(self._fields)


class QgsFeature:
    def __init__(self, fields: QgsFields | None = None, fid: int = 0) -> None:
        self._fields = fields or QgsFields()
        self._attributes: dict[str, Any] = {}
        self._geometry = QgsGeometry()
        self._id = fid

    def geometry(self) -> QgsGeometry:
        return QgsGeometry(self._geometry)

    def setGeometry(self, geometry: QgsGeometry) -> None:
        self._geometry = geometry

    def setAttributes(self, values: list[Any]) -> None:
        self._attributes = dict(zip(self._fields.names(), values))

    def __getitem__(self, name: str) -> Any:
        if name not in self._fields.names():
            raise KeyError(name)
        return self._attributes.get(name, NULL)

    def id(self) -> int:
        return self._id


class QgsFeatureRequest:
    def __init__(self) -> None:
        self.rect: QgsRectangle | None = None
        self.attributes: list[str] | None = None

    def setFilterRect(self, rect: QgsRectangle) -> QgsFeatureRequest:
        self.rect = rect
        return self

    def setSubsetOfAttributes(self, names: list[str], _fields: QgsFields) -> None:
        self.attributes = list(names)


class QgsCoordinateReferenceSystem:
    def __init__(self, authid: str = "") -> None:
        self._authid = authid

    def isValid(self) -> bool:
        return bool(self._authid)

    def authid(self) -> str:
        return self._authid

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QgsCoordinateReferenceSystem) and other._authid == self._authid

    def __hash__(self) -> int:
        return hash(self._authid)


_EARTH_RADIUS = 6378137.0


def mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    return (
        math.degrees(x / _EARTH_RADIUS),
        math.degrees(math.atan(math.sinh(y / _EARTH_RADIUS))),
    )


def wgs84_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    return (
        math.radians(lon) * _EARTH_RADIUS,
        math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * _EARTH_RADIUS,
    )


class QgsCoordinateTransform:
    """Supports EPSG:3857 <-> EPSG:4326 (what the tests need) and the identity."""

    def __init__(
        self,
        source: QgsCoordinateReferenceSystem,
        target: QgsCoordinateReferenceSystem,
        _context: Any = None,
    ) -> None:
        self._pair = (source.authid(), target.authid())

    def transform(self, point: QgsPointXY) -> QgsPointXY:
        source, target = self._pair
        if source == target:
            return point
        if (source, target) == ("EPSG:3857", "EPSG:4326"):
            return QgsPointXY(*mercator_to_wgs84(point.x(), point.y()))
        if (source, target) == ("EPSG:4326", "EPSG:3857"):
            if abs(point.y()) >= 90:
                raise QgsCsException("latitude out of range")
            return QgsPointXY(*wgs84_to_mercator(point.x(), point.y()))
        raise QgsCsException(f"no transform from {source} to {target}")


class _Provider:
    def __init__(self, layer: QgsVectorLayer) -> None:
        self._layer = layer

    def addFeatures(self, features: list[QgsFeature]) -> tuple[bool, list[QgsFeature]]:
        for feature in features:
            feature._id = len(self._layer._features) + 1
            self._layer._features.append(feature)
        return True, features


class QgsVectorLayer:
    """A memory layer created from a URI such as ``Polygon?crs=EPSG:4326&field=score:double``."""

    _count = 0

    def __init__(self, uri: str = "Polygon", name: str = "", provider: str = "memory") -> None:
        QgsVectorLayer._count += 1
        self._id = f"layer_{QgsVectorLayer._count}"
        self._name = name
        head, _, query = uri.partition("?")
        self._geometry_type = {
            "point": QgsWkbTypes.PointGeometry,
            "linestring": QgsWkbTypes.LineGeometry,
        }.get(head.lower(), QgsWkbTypes.PolygonGeometry)
        authid, fields = "EPSG:4326", []
        for part in filter(None, query.split("&")):
            key, _, value = part.partition("=")
            if key == "crs":
                authid = value
            elif key == "field":
                fname, _, ftype = value.partition(":")
                fields.append(QgsField(fname, ftype.lower() in ("integer", "double", "real")))
        self._crs = QgsCoordinateReferenceSystem(authid)
        self._fields = QgsFields(fields)
        self._features: list[QgsFeature] = []
        self._selected: list[int] = []

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def isValid(self) -> bool:
        return True

    def geometryType(self) -> int:
        return self._geometry_type

    def crs(self) -> QgsCoordinateReferenceSystem:
        return self._crs

    def fields(self) -> QgsFields:
        return self._fields

    def dataProvider(self) -> _Provider:
        return _Provider(self)

    def updateExtents(self) -> None:
        return None

    def getFeatures(self, request: QgsFeatureRequest | None = None) -> Any:
        rect = request.rect if request is not None else None
        for feature in self._features:
            geom = feature.geometry()
            if rect is not None and not geom.isEmpty():
                if geom.kind == "point":
                    p = geom.asPoint()
                    if not rect.contains_point(p.x(), p.y()):
                        continue
                elif not rect.intersects_box(*geom.bbox()):
                    continue
            yield feature

    def selectByIds(self, ids: list[int]) -> None:
        self._selected = list(ids)

    def selectedFeatureCount(self) -> int:
        return len(self._selected)

    def selectedFeatures(self) -> list[QgsFeature]:
        return [f for f in self._features if f.id() in self._selected]

    def _values(self, index: int) -> list[float]:
        name = self._fields.names()[index]
        values = []
        for feature in self._features:
            try:
                values.append(float(feature[name]))
            except (TypeError, ValueError):
                continue
        return values

    def minimumValue(self, index: int) -> Any:
        values = self._values(index)
        return min(values) if values else NULL

    def maximumValue(self, index: int) -> Any:
        values = self._values(index)
        return max(values) if values else NULL


class QgsProject:
    _instance: QgsProject | None = None

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], str] = {}
        self._layers: dict[str, QgsVectorLayer] = {}

    @classmethod
    def instance(cls) -> QgsProject:
        if cls._instance is None:
            cls._instance = QgsProject()
        return cls._instance

    def readEntry(self, scope: str, key: str, default: str = "") -> tuple[str, bool]:
        if (scope, key) in self._entries:
            return self._entries[(scope, key)], True
        return default, False

    def writeEntry(self, scope: str, key: str, value: str) -> bool:
        self._entries[(scope, key)] = value
        return True

    def removeEntry(self, scope: str, key: str) -> bool:
        return self._entries.pop((scope, key), None) is not None

    def mapLayers(self) -> dict[str, QgsVectorLayer]:
        return dict(self._layers)

    def addMapLayer(self, layer: QgsVectorLayer) -> QgsVectorLayer:
        self._layers[layer.id()] = layer
        return layer

    def transformContext(self) -> object:
        return object()


class QgsSettings:
    _store: dict[str, Any] = {}

    def value(self, key: str, default: Any = None, type: Any = None) -> Any:  # noqa: A002
        value = self._store.get(key, default)
        if type is not None and value is not None:
            try:
                return type(value)
            except (TypeError, ValueError):
                # PyQt5 raises TypeError when a stored value cannot be converted to ``type``.
                raise TypeError(f"unable to convert a QVariant to {type.__name__}") from None
        return value

    def setValue(self, key: str, value: Any) -> None:
        self._store[key] = value


class QgsMessageLog:
    messages: list[tuple[str, str, int]] = []

    @staticmethod
    def logMessage(message: str, tag: str = "", level: int = 0, notifyUser: bool = True) -> None:  # noqa: N803
        QgsMessageLog.messages.append((message, tag, level))


class QgsTask:
    """Base class of the plugin's ``ApiTask``. ``Flags()`` is the empty flag set."""

    class Flags:
        def __init__(self, value: int = 0) -> None:
            self.value = value

    def __init__(self, description: str = "", flags: Any = None) -> None:
        self._description = description

    def description(self) -> str:
        return self._description


class _TaskManager:
    """Queues tasks like QGIS does; tests call :meth:`run_all` to execute and finish them."""

    def __init__(self) -> None:
        self.queue: list[Any] = []

    def addTask(self, task: Any) -> int:
        self.queue.append(task)
        return len(self.queue)

    def run_all(self, limit: int = 20) -> int:
        """Run queued tasks (``run`` then ``finished``) until none is left; returns the count."""
        done = 0
        while self.queue and done < limit:
            task = self.queue.pop(0)
            ok = task.run()
            task.finished(bool(ok))
            done += 1
        return done


class QgsApplication:
    _manager = _TaskManager()

    @staticmethod
    def taskManager() -> _TaskManager:
        return QgsApplication._manager


class LayerBuilder:
    """Creates layers and features in the fake QGIS (the layers are registered in the project)."""

    @staticmethod
    def layer(
        name: str,
        kind: str = "Polygon",
        crs: str = "EPSG:4326",
        fields: tuple[str, ...] = (),
        add_to_project: bool = True,
    ) -> QgsVectorLayer:
        uri = f"{kind}?crs={crs}" + "".join(f"&field={f}" for f in fields)
        layer = QgsVectorLayer(uri, name, "memory")
        if add_to_project:
            QgsProject.instance().addMapLayer(layer)
        return layer

    @staticmethod
    def _add(layer: QgsVectorLayer, geometry: QgsGeometry, attributes: list[Any] | None) -> Any:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry)
        if attributes is not None:
            feature.setAttributes(attributes)
        layer.dataProvider().addFeatures([feature])
        return feature

    @staticmethod
    def _points(rings: list[list[tuple[float, float]]]) -> list[list[QgsPointXY]]:
        return [[QgsPointXY(x, y) for x, y in ring] for ring in rings]

    def polygon(
        self, layer: QgsVectorLayer, *rings: list[tuple[float, float]], attributes: Any = None
    ) -> Any:
        return self._add(layer, QgsGeometry.fromPolygonXY(self._points(list(rings))), attributes)

    def multipolygon(
        self, layer: QgsVectorLayer, *polygons: list[list[tuple[float, float]]]
    ) -> Any:
        geometry = QgsGeometry.fromMultiPolygonXY([self._points(list(p)) for p in polygons])
        return self._add(layer, geometry, None)

    def point(self, layer: QgsVectorLayer, x: float, y: float, attributes: Any = None) -> Any:
        return self._add(layer, QgsGeometry.fromPointXY(QgsPointXY(x, y)), attributes)

    def empty(self, layer: QgsVectorLayer, attributes: Any = None) -> Any:
        return self._add(layer, QgsGeometry(), attributes)

    @staticmethod
    def select(layer: QgsVectorLayer, *features: Any) -> None:
        layer.selectByIds([feature.id() for feature in features])


def reset_core_state() -> None:
    QgsProject._instance = None
    QgsSettings._store = {}
    QgsMessageLog.messages = []
    QgsApplication._manager = _TaskManager()
    QgsVectorLayer._count = 0


def _core_module() -> types.ModuleType:
    module = types.ModuleType("qgis.core")
    for name, value in dict(globals()).items():
        if name.startswith("Qgs") or name in ("Qgis", "NULL"):
            setattr(module, name, value)
    return module


# =========================================================================== qgis.gui (Qt)
def _gui_module() -> types.ModuleType:
    """Qt-based fakes of the QGIS widgets the dialogs use (needs PyQt5)."""
    from PyQt5.QtCore import pyqtSignal
    from PyQt5.QtWidgets import QComboBox

    class QgsMapLayerComboBox(QComboBox):
        layerChanged = pyqtSignal(object)

        def __init__(self, parent: Any = None) -> None:
            super().__init__(parent)
            self._filters = 0
            self._allow_empty = False
            self._excepted: list[Any] = []
            self._layers: list[Any] = []
            self.currentIndexChanged.connect(self._emit_layer)

        def setFilters(self, filters: int) -> None:
            self._filters = filters
            self._rebuild()

        def setAllowEmptyLayer(self, allow: bool) -> None:
            self._allow_empty = allow
            self._rebuild()

        def setExceptedLayerList(self, layers: list[Any]) -> None:
            self._excepted = list(layers)
            self._rebuild()

        def _wanted(self, layer: Any) -> bool:
            kind = layer.geometryType()
            wanted = (
                self._filters & QgsMapLayerProxyModel.PolygonLayer
                and kind == QgsWkbTypes.PolygonGeometry
            ) or (
                self._filters & QgsMapLayerProxyModel.PointLayer
                and kind == QgsWkbTypes.PointGeometry
            )
            return bool(wanted) and layer not in self._excepted

        def _rebuild(self) -> None:
            self.blockSignals(True)
            self.clear()
            self._layers = [None] if self._allow_empty else []
            if self._allow_empty:
                self.addItem("")
            for layer in QgsProject.instance().mapLayers().values():
                if self._wanted(layer):
                    self._layers.append(layer)
                    self.addItem(layer.name())
            self.blockSignals(False)

        def _emit_layer(self, _index: int) -> None:
            self.layerChanged.emit(self.currentLayer())

        def setLayer(self, layer: Any) -> None:
            if layer in self._layers:
                self.setCurrentIndex(self._layers.index(layer))

        def currentLayer(self) -> Any:
            index = self.currentIndex()
            return self._layers[index] if 0 <= index < len(self._layers) else None

    class QgsFieldComboBox(QComboBox):
        fieldChanged = pyqtSignal(str)

        def __init__(self, parent: Any = None) -> None:
            super().__init__(parent)
            self._allow_empty = False
            self._numeric_only = False
            self._names: list[str] = []
            self.currentIndexChanged.connect(lambda _i: self.fieldChanged.emit(self.currentField()))

        def setFilters(self, filters: int) -> None:
            self._numeric_only = bool(filters & QgsFieldProxyModel.Numeric)

        def setAllowEmptyFieldName(self, allow: bool) -> None:
            self._allow_empty = allow

        def setLayer(self, layer: Any) -> None:
            self.blockSignals(True)
            self.clear()
            self._names = [""] if self._allow_empty else []
            if self._allow_empty:
                self.addItem("")
            if layer is not None:
                for field in layer.fields():
                    if field.isNumeric() or not self._numeric_only:
                        self._names.append(field.name())
                        self.addItem(field.name())
            self.blockSignals(False)
            self.fieldChanged.emit(self.currentField())

        def setField(self, name: str) -> None:
            if name in self._names:
                self.setCurrentIndex(self._names.index(name))

        def currentField(self) -> str:
            index = self.currentIndex()
            return self._names[index] if 0 <= index < len(self._names) else ""

    class QgsMessageBar:
        """Records the messages pushed by the plugin."""

        def __init__(self) -> None:
            self.messages: list[tuple[str, str, int, int]] = []

        def pushMessage(self, title: str, text: str, level: int = 0, duration: int = -1) -> None:
            self.messages.append((title, text, level, duration))

    module = types.ModuleType("qgis.gui")
    module.QgsMapLayerComboBox = QgsMapLayerComboBox  # type: ignore[attr-defined]
    module.QgsFieldComboBox = QgsFieldComboBox  # type: ignore[attr-defined]
    module.QgsMessageBar = QgsMessageBar  # type: ignore[attr-defined]
    return module


def make_iface() -> Any:
    """A fake ``QgisInterface`` backed by a real (offscreen) ``QMainWindow``."""
    from PyQt5.QtWidgets import QMainWindow

    gui = sys.modules["qgis.gui"]

    class FakeIface:
        def __init__(self) -> None:
            self.window = QMainWindow()
            self.bar = gui.QgsMessageBar()
            self.menu_actions: dict[str, list[Any]] = {}
            self.active_layer: Any = None

        def addToolBar(self, name: str) -> Any:  # noqa: N802
            return self.window.addToolBar(name)

        def mainWindow(self) -> Any:  # noqa: N802
            return self.window

        def addPluginToMenu(self, menu: str, action: Any) -> None:  # noqa: N802
            self.menu_actions.setdefault(menu, []).append(action)

        def removePluginMenu(self, menu: str, action: Any) -> None:  # noqa: N802
            self.menu_actions[menu].remove(action)
            if not self.menu_actions[menu]:
                del self.menu_actions[menu]

        def messageBar(self) -> Any:  # noqa: N802
            return self.bar

        def activeLayer(self) -> Any:  # noqa: N802
            return self.active_layer

    return FakeIface()


# =========================================================================== installation
def forget_plugin_modules() -> None:
    """Drop the QGIS-dependent plugin modules so the next import binds to the current fakes.

    ``from . import qgis_helpers`` consults the attribute on the package before ``sys.modules``,
    so the package attribute has to go as well.
    """
    package = sys.modules.get("carboncreditbuy_qgis")
    for name in PLUGIN_MODULES:
        sys.modules.pop(f"carboncreditbuy_qgis.{name}", None)
        if package is not None and hasattr(package, name):
            delattr(package, name)


def install(monkeypatch: Any, qt: bool = False) -> types.ModuleType:
    """Register the fake ``qgis`` package; returns the fake ``qgis.core`` module.

    The ``fake_qgis`` fixtures in ``conftest.py`` call this and run :func:`forget_plugin_modules`
    again after the test, so every test imports the plugin modules fresh against the fakes and
    nothing leaks into other tests (``monkeypatch`` undoes the ``qgis`` registration itself).
    """
    reset_core_state()
    forget_plugin_modules()

    core = _core_module()
    package = types.ModuleType("qgis")
    package.__path__ = []  # type: ignore[attr-defined]
    package.core = core  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "qgis", package)
    monkeypatch.setitem(sys.modules, "qgis.core", core)
    if qt:
        import PyQt5.QtCore
        import PyQt5.QtGui
        import PyQt5.QtWidgets

        pyqt = types.ModuleType("qgis.PyQt")
        pyqt.__path__ = []  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "qgis.PyQt", pyqt)
        monkeypatch.setitem(sys.modules, "qgis.PyQt.QtCore", PyQt5.QtCore)
        monkeypatch.setitem(sys.modules, "qgis.PyQt.QtGui", PyQt5.QtGui)
        monkeypatch.setitem(sys.modules, "qgis.PyQt.QtWidgets", PyQt5.QtWidgets)
        gui = _gui_module()
        package.gui = gui  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "qgis.gui", gui)
    return core
