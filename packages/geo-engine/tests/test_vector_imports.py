"""GeoJSON / KML / KMZ / CSV imports: parsing, classification, counting (geo_engine.imports)."""

from __future__ import annotations

import io
import json
import math
import time
import zipfile

import numpy as np
import pytest
from shapely.geometry import Polygon, shape

from geo_engine.construct import geodesic_area_m2
from geo_engine.geometry import ValidationLimits
from geo_engine.imports import (
    MAX_ARCHIVE_ENTRIES,
    MAX_FEATURES,
    ImportDataError,
    UnsupportedFormatError,
    VectorImportParams,
    count_inside,
    describe_import,
    height_stats,
    parse_vector,
)

PLOT = Polygon(
    [
        (77.5370, 13.2910),
        (77.5400, 13.2910),
        (77.5400, 13.2940),
        (77.5370, 13.2940),
        (77.5370, 13.2910),
    ]
)  # about 10.8 ha
M_PER_DEG_LAT = 110_600.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(13.29))


# ---------------------------------------------------------------------------- builders
def square_ring(lon: float, lat: float, side_m: float) -> list[list[float]]:
    dx = side_m / 2 / M_PER_DEG_LON
    dy = side_m / 2 / M_PER_DEG_LAT
    return [
        [lon - dx, lat - dy],
        [lon + dx, lat - dy],
        [lon + dx, lat + dy],
        [lon - dx, lat + dy],
        [lon - dx, lat - dy],
    ]


def poly_feature(ring: list[list[float]], **props) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def point_feature(lon: float, lat: float, **props) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def collection(*features: dict, **extra) -> bytes:
    return json.dumps({"type": "FeatureCollection", "features": list(features), **extra}).encode()


def crowns(count: int, scores: list[float] | None = None, side_m: float = 4.0) -> list[dict]:
    """Small square crowns on a 10 m grid inside PLOT, optionally with scores."""
    out = []
    columns = 20
    for i in range(count):
        lon = 77.5372 + (i % columns) * 10 / M_PER_DEG_LON
        lat = 13.2912 + (i // columns) * 10 / M_PER_DEG_LAT
        props = {} if scores is None else {"score": scores[i]}
        out.append(poly_feature(square_ring(lon, lat, side_m), **props))
    return out


def kml_polygon(ring: list[list[float]], name: str = "Field 7") -> str:
    coords = " ".join(f"{lon},{lat},0" for lon, lat in ring)
    return (
        '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2">'
        f"<Document><name>Doc</name><Placemark><name>{name}</name><Polygon><outerBoundaryIs>"
        f"<LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon>"
        "</Placemark></Document></kml>"
    )


def kml_points(count: int) -> str:
    marks = "".join(
        f"<Placemark><name>T{i}</name><Point><coordinates>{77.5372 + i * 1e-5},13.2915,0"
        "</coordinates></Point></Placemark>"
        for i in range(count)
    )
    return f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>{marks}</Document></kml>'


def make_kmz(entries: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


PLOT_RING = [list(c) for c in PLOT.exterior.coords]


# ---------------------------------------------------------------------------- boundaries
def test_geojson_boundary_has_area_and_name():
    data = collection(poly_feature(PLOT_RING, name="Field 7"))
    vector = parse_vector("field.geojson", data)
    assert vector.kind == "boundary" and vector.format == "geojson"
    assert vector.boundary is not None and vector.boundary_polygon is not None
    assert vector.boundary["name"] == "Field 7"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )
    assert vector.boundary["geometry"]["type"] == "Polygon"
    assert (vector.feature_count, vector.polygon_count, vector.point_count) == (1, 1, 0)
    assert vector.trees is None


@pytest.mark.parametrize("filename", ["a.json", "A.GEOJSON", "dir/sub\\field.geojson"])
def test_extension_variants_and_paths(filename):
    assert parse_vector(filename, collection(poly_feature(PLOT_RING))).kind == "boundary"


def test_bare_geometry_and_single_feature_are_accepted():
    geometry = {"type": "Polygon", "coordinates": [PLOT_RING]}
    assert parse_vector("a.geojson", json.dumps(geometry).encode()).kind == "boundary"
    feature = poly_feature(PLOT_RING, name="Solo")
    vector = parse_vector("a.geojson", json.dumps(feature).encode())
    assert vector.boundary and vector.boundary["name"] == "Solo"


def test_utf8_bom_is_accepted():
    data = b"\xef\xbb\xbf" + collection(poly_feature(PLOT_RING))
    assert parse_vector("a.geojson", data).kind == "boundary"


def test_multipolygon_parts_are_read_as_polygons():
    other = square_ring(77.5390, 13.2930, 60.0)
    multi = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "MultiPolygon", "coordinates": [[PLOT_RING], [other]]},
    }
    vector = parse_vector("a.geojson", json.dumps(multi).encode())
    assert vector.polygon_count == 2
    assert vector.kind == "boundary"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )  # the larger part


def test_several_large_polygons_use_the_largest_and_warn():
    big = square_ring(77.5385, 13.2925, 200.0)
    small = square_ring(77.5390, 13.2930, 100.0)
    vector = parse_vector("a.geojson", collection(poly_feature(small), poly_feature(big)))
    assert vector.kind == "boundary"
    assert vector.boundary["area_hectares"] == pytest.approx(4.0, rel=0.02)
    assert any("largest" in w for w in vector.warnings)


def test_boundary_purpose_beats_the_crown_heuristic():
    # a field outline plus a dozen small polygons (ponds, buildings): the median says "crowns"
    data = collection(poly_feature(PLOT_RING), *crowns(12))
    auto = parse_vector("a.geojson", data)
    assert auto.kind == "tree-crowns"
    assert any("much larger" in w for w in auto.warnings)
    forced = parse_vector("a.geojson", data, purpose="boundary")
    assert forced.kind == "boundary"
    assert forced.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )


def test_boundary_purpose_on_crowns_explains_the_problem():
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", collection(*crowns(12)), purpose="boundary")
    assert caught.value.code == "invalid_boundary"
    assert "trees" in caught.value.detail


def test_boundary_below_the_minimum_area_is_rejected_with_a_hint():
    data = collection(poly_feature(square_ring(77.538, 13.292, 20.0)))  # 0.04 ha...
    tiny = collection(poly_feature(square_ring(77.538, 13.292, 5.0)))  # 0.0025 ha
    assert parse_vector("a.geojson", data).kind == "boundary"
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", tiny)
    assert caught.value.code == "invalid_boundary"
    assert "trees" in caught.value.detail


def test_a_self_intersecting_boundary_is_rejected():
    bow_tie = [
        [77.537, 13.291],
        [77.540, 13.294],
        [77.540, 13.291],
        [77.537, 13.294],
        [77.537, 13.291],
    ]
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", collection(poly_feature(bow_tie)))
    assert caught.value.code == "invalid_boundary"
    assert "self-intersection" in caught.value.detail


def test_a_boundary_with_too_many_vertices_is_simplified_with_a_warning():
    angles = np.linspace(0, 2 * math.pi, 801)[:-1]
    ring = [[77.538 + 0.0008 * math.cos(a), 13.292 + 0.0008 * math.sin(a)] for a in angles]
    ring.append(ring[0])
    vector = parse_vector(
        "a.geojson",
        collection(poly_feature(ring)),
        limits=ValidationLimits(max_vertices=500),
    )
    assert vector.kind == "boundary"
    assert len(vector.boundary["geometry"]["coordinates"][0]) - 1 <= 500
    assert any("simplified" in w for w in vector.warnings)


# ---------------------------------------------------------------------------- crowns
def test_crowns_with_scores_are_filtered_by_confidence():
    scores = [0.9 if i % 3 else 0.3 for i in range(30)]
    vector = parse_vector("crowns.geojson", collection(*crowns(30, scores)))
    assert vector.kind == "tree-crowns"
    trees = vector.trees
    assert trees is not None
    assert trees.total_in_file == 30
    assert len(trees) == sum(1 for s in scores if s >= 0.5) == 20
    assert trees.confidence_field == "score" and trees.min_confidence == 0.5
    assert "0.5" in trees.method and "centroid" in trees.method
    stricter = parse_vector("crowns.geojson", collection(*crowns(30, scores)), min_confidence=0.95)
    assert len(stricter.trees) == 0  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["score", "Confidence", "PROB", "probability"])
def test_confidence_field_names(field):
    features = crowns(12)
    for i, feature in enumerate(features):
        feature["properties"][field] = 0.2 if i < 4 else 0.8
    vector = parse_vector("a.geojson", collection(*features))
    assert len(vector.trees) == 8  # type: ignore[arg-type]
    assert vector.trees.confidence_field == field  # type: ignore[union-attr]


def test_scores_in_percent_are_read_with_a_warning():
    features = crowns(12)
    for i, feature in enumerate(features):
        feature["properties"]["score"] = 30 if i < 5 else 90
    vector = parse_vector("a.geojson", collection(*features))
    assert len(vector.trees) == 7  # type: ignore[arg-type]
    assert any("percent" in w for w in vector.warnings)


def test_scores_outside_any_scale_disable_the_filter_with_a_warning():
    features = crowns(12)
    for i, feature in enumerate(features):
        feature["properties"]["score"] = 500 + i
    vector = parse_vector("a.geojson", collection(*features))
    assert len(vector.trees) == 12  # type: ignore[arg-type]
    assert any("no confidence filter" in w for w in vector.warnings)


def test_features_without_a_score_are_kept_with_a_warning():
    features = crowns(12)
    for i, feature in enumerate(features[:6]):
        feature["properties"]["score"] = 0.2 if i < 3 else 0.9
    vector = parse_vector("a.geojson", collection(*features))
    assert (
        len(vector.trees) == 9
    )  # 3 low dropped; 3 high + 6 unscored kept  # type: ignore[arg-type]
    assert any("no 'score' value" in w for w in vector.warnings)


def test_ten_small_polygons_are_crowns_even_when_above_the_median_rule():
    vector = parse_vector("a.geojson", collection(*crowns(10, side_m=20.0)))  # 400 m2 each
    assert vector.kind == "tree-crowns"
    assert "all smaller than" in vector.trees.method  # type: ignore[union-attr]
    nine = parse_vector("a.geojson", collection(*crowns(9, side_m=20.0)))
    assert nine.kind == "boundary"  # fewer than ten and not below the median rule


def test_a_few_small_polygons_next_to_a_field_outline_stay_a_boundary():
    pond = poly_feature(square_ring(77.5385, 13.2925, 10.0))
    building = poly_feature(square_ring(77.5390, 13.2930, 10.0))
    vector = parse_vector("a.geojson", collection(poly_feature(PLOT_RING), pond, building))
    assert vector.kind == "boundary"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )
    assert any("largest" in w for w in vector.warnings)


def test_many_small_polygons_next_to_a_field_outline_are_crowns_with_a_warning():
    vector = parse_vector("a.geojson", collection(poly_feature(PLOT_RING), *crowns(12)))
    assert vector.kind == "tree-crowns"
    assert vector.trees.total_in_file == 13  # type: ignore[union-attr]
    assert any("much larger" in w for w in vector.warnings)


def test_trees_purpose_forces_crowns_for_a_few_polygons():
    vector = parse_vector("a.geojson", collection(*crowns(5)), purpose="trees")
    assert vector.kind == "tree-crowns"
    assert len(vector.trees) == 5  # type: ignore[arg-type]


def test_crown_positions_are_centroids():
    vector = parse_vector("a.geojson", collection(*crowns(12)))
    first = vector.trees
    assert first is not None
    expected = shape(crowns(12)[0]["geometry"]).centroid
    assert (first.xs[0], first.ys[0]) == pytest.approx((expected.x, expected.y), abs=1e-9)


def test_crown_heights_are_read_from_a_height_field():
    features = crowns(12)
    for i, feature in enumerate(features):
        feature["properties"]["height_m"] = 4.0 + i
    vector = parse_vector("a.geojson", collection(*features))
    stats = describe_import(vector, PLOT)["trees"]
    assert stats["mean_height_m"] == pytest.approx(9.5)
    assert stats["median_height_m"] == pytest.approx(9.5)
    assert stats["p90_height_m"] == pytest.approx(np.percentile(np.arange(4, 16), 90), abs=0.01)


# ---------------------------------------------------------------------------- tree points
def test_points_with_confidence_and_height():
    features = [
        point_feature(77.5372 + i * 1e-5, 13.2915, confidence=0.9 if i % 2 else 0.4, height=5.0 + i)
        for i in range(60)
    ]
    vector = parse_vector("trees.geojson", collection(*features))
    assert vector.kind == "tree-points"
    assert len(vector.trees) == 30  # type: ignore[arg-type]
    described = describe_import(vector, PLOT)
    assert described["trees"]["count"] == 30
    assert described["trees"]["count_in_plot"] == 30
    assert described["trees"]["mean_height_m"] is not None
    assert described["trees"]["canopy_cover_fraction"] is None  # points have no crown area


def test_points_that_are_few_without_attributes_are_read_as_corners():
    ring = PLOT_RING[:-1]
    features = [point_feature(lon, lat) for lon, lat in ring]
    vector = parse_vector("corners.geojson", collection(*features))
    assert vector.kind == "boundary"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )
    assert any("corners" in w for w in vector.warnings)


def test_trees_purpose_overrides_the_corner_reading():
    ring = PLOT_RING[:-1]
    features = [point_feature(lon, lat) for lon, lat in ring]
    vector = parse_vector("corners.geojson", collection(*features), purpose="trees")
    assert vector.kind == "tree-points" and len(vector.trees) == 4  # type: ignore[arg-type]


def test_boundary_purpose_with_collinear_points_explains_itself():
    features = [point_feature(77.537 + i * 1e-4, 13.291) for i in range(5)]
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", collection(*features), purpose="boundary")
    assert caught.value.code in {"invalid_boundary", "no_boundary"}


def test_more_than_fifty_points_are_trees():
    features = [point_feature(77.5372 + i * 1e-5, 13.2915) for i in range(60)]
    assert parse_vector("a.geojson", collection(*features)).kind == "tree-points"


def test_mixed_polygons_and_points_warn_about_what_was_ignored():
    features = [
        poly_feature(PLOT_RING),
        *[point_feature(77.538, 13.292 + i * 1e-5) for i in range(3)],
    ]
    vector = parse_vector("a.geojson", collection(*features))
    assert vector.kind == "boundary"
    assert any("point feature(s)" in w and "ignored" in w for w in vector.warnings)


def test_lines_are_skipped_with_a_warning_and_only_lines_is_an_error():
    line = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "LineString", "coordinates": [[77.5, 13.2], [77.6, 13.3]]},
    }
    vector = parse_vector("a.geojson", collection(poly_feature(PLOT_RING), line))
    assert vector.kind == "boundary" and vector.feature_count == 1
    assert any("line" in w.lower() for w in vector.warnings)
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", collection(line))
    assert caught.value.code == "no_features"


# ---------------------------------------------------------------------------- bad GeoJSON
@pytest.mark.parametrize(
    "payload, code",
    [
        (b"not json at all", "invalid_content"),
        (b"[1, 2, 3]", "invalid_content"),
        (b'{"type": "Banana"}', "invalid_content"),
        (b'{"type": "FeatureCollection", "features": "x"}', "invalid_content"),
        (b'{"type": "FeatureCollection", "features": []}', "no_features"),
        (b"\xff\xfe\x00\x00 not utf8", "invalid_content"),
    ],
)
def test_malformed_geojson_gives_a_stable_code(payload, code):
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", payload)
    assert caught.value.code == code


def test_non_wgs84_crs_is_refused():
    data = collection(
        poly_feature(PLOT_RING),
        crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32643"}},
    )
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", data)
    assert caught.value.code == "unsupported_crs"
    for name in ("urn:ogc:def:crs:OGC:1.3:CRS84", "EPSG:4326", "urn:ogc:def:crs:EPSG::4326"):
        ok = collection(poly_feature(PLOT_RING), crs={"type": "name", "properties": {"name": name}})
        assert parse_vector("a.geojson", ok).kind == "boundary"


def test_out_of_range_coordinates_are_rejected_without_echoing_them():
    bad = [[77.5, 13.2], [987.654321, 13.2], [77.6, 13.3], [77.5, 13.2]]
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", collection(poly_feature(bad)))
    assert caught.value.code == "coordinate_out_of_range"
    assert "987.654321" not in caught.value.detail


def test_feature_limit_is_enforced():
    features = [
        point_feature(77.5 + (i % 100) * 1e-5, 13.2 + (i // 100) * 1e-5)
        for i in range(MAX_FEATURES + 1)
    ]
    with pytest.raises(ImportDataError) as caught:
        parse_vector("big.geojson", collection(*features))
    assert caught.value.code == "too_many_features"
    ok = parse_vector("big.geojson", collection(*features[:MAX_FEATURES]))
    assert ok.kind == "tree-points" and ok.point_count == MAX_FEATURES


def test_unsupported_and_empty_files():
    with pytest.raises(UnsupportedFormatError):
        parse_vector("a.shp", b"x")
    with pytest.raises(UnsupportedFormatError):
        parse_vector("scan.laz", b"x")  # point clouds have their own entry point
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.geojson", b"   \n")
    assert caught.value.code == "empty_file"
    with pytest.raises(ImportDataError):
        parse_vector("a.geojson", collection(poly_feature(PLOT_RING)), purpose="nonsense")
    with pytest.raises(ImportDataError):
        parse_vector("a.geojson", collection(poly_feature(PLOT_RING)), min_confidence=2.0)


# ---------------------------------------------------------------------------- KML
def test_kml_boundary_name_and_area():
    vector = parse_vector("field.kml", kml_polygon(PLOT_RING).encode())
    assert vector.kind == "boundary" and vector.format == "kml"
    assert vector.boundary["name"] == "Field 7"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )


def test_kml_points_are_trees():
    vector = parse_vector("trees.kml", kml_points(80).encode())
    assert vector.kind == "tree-points" and len(vector.trees) == 80  # type: ignore[arg-type]


def test_kml_extended_data_numbers_are_read():
    marks = "".join(
        "<Placemark><ExtendedData><Data name='score'><value>"
        f"{0.9 if i % 2 else 0.1}</value></Data></ExtendedData><Point><coordinates>"
        f"{77.5372 + i * 1e-5},13.2915,0</coordinates></Point></Placemark>"
        for i in range(60)
    )
    kml = f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>{marks}</Document></kml>'
    vector = parse_vector("a.kml", kml.encode())
    assert len(vector.trees) == 30  # type: ignore[arg-type]


def test_kml_with_folders_multigeometry_and_bom():
    inner = (
        "<Folder><Placemark><MultiGeometry><Polygon><outerBoundaryIs><LinearRing><coordinates>"
        + " ".join(f"{a},{b},0" for a, b in PLOT_RING)
        + "</coordinates></LinearRing></outerBoundaryIs></Polygon>"
        + "</MultiGeometry></Placemark></Folder>"
    )
    kml = f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document>{inner}</Document></kml>'
    vector = parse_vector("a.kml", b"\xef\xbb\xbf" + kml.encode())
    assert vector.kind == "boundary"


XXE = (
    '<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>&xxe;</name></Document></kml>'
)
BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
    '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">'
    '<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">'
    '<!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">'
    '<!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">'
    '<!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">'
    '<!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">'
    '<!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">]>'
    '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>&lol9;</name></Document></kml>'
)
QUADRATIC_BLOWUP = (
    '<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY a "' + "a" * 5000 + '">]>'
    '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>'
    + "&a;" * 5000
    + "</name></Document></kml>"
)
EXTERNAL_DTD = (
    '<?xml version="1.0"?><!DOCTYPE kml SYSTEM "http://127.0.0.1:9/evil.dtd">'
    '<kml xmlns="http://www.opengis.net/kml/2.2"><Document/></kml>'
)


@pytest.mark.parametrize("payload", [XXE, BILLION_LAUGHS, QUADRATIC_BLOWUP, EXTERNAL_DTD])
def test_hostile_xml_is_rejected_fast_and_without_expanding(payload):
    started = time.perf_counter()
    with pytest.raises(ImportDataError) as caught:
        parse_vector("evil.kml", payload.encode())
    assert caught.value.code == "unsafe_xml"
    assert "root:" not in caught.value.detail and "lol" not in caught.value.detail
    assert time.perf_counter() - started < 2.0


def test_hostile_xml_inside_a_kmz_is_rejected_too():
    with pytest.raises(ImportDataError) as caught:
        parse_vector("evil.kmz", make_kmz({"doc.kml": BILLION_LAUGHS}))
    assert caught.value.code == "unsafe_xml"


def test_a_missing_xml_backend_is_reported_not_guessed(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "defusedxml", None)  # as if the package were not installed
    for name, data in (("a.kml", b"<kml/>"), ("a.kmz", make_kmz({"doc.kml": b"<kml/>"}))):
        with pytest.raises(UnsupportedFormatError) as caught:
            parse_vector(name, data)
        assert caught.value.code == "xml_backend_missing"
        assert "defusedxml" in caught.value.detail and "GeoJSON" in caught.value.detail
    assert parse_vector("a.geojson", json.dumps(PLOT.__geo_interface__).encode()).kind == "boundary"


@pytest.mark.parametrize(
    "payload, code",
    [
        (b"<kml><Document>", "invalid_content"),
        (b"<html><body>hi</body></html>", "invalid_content"),
        (b"plain text", "invalid_content"),
    ],
)
def test_malformed_kml(payload, code):
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.kml", payload)
    assert caught.value.code == code


# ---------------------------------------------------------------------------- KMZ
def test_kmz_with_doc_kml():
    data = make_kmz({"doc.kml": kml_polygon(PLOT_RING), "images/icon.png": b"\x89PNG"})
    vector = parse_vector("field.kmz", data)
    assert vector.kind == "boundary" and vector.format == "kmz"


def test_kmz_picks_doc_kml_over_other_kml_files():
    data = make_kmz({"other.kml": kml_points(70), "files/doc.kml": kml_polygon(PLOT_RING)})
    assert parse_vector("a.kmz", data).kind == "boundary"
    only_other = make_kmz({"layer.kml": kml_polygon(PLOT_RING)})
    assert parse_vector("a.kmz", only_other).kind == "boundary"


def test_kmz_zip_bomb_is_refused_by_declared_size():
    zeros = b"\0" * (20 * 1024 * 1024)
    bomb = make_kmz(
        {"doc.kml": kml_polygon(PLOT_RING), "a.bin": zeros, "b.bin": zeros, "c.bin": zeros}
    )
    assert len(bomb) < 1024 * 1024  # a small download that expands to 60 MB
    with pytest.raises(ImportDataError) as caught:
        parse_vector("bomb.kmz", bomb)
    assert caught.value.code == "archive_too_large"


def test_kmz_with_too_many_entries_is_refused():
    entries = {f"f{i}.txt": b"x" for i in range(MAX_ARCHIVE_ENTRIES + 1)}
    entries["doc.kml"] = kml_polygon(PLOT_RING)
    with pytest.raises(ImportDataError) as caught:
        parse_vector("many.kmz", make_kmz(entries))
    assert caught.value.code == "archive_too_many_entries"


def test_kmz_errors():
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.kmz", b"this is not a zip")
    assert caught.value.code == "bad_archive"
    with pytest.raises(ImportDataError) as caught:
        parse_vector("a.kmz", make_kmz({"readme.txt": "no kml here"}))
    assert caught.value.code == "invalid_content"
    truncated = make_kmz({"doc.kml": kml_polygon(PLOT_RING)})[:-30]
    with pytest.raises(ImportDataError):
        parse_vector("a.kmz", truncated)


# ---------------------------------------------------------------------------- CSV
def lat_lon_rows(count: int, delimiter: str = ",") -> list[str]:
    return [f"{13.2915 + i * 1e-5:.5f}{delimiter}77.5372" for i in range(count)]


@pytest.mark.parametrize(
    "header, delimiter",
    [
        ("lat,lon", ","),
        ("Latitude,Longitude", ","),
        ("LAT,LNG", ","),
        ("latitude;longitude", ";"),
        ("lat\tlon", "\t"),
    ],
)
def test_csv_header_names_and_delimiters(header, delimiter):
    rows = [header, *lat_lon_rows(60, delimiter)]
    vector = parse_vector("pts.csv", "\n".join(rows).encode())
    assert vector.kind == "tree-points" and vector.point_count == 60
    assert vector.trees.ys[0] == pytest.approx(13.2915)  # type: ignore[union-attr]


def test_csv_x_y_header_means_lon_lat_when_values_say_so():
    rows = ["x,y", *[f"{77.5372 + i * 1e-5},13.2915" for i in range(60)]]
    vector = parse_vector("pts.csv", "\n".join(rows).encode())
    assert vector.point_count == 60
    assert vector.trees.xs[0] == pytest.approx(77.5372)  # type: ignore[union-attr]


def test_csv_corner_list_is_a_boundary():
    rows = ["name,lat,lon", *[f"C{i},{lat},{lon}" for i, (lon, lat) in enumerate(PLOT_RING[:-1])]]
    vector = parse_vector("corners.csv", "\n".join(rows).encode())
    assert vector.kind == "boundary"
    assert vector.boundary["area_hectares"] == pytest.approx(
        geodesic_area_m2(PLOT) / 10_000, rel=1e-3
    )


def test_csv_numeric_columns_become_properties():
    rows = [
        "lat,lon,height_m,score",
        *[f"{13.2915 + i * 1e-5},77.5372,{3 + i % 5},{0.2 + (i % 8) / 10}" for i in range(60)],
    ]
    vector = parse_vector("pts.csv", "\n".join(rows).encode())
    assert vector.kind == "tree-points"
    assert vector.trees.confidence_field == "score"  # type: ignore[union-attr]
    assert vector.trees.height_m is not None  # type: ignore[union-attr]
    assert len(vector.trees) < 60  # type: ignore[arg-type]


def test_csv_decimal_comma_semicolon_and_encodings():
    rows = ["lat;lon", *[f"13,{2915 + i};77,5372" for i in range(60)]]
    text = "\n".join(rows)
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "cp1252"):
        vector = parse_vector("pts.csv", text.encode(encoding))
        assert vector.point_count == 60, encoding
        assert vector.trees.ys[0] == pytest.approx(13.2915)  # type: ignore[union-attr]


def test_csv_headerless_rows():
    rows = [f"{13.2915 + i * 1e-5}, 77.5372" for i in range(60)]
    vector = parse_vector("pts.csv", "\n".join(rows).encode())
    assert vector.point_count == 60


def test_csv_bad_rows_are_skipped_with_line_numbers_and_never_echoed():
    rows = [
        "lat,lon",
        "13.2915,77.5372",
        "abc,def",
        "13.2916,77.5373",
        "999.5,77.5",
        *[f"13.292,77.5{i}" for i in range(10, 70)],
    ]
    vector = parse_vector("pts.csv", "\n".join(rows).encode())
    joined = " ".join(vector.warnings)
    assert "3" in joined and "5" in joined  # line numbers
    assert "999.5" not in joined and "abc" not in joined


def test_csv_errors():
    with pytest.raises(ImportDataError) as binary:
        parse_vector("a.csv", b"\x00\x01\x02binary\x00\x00")
    assert binary.value.code == "invalid_content"
    with pytest.raises(ImportDataError) as empty:
        parse_vector("a.csv", b"\n\n")
    assert empty.value.code == "empty_file"
    with pytest.raises(ImportDataError) as none:
        parse_vector("a.csv", b"name,colour\nA,red\nB,blue\n")
    assert none.value.code == "no_coordinates"
    rows = [
        "lat,lon",
        *[
            f"{13.0 + (i % 1000) * 1e-5},{77.0 + (i // 1000) * 1e-5}"
            for i in range(MAX_FEATURES + 1)
        ],
    ]
    with pytest.raises(ImportDataError) as many:
        parse_vector("a.csv", "\n".join(rows).encode())
    assert many.value.code == "too_many_features"


# ---------------------------------------------------------------------------- counting
def test_count_inside_includes_the_edge_and_handles_empty_input():
    xs = np.array([77.5385, 77.5370, 77.5500, 77.5385])
    ys = np.array([13.2925, 13.2925, 13.2925, 13.3000])
    assert count_inside(PLOT, xs, ys).tolist() == [True, True, False, False]
    assert count_inside(PLOT, np.array([]), np.array([])).size == 0


def test_height_stats():
    assert height_stats(None) == {
        "mean_height_m": None,
        "median_height_m": None,
        "p90_height_m": None,
    }
    assert height_stats(np.array([np.nan]))["mean_height_m"] is None
    stats = height_stats(np.array([2.0, 4.0, 6.0, np.nan]))
    assert stats["mean_height_m"] == 4.0 and stats["median_height_m"] == 4.0
    assert stats["p90_height_m"] == pytest.approx(5.6)


def test_describe_import_counts_trees_inside_the_plot():
    inside = crowns(12)
    outside = [poly_feature(square_ring(77.60, 13.30, 4.0)) for _ in range(4)]
    vector = parse_vector("a.geojson", collection(*inside, *outside))
    described = describe_import(vector, PLOT)
    assert described["trees"]["count"] == 16
    assert described["trees"]["count_in_plot"] == 12
    assert described["summary"] == {
        "feature_count": 16,
        "polygon_count": 16,
        "point_count": 0,
        "georeferenced": True,
        "crs": "EPSG:4326",
    }
    flags = [f["properties"]["in_plot"] for f in described["preview"]["features"]]
    assert flags.count(True) == 12 and flags.count(False) == 4
    without_plot = describe_import(vector)
    assert without_plot["trees"]["count_in_plot"] is None
    assert without_plot["trees"]["canopy_cover_fraction"] is None


def test_canopy_cover_is_the_union_of_crowns_over_the_plot_area():
    vector = parse_vector("a.geojson", collection(*crowns(12, side_m=10.0)))
    described = describe_import(vector, PLOT)
    plot_m2 = geodesic_area_m2(PLOT)
    assert described["trees"]["canopy_cover_fraction"] == pytest.approx(
        12 * 100.0 / plot_m2, rel=0.05
    )
    # overlapping crowns count once
    doubled = parse_vector(
        "a.geojson", collection(*crowns(12, side_m=10.0), *crowns(12, side_m=10.0))
    )
    again = describe_import(doubled, PLOT)
    assert again["trees"]["canopy_cover_fraction"] == pytest.approx(
        described["trees"]["canopy_cover_fraction"], rel=0.01
    )


def test_boundary_preview_is_the_boundary_feature():
    vector = parse_vector("a.geojson", collection(poly_feature(PLOT_RING, name="Field 7")))
    preview = describe_import(vector)["preview"]
    assert len(preview["features"]) == 1
    assert preview["features"][0]["properties"] == {"role": "boundary", "name": "Field 7"}


def test_preview_is_capped_and_deterministic():
    features = [
        point_feature(77.5 + (i % 100) * 1e-5, 13.2 + (i // 100) * 1e-5) for i in range(6000)
    ]
    vector = parse_vector("a.geojson", collection(*features))
    first = describe_import(vector, PLOT)
    second = describe_import(vector, PLOT)
    assert len(first["preview"]["features"]) == 5000
    assert first["preview"] == second["preview"]
    assert any("5000 of 6000" in w for w in first["warnings"])
    small = describe_import(vector, PLOT, preview_limit=100)
    assert len(small["preview"]["features"]) <= 100


def test_parameters_come_from_the_config_file():
    params = VectorImportParams.from_config()
    assert params.default_min_confidence == 0.5
    assert params.crown_median_area_m2 == 200.0
    assert params.to_dict()["corner_points_max"] == 50


def test_import_errors_are_value_errors_with_a_code_and_a_detail():
    error = ImportDataError("some_code", "something specific")
    assert isinstance(error, ValueError)
    assert (error.code, error.detail, str(error)) == (
        "some_code",
        "something specific",
        "something specific",
    )
    unsupported = UnsupportedFormatError("nope")
    assert unsupported.code == "unsupported_format" and isinstance(unsupported, ImportDataError)
