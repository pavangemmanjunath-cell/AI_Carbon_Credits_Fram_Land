"""Import endpoints: GeoJSON, KML, KMZ, CSV, LAS and LAZ become a derived record (not stored)."""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape

from app.core.config import Settings
from app.main import create_app
from geo_engine.pointcloud.synthetic import make_orchard, to_las_bytes

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "data" / "sample" / "imports"
URL = "/api/v1/imports"
PLOT_ID = "PLT-DEMOIN"  # the demo plot the sample files were generated around
OTHER_PLOT_ID = "PLT-DEMOUS"  # a demo plot on another continent
PROBLEM = "application/problem+json"
MB = 1024 * 1024


def settings_for(**env: Any) -> Settings:
    base: dict[str, Any] = {
        "ATLAS_MODE": "demo",
        "ATLAS_RATE_LIMIT_ENABLED": False,
        "ATLAS_API_KEYS": "",
        "ATLAS_LOG_LEVEL": "warning",
    }
    base.update(env)
    return Settings(**base)


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with TestClient(create_app(settings_for())) as client:
        yield client


@pytest.fixture(scope="module")
def small_api() -> Iterator[TestClient]:
    """An app whose upload limit is 1 MB."""
    with TestClient(create_app(settings_for(ATLAS_MAX_UPLOAD_MB=1))) as client:
        yield client


@pytest.fixture(scope="module")
def keyed_api() -> Iterator[TestClient]:
    with TestClient(create_app(settings_for(ATLAS_API_KEYS="s3cret"))) as client:
        yield client


# ---------------------------------------------------------------------------- helpers
def sample(name: str) -> bytes:
    return (SAMPLES / name).read_bytes()


def upload(
    client: TestClient,
    name: str,
    data: bytes,
    *,
    headers: dict[str, str] | None = None,
    **form: Any,
):
    fields = {
        key: (str(value).lower() if isinstance(value, bool) else str(value))
        for key, value in form.items()
        if value is not None
    }
    return client.post(
        URL,
        files={"file": (name, data, "application/octet-stream")},
        data=fields,
        headers=headers,
    )


def created(response) -> dict[str, Any]:
    assert response.status_code == 201, response.text
    return response.json()


def assert_problem(response, status: int, slug: str | None = None, code: str | None = None) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM)
    body = response.json()
    assert body["status"] == status and body["title"] and body["detail"]
    if slug:
        assert body["type"].endswith("/" + slug), body["type"]
    if code:
        assert body.get("code") == code, body
    return body


def plot_polygon(client: TestClient, plot_id: str = PLOT_ID):
    return shape(client.get(f"/api/v1/plots/{plot_id}").json()["geometry"])


def geojson_points(count: int, *, score: bool = True) -> bytes:
    """``count`` tree points (a 0.0001 degree row), every other one with a low score."""
    features = []
    for i in range(count):
        properties: dict[str, Any] = {"name": f"tree {i}"}
        if score:
            properties["score"] = 0.9 if i % 2 else 0.2
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [77.5380 + i * 1e-4, 13.2920]},
                "properties": properties,
            }
        )
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def kmz_with(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def small_cloud(*, classified: bool = True, with_crs: bool = True, compressed: bool = False):
    """12 planted trees of 4-8 m on 60 x 60 m (about 9 000 points)."""
    orchard = make_orchard(
        12,
        size_m=(60.0, 60.0),
        height_range_m=(4.0, 8.0),
        ground_points_per_m2=2.0,
        crown_points_per_m2=8.0,
        classified=classified,
        seed=3,
    )
    return orchard, to_las_bytes(orchard, compressed=compressed, with_crs=with_crs)


# ---------------------------------------------------------------------------- boundary files
def test_kml_boundary_is_read_and_linked_to_the_plot(api):
    plot_area = api.get(f"/api/v1/plots/{PLOT_ID}").json()["area_hectares"]
    record = created(upload(api, "demo-boundary.kml", sample("demo-boundary.kml"), plot_id=PLOT_ID))
    assert record["import_id"].startswith("IMP-")
    assert record["filename"] == "demo-boundary.kml"
    assert record["format"] == "kml"
    assert record["kind"] == "boundary" and record["status"] == "ready"
    assert record["plot_id"] == PLOT_ID
    assert record["size_bytes"] == len(sample("demo-boundary.kml"))
    assert record["privacy"] == "private"
    assert record["summary"] == {
        "feature_count": 1,
        "polygon_count": 1,
        "point_count": 0,
        "georeferenced": True,
        "crs": "EPSG:4326",
    }
    boundary = record["boundary"]
    assert shape(boundary["geometry"]).geom_type == "Polygon"
    assert boundary["area_hectares"] == pytest.approx(plot_area, rel=0.01)  # the demo plot itself
    assert boundary["name"] == "Demo mango orchard (synthetic)"
    assert record["trees"] is None and record["detection"] is None
    assert record["preview"]["type"] == "FeatureCollection"
    assert len(record["preview"]["features"]) == 1
    assert record["created_at"].endswith("Z")


def test_the_record_carries_provenance_and_says_the_file_was_not_stored(api):
    record = created(upload(api, "demo-boundary.kml", sample("demo-boundary.kml")))
    provenance = record["provenance"]
    assert provenance["mode"] == "demo" and provenance["api_version"] and provenance["generated_at"]
    source = provenance["sources"][0]
    assert source["id"] == "user-upload" and source["license"] and source["attribution"]
    assert provenance["parameter_set"]["id"] == "config/detection.yaml#vector_import"
    assert provenance["parameter_set"]["version"]
    assert provenance["parameter_set"]["verification_status"] in {
        "assumption",
        "pending",
        "verified",
    }
    assert any("not stored" in note for note in provenance["notes"])


@pytest.mark.parametrize("extension", ["geojson", "json"])
def test_geojson_boundary(api, extension):
    polygon = {
        "type": "Feature",
        "properties": {"name": "Field 7"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.538, 13.292],
                    [77.539, 13.292],
                    [77.539, 13.293],
                    [77.538, 13.293],
                    [77.538, 13.292],
                ]
            ],
        },
    }
    record = created(upload(api, f"field.{extension}", json.dumps(polygon).encode()))
    assert record["kind"] == "boundary" and record["format"] == "geojson"
    assert record["boundary"]["name"] == "Field 7"
    assert record["boundary"]["area_hectares"] == pytest.approx(1.2, rel=0.05)
    assert record["plot_id"] is None


def test_csv_corner_list_is_a_boundary_in_file_order(api):
    record = created(upload(api, "demo-corners.csv", sample("demo-corners.csv"), plot_id=PLOT_ID))
    assert record["kind"] == "boundary" and record["format"] == "csv"
    assert record["summary"]["point_count"] == 7
    assert record["boundary"]["area_hectares"] == pytest.approx(
        api.get(f"/api/v1/plots/{PLOT_ID}").json()["area_hectares"], rel=0.01
    )
    assert any("corners" in w and "purpose" in w for w in record["warnings"])


def test_purpose_trees_reads_the_same_csv_as_seven_trees(api):
    record = created(upload(api, "demo-corners.csv", sample("demo-corners.csv"), purpose="trees"))
    assert record["kind"] == "tree-points"
    assert record["boundary"] is None
    assert record["trees"]["count"] == 7


def test_kmz_boundary(api):
    archive = kmz_with({"doc.kml": sample("demo-boundary.kml"), "files/readme.txt": b"hello"})
    record = created(upload(api, "orchard.kmz", archive))
    assert record["format"] == "kmz" and record["kind"] == "boundary"
    assert record["boundary"]["area_hectares"] == pytest.approx(2.13, rel=0.02)


def test_a_byte_order_mark_and_windows_style_path_are_tolerated(api):
    data = b"\xef\xbb\xbf" + sample("demo-boundary.kml")
    record = created(upload(api, "C:\\Users\\me\\Documents\\orchard boundary.kml", data))
    assert record["filename"] == "orchard boundary.kml"
    assert record["kind"] == "boundary"


# ---------------------------------------------------------------------------- tree points / crowns
def test_crown_polygons_are_counted_by_confidence_inside_the_plot(api):
    record = created(
        upload(api, "demo-crowns.geojson", sample("demo-crowns.geojson"), plot_id=PLOT_ID)
    )
    assert record["kind"] == "tree-crowns" and record["format"] == "geojson"
    assert record["summary"]["feature_count"] == 220 and record["summary"]["polygon_count"] == 220
    trees = record["trees"]
    assert trees["confidence_field"] == "score" and trees["min_confidence"] == 0.5
    assert 150 <= trees["count"] < 220  # the low-score tenth is dropped
    assert trees["count_in_plot"] == trees["count"]  # all crowns stand inside the demo plot
    assert 0.0 < trees["canopy_cover_fraction"] < 1.0
    assert trees["mean_height_m"] is None and trees["p90_height_m"] is None
    assert "crown" in trees["method"] and "centroid" in trees["method"]
    assert record["boundary"] is None and record["detection"] is None
    preview = record["preview"]["features"]
    assert len(preview) == trees["count"]
    assert all(shape(f["geometry"]).geom_type == "Polygon" for f in preview)


def test_min_confidence_changes_how_many_crowns_are_kept(api):
    counts = {}
    for threshold in (0, 0.5, 0.95):
        record = created(
            upload(api, "c.geojson", sample("demo-crowns.geojson"), min_confidence=threshold)
        )
        counts[threshold] = record["trees"]["count"]
        assert record["trees"]["min_confidence"] == threshold
    assert counts[0] == 220
    assert counts[0] >= counts[0.5] >= counts[0.95]
    assert counts[0.5] < counts[0]


def test_tree_points_with_a_score_field(api):
    record = created(upload(api, "pts.geojson", geojson_points(30), plot_id=PLOT_ID))
    assert record["kind"] == "tree-points"
    assert record["summary"]["point_count"] == 30
    assert record["trees"]["count"] == 15  # the 15 points scored 0.9; the other 15 scored 0.2
    assert record["trees"]["confidence_field"] == "score"
    assert len(record["preview"]["features"]) == 15


def test_tree_points_without_a_score_are_all_counted(api):
    record = created(upload(api, "pts.geojson", geojson_points(25, score=False)))
    assert record["kind"] == "tree-points"
    assert record["trees"]["count"] == 25
    assert record["trees"]["confidence_field"] is None and record["trees"]["min_confidence"] is None


def test_purpose_boundary_on_points_that_cannot_make_a_polygon_is_explained(api):
    problem = assert_problem(
        upload(api, "pts.geojson", geojson_points(30), purpose="boundary"),
        422,
        "invalid-file",
        "invalid_boundary",
    )
    assert "order" in problem["detail"]


def test_trees_outside_the_plot_are_counted_separately(api):
    record = created(
        upload(api, "pts.geojson", geojson_points(20, score=False), plot_id=OTHER_PLOT_ID)
    )
    assert record["trees"]["count"] == 20 and record["trees"]["count_in_plot"] == 0
    assert any("None of the 20 trees" in w for w in record["warnings"])


def test_a_large_point_file_keeps_a_capped_preview(api):
    rows = "name,lat,lon\n" + "\n".join(
        f"t{i},{13.29 + (i % 100) * 1e-5:.6f},{77.53 + (i // 100) * 1e-5:.6f}" for i in range(6000)
    )
    record = created(upload(api, "many.csv", rows.encode()))
    assert record["trees"]["count"] == 6000
    assert len(record["preview"]["features"]) == 5000
    assert any("5000 of 6000" in w for w in record["warnings"])


# ---------------------------------------------------------------------------- point clouds
def detection_config() -> dict[str, Any]:
    import yaml

    return yaml.safe_load((ROOT / "config" / "detection.yaml").read_text(encoding="utf-8"))


def test_sample_laz_becomes_tree_tops_with_heights(api):
    import laspy

    with laspy.open(SAMPLES / "demo-orchard.laz") as reader:
        expected_points = reader.header.point_count
    record = created(upload(api, "demo-orchard.laz", sample("demo-orchard.laz"), plot_id=PLOT_ID))
    assert record["kind"] == "point-cloud" and record["format"] == "laz"
    assert record["summary"] == {
        "feature_count": 1,
        "polygon_count": 0,
        "point_count": expected_points,
        "georeferenced": True,
        "crs": "EPSG:32643",
    }
    trees = record["trees"]
    assert trees["count"] == pytest.approx(472, rel=0.03)  # 472 trees are planted in the sample
    assert 4.5 < trees["mean_height_m"] < 5.5 and trees["median_height_m"] < trees["p90_height_m"]
    assert 0.0 < trees["canopy_cover_fraction"] < 0.5
    assert trees["confidence_field"] is None and trees["min_confidence"] is None
    assert "canopy height model" in trees["method"]
    assert "whole cloud" in trees["method"]  # heights and counts are not limited to the plot
    assert record["boundary"] is None


def test_point_cloud_detection_block_reports_the_configured_parameters(api):
    parameters = detection_config()["point_cloud"]
    record = created(upload(api, "demo-orchard.laz", sample("demo-orchard.laz")))
    detection = record["detection"]
    assert detection["ran"] is True
    assert detection["method"] == "canopy height model + local maxima"
    for name in ("cell_size_m", "min_height_m", "window_radius_m", "ground_cell_size_m"):
        assert detection["parameters"][name] == parameters[name]["value"]
    assert detection["notes"] and all(isinstance(note, str) for note in detection["notes"])
    provenance = record["provenance"]
    assert provenance["model"]["id"] == "chm-local-maxima" and provenance["model"]["version"]
    assert provenance["parameter_set"]["id"] == "config/detection.yaml#point_cloud"
    assert any("field count" in note for note in provenance["notes"])


def test_count_in_plot_matches_the_tree_tops_inside_the_plot_polygon(api):
    record = created(upload(api, "demo-orchard.laz", sample("demo-orchard.laz"), plot_id=PLOT_ID))
    tops = record["preview"]["features"]
    assert len(tops) == record["trees"]["count"]  # at most 5 000 tops are previewed
    polygon = plot_polygon(api)
    inside = [t for t in tops if polygon.contains(shape(t["geometry"]))]
    assert record["trees"]["count_in_plot"] == len(inside)
    assert len(inside) == sum(1 for t in tops if t["properties"]["in_plot"])
    assert 0 < len(inside) < len(tops)  # the cloud reaches beyond the plot
    assert all(t["properties"]["height_m"] > 2.0 for t in tops)  # min_height_m


def test_a_cloud_without_a_plot_has_no_count_in_plot(api):
    record = created(upload(api, "demo-orchard.laz", sample("demo-orchard.laz")))
    assert record["plot_id"] is None
    assert record["trees"]["count_in_plot"] is None


@pytest.mark.parametrize("compressed", [False, True], ids=["las", "laz"])
def test_small_cloud_counts_the_planted_trees(api, compressed):
    orchard, data = small_cloud(compressed=compressed)
    record = created(upload(api, "orchard.laz" if compressed else "orchard.las", data))
    assert record["format"] == ("laz" if compressed else "las")
    assert record["summary"]["point_count"] == orchard.n_points
    assert record["trees"]["count"] == orchard.n_trees == 12
    assert record["trees"]["mean_height_m"] == pytest.approx(
        float(orchard.tree_height_m.mean()), abs=0.2
    )
    assert record["warnings"] == []


def test_an_unclassified_cloud_estimates_the_ground_itself(api):
    orchard, data = small_cloud(classified=False)
    record = created(upload(api, "unclassified.las", data))
    assert record["trees"]["count"] == orchard.n_trees
    assert any("lowest return" in note for note in record["detection"]["notes"])


def test_a_cloud_without_a_crs_is_analysed_but_not_placed(api):
    orchard, data = small_cloud(with_crs=False)
    record = created(upload(api, "no-crs.las", data, plot_id=PLOT_ID))
    assert record["summary"]["georeferenced"] is False and record["summary"]["crs"] is None
    assert record["trees"]["count"] == orchard.n_trees
    assert record["trees"]["count_in_plot"] is None
    assert record["preview"] is None  # nothing can be drawn without a position
    assert any("coordinate system" in w for w in record["warnings"])


def test_run_detection_false_only_inspects_the_file(api):
    _, data = small_cloud()
    record = created(upload(api, "orchard.las", data, run_detection=False))
    assert record["kind"] == "point-cloud"
    assert record["trees"] is None and record["preview"] is None
    assert record["detection"]["ran"] is False and record["detection"]["parameters"] is None
    assert record["summary"]["point_count"] > 0 and record["summary"]["georeferenced"] is True


def test_a_cloud_elsewhere_warns_that_it_does_not_overlap_the_plot(api):
    _, data = small_cloud()
    detected = created(upload(api, "orchard.las", data, plot_id=PLOT_ID))
    assert detected["trees"]["count"] == 12 and detected["trees"]["count_in_plot"] == 0
    assert any("does not overlap the plot" in w for w in detected["warnings"])
    inspected = created(upload(api, "orchard.las", data, plot_id=PLOT_ID, run_detection=False))
    assert any("does not overlap the plot" in w for w in inspected["warnings"])


def test_e57_gets_advice_when_pye57_is_missing(api, monkeypatch):
    monkeypatch.setattr("app.services.imports.pye57_available", lambda: False)
    problem = assert_problem(
        upload(api, "scan.e57", b"ASTM-E57" + b"\x00" * 64),
        415,
        "unsupported-file-type",
        "e57_unsupported",
    )
    assert problem["title"] == "Unsupported Media Type"
    assert "CloudCompare" in problem["detail"] and "PDAL" in problem["detail"]
    assert "LAZ" in problem["detail"]


def test_a_cloud_in_degrees_is_rejected_with_advice(api):
    orchard = make_orchard(5, size_m=(60.0, 60.0), origin=(77.5, 13.29), epsg=4326)
    problem = assert_problem(
        upload(api, "degrees.las", to_las_bytes(orchard, epsg=4326)),
        422,
        "invalid-file",
        "geographic_crs",
    )
    assert "projected" in problem["detail"] and "UTM" in problem["detail"]


def test_damaged_clouds_are_422_with_a_code(api):
    _, data = small_cloud()
    truncated = assert_problem(upload(api, "cut.las", data[: len(data) // 2]), 422, "invalid-file")
    assert truncated["code"] == "truncated"
    garbage = assert_problem(upload(api, "bad.las", b"LASF" + b"\x00" * 300), 422, "invalid-file")
    assert garbage["code"] == "invalid_content"


# ---------------------------------------------------------------------------- what is accepted
@pytest.mark.parametrize(
    "name", ["notes.txt", "parcel.shp", "scan", "archive.zip", "photo.tif", ".csv.exe"]
)
def test_other_file_types_are_415_with_the_list_of_accepted_ones(api, name):
    problem = assert_problem(upload(api, name, b"hello"), 415, "unsupported-file-type")
    assert (
        problem["code"] == "unsupported_extension" and problem["title"] == "Unsupported Media Type"
    )
    assert ".geojson" in problem["detail"] and ".laz" in problem["detail"]


@pytest.mark.parametrize(
    "name, data",
    [
        ("a.las", b"this is not a point cloud"),
        ("a.laz", b"PK\x03\x04 zip data"),
        ("a.kmz", b"<kml/>"),
        ("a.kml", b"\x00\x01\x02\x03"),
        ("a.geojson", b"<kml/>"),
        ("a.json", b"PK\x03\x04"),
        ("a.csv", b"\x00\x01\x02\x03"),
        ("a.e57", b"LASF....."),
    ],
)
def test_content_that_does_not_fit_the_extension_is_415(api, name, data):
    problem = assert_problem(upload(api, name, data), 415, "unsupported-file-type")
    assert problem["code"] == "signature_mismatch"
    assert "does not match" in problem["detail"]


def test_an_empty_file_is_422(api):
    assert_problem(upload(api, "empty.csv", b""), 422, "invalid-file", "empty_file")


def test_a_malformed_file_is_422_with_the_engine_code(api):
    assert_problem(upload(api, "bad.geojson", b"{not json"), 422, "invalid-file", "invalid_content")
    assert_problem(
        upload(api, "odd.geojson", b'{"hello": 1}'), 422, "invalid-file", "invalid_content"
    )
    projected = json.dumps({"type": "Point", "coordinates": [775000, 1470000]}).encode()
    assert_problem(
        upload(api, "utm.geojson", projected), 422, "invalid-file", "coordinate_out_of_range"
    )
    assert_problem(
        upload(api, "head.csv", b"name,lat,lon\n"), 422, "invalid-file", "no_coordinates"
    )


def test_a_self_intersecting_boundary_is_422_and_does_not_echo_coordinates(api):
    bowtie = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.5311, 13.2911],
                [77.5421, 13.3021],
                [77.5421, 13.2911],
                [77.5311, 13.3021],
                [77.5311, 13.2911],
            ]
        ],
    }
    problem = assert_problem(
        upload(api, "bowtie.geojson", json.dumps(bowtie).encode()),
        422,
        "invalid-file",
        "invalid_boundary",
    )
    assert "Self-intersection" in problem["detail"]
    assert not re.search(r"\d+\.\d{3,}", problem["detail"])


def test_purpose_and_min_confidence_are_validated(api):
    assert_problem(
        upload(api, "a.kml", sample("demo-boundary.kml"), purpose="everything"),
        422,
        "validation-error",
    )
    too_high = assert_problem(
        upload(api, "p.geojson", geojson_points(5), min_confidence=1.5), 422, "validation-error"
    )
    assert too_high["errors"][0]["field"].endswith("min_confidence")
    assert_problem(
        upload(api, "p.geojson", geojson_points(5), min_confidence=-0.1), 422, "validation-error"
    )


def test_the_file_field_is_required(api):
    assert_problem(api.post(URL, data={"plot_id": PLOT_ID}), 422, "validation-error")
    assert_problem(api.post(URL, json={"file": "x"}), 422, "validation-error")


def test_a_plot_that_does_not_exist_is_404(api):
    problem = assert_problem(
        upload(api, "a.kml", sample("demo-boundary.kml"), plot_id="PLT-NOPE"), 404, "plot-not-found"
    )
    assert "PLT-NOPE" in problem["detail"]


# ---------------------------------------------------------------------------- limits
def test_a_body_over_the_limit_is_413_before_it_is_read(small_api):
    response = upload(small_api, "big.csv", b"name,lat,lon\n" + b"x" * (2 * MB))
    problem = assert_problem(response, 413, "payload-too-large")
    assert problem["title"] == "Payload Too Large"


def chunked_multipart(name: str, payload: bytes, chunk: int = 64 * 1024):
    """A multipart body sent as a generator: no Content-Length, so the guard cannot rely on it."""
    boundary = "----atlas-chunked-boundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body():
        yield head
        for start in range(0, len(payload), chunk):
            yield payload[start : start + chunk]
        yield tail

    return body(), {"Content-Type": f"multipart/form-data; boundary={boundary}"}


@pytest.mark.parametrize("megabytes", [1.3, 5])
def test_a_chunked_body_without_content_length_is_cut_off_at_the_limit(small_api, megabytes):
    payload = b"name,lat,lon\n" + b"A,13.29,77.53\n" * int(megabytes * MB / 14)
    body, headers = chunked_multipart("big.csv", payload)
    response = small_api.post(URL, content=body, headers=headers)
    assert_problem(response, 413, "payload-too-large")


def test_a_file_just_under_the_limit_is_accepted(small_api):
    big = {
        "type": "Feature",
        "properties": {"description": "x" * (900 * 1024)},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[77.53, 13.29], [77.54, 13.29], [77.54, 13.30], [77.53, 13.30], [77.53, 13.29]]
            ],
        },
    }
    record = created(upload(small_api, "big.geojson", json.dumps(big).encode()))
    assert record["kind"] == "boundary" and record["size_bytes"] > 900 * 1024


def test_the_feature_limit_is_20000(api):
    def rows(count: int) -> bytes:
        lines = [
            f"t{i},{13.29 + (i % 100) * 1e-5:.6f},{77.53 + (i // 100) * 1e-5:.6f}"
            for i in range(count)
        ]
        return ("name,lat,lon\n" + "\n".join(lines)).encode()

    record = created(upload(api, "limit.csv", rows(20_000)))
    assert record["summary"]["feature_count"] == 20_000
    assert_problem(upload(api, "limit.csv", rows(20_001)), 422, "invalid-file", "too_many_features")


# ---------------------------------------------------------------------------- hostile files
XXE_KML = (
    b'<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b'<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>&xxe;</name></Document></kml>'
)
BILLION_LAUGHS = (
    b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
    b'<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>&lol2;</name></Document></kml>'
)


@pytest.mark.parametrize(
    "payload", [XXE_KML, BILLION_LAUGHS], ids=["external-entity", "entity-expansion"]
)
def test_kml_with_entities_is_refused_and_nothing_is_read(api, payload):
    problem = assert_problem(upload(api, "evil.kml", payload), 422, "invalid-file", "unsafe_xml")
    assert "root:" not in problem["detail"]
    in_kmz = assert_problem(
        upload(api, "evil.kmz", kmz_with({"doc.kml": payload})), 422, "invalid-file", "unsafe_xml"
    )
    assert "root:" not in in_kmz["detail"]


def test_a_kmz_that_expands_beyond_the_limit_is_refused(api):
    bomb = kmz_with({"doc.kml": b"<kml>" + b"A" * (60 * MB) + b"</kml>"})
    assert len(bomb) < 1 * MB  # a small upload that would fill memory when unpacked
    assert_problem(upload(api, "bomb.kmz", bomb), 422, "invalid-file", "archive_too_large")


def test_a_kmz_with_too_many_entries_is_refused(api):
    entries = {f"file{i}.txt": b"x" for i in range(101)}
    entries["doc.kml"] = sample("demo-boundary.kml")
    assert_problem(
        upload(api, "many.kmz", kmz_with(entries)), 422, "invalid-file", "archive_too_many_entries"
    )


def test_a_kmz_without_a_kml_or_that_is_not_a_zip_is_422(api):
    assert_problem(upload(api, "none.kmz", kmz_with({"readme.txt": b"hi"})), 422, "invalid-file")
    assert_problem(
        upload(api, "fake.kmz", b"PK\x03\x04 not really a zip"), 422, "invalid-file", "bad_archive"
    )


@pytest.mark.parametrize(
    "given, expected",
    [
        ("../../etc/passwd.csv", "passwd.csv"),
        ("..\\..\\windows\\system32\\points.csv", "points.csv"),
        ("/var/data/orchard.kml", "orchard.kml"),
        ("my orchard (final).csv", "my orchard (final).csv"),
    ],
)
def test_the_stored_file_name_is_a_base_name(api, given, expected):
    data = sample("demo-corners.csv") if expected.endswith(".csv") else sample("demo-boundary.kml")
    assert created(upload(api, given, data))["filename"] == expected


def test_file_name_helpers():
    from app.services.imports import extension_of, safe_filename

    assert safe_filename(None) == "upload" and safe_filename("") == "upload"
    assert safe_filename("a\x00b\x1f.csv") == "ab.csv"
    long_name = safe_filename("x" * 300 + ".geojson")
    assert len(long_name) <= 200 and long_name.endswith(".geojson")
    assert extension_of("Orchard.LAZ") == extension_of("dir/orchard.laz") == "laz"
    assert extension_of("noextension") == "" and extension_of("trailing.") == ""


# ---------------------------------------------------------------------------- stored records
def make_plot(client: TestClient, geometry: dict, **extra: Any) -> str:
    body = {"name": "Imported boundary", "country": "IN", "geometry": geometry, **extra}
    response = client.post("/api/v1/plots", json=body)
    assert response.status_code == 201, response.text
    return response.json()["plot_id"]


def test_list_get_and_delete_round_trip(api):
    boundary = created(upload(api, "b.kml", sample("demo-boundary.kml")))["boundary"]["geometry"]
    plot_id = make_plot(api, boundary, source="import")
    first = created(upload(api, "first.kml", sample("demo-boundary.kml"), plot_id=plot_id))
    second = created(upload(api, "second.csv", sample("demo-corners.csv"), plot_id=plot_id))
    created(
        upload(api, "unlinked.csv", sample("demo-corners.csv"))
    )  # no plot: not in the plot's list

    listed = api.get(URL, params={"plot_id": plot_id})
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert [item["import_id"] for item in items] == [
        second["import_id"],
        first["import_id"],
    ]  # newest first
    assert all("preview" not in item and item["plot_id"] == plot_id for item in items)
    assert items[0]["boundary"]["geometry"]["type"] == "Polygon"  # everything but the preview

    one = api.get(f"{URL}/{first['import_id']}")
    assert one.status_code == 200
    assert one.json() == first and one.json()["preview"]["features"]

    everything = api.get(URL).json()["items"]
    assert {first["import_id"], second["import_id"]} <= {item["import_id"] for item in everything}
    assert all("preview" not in item for item in everything)

    assert api.delete(f"{URL}/{first['import_id']}").status_code == 204
    assert_problem(api.get(f"{URL}/{first['import_id']}"), 404, "import-not-found")
    assert_problem(api.delete(f"{URL}/{first['import_id']}"), 404, "import-not-found")
    remaining = api.get(URL, params={"plot_id": plot_id}).json()["items"]
    assert [item["import_id"] for item in remaining] == [second["import_id"]]


def test_a_list_for_an_unknown_plot_is_empty_and_an_unknown_import_is_404(api):
    assert api.get(URL, params={"plot_id": "PLT-NOPE"}).json() == {"items": []}
    assert_problem(api.get(f"{URL}/IMP-NOPE00"), 404, "import-not-found")


def test_deleting_a_plot_deletes_its_imports(api):
    geometry = created(upload(api, "b.kml", sample("demo-boundary.kml")))["boundary"]["geometry"]
    plot_id = make_plot(api, geometry, source="import")
    linked = created(upload(api, "linked.kml", sample("demo-boundary.kml"), plot_id=plot_id))
    free = created(upload(api, "free.kml", sample("demo-boundary.kml")))
    assert api.delete(f"/api/v1/plots/{plot_id}").status_code == 204
    assert_problem(api.get(f"{URL}/{linked['import_id']}"), 404, "import-not-found")
    assert api.get(f"{URL}/{free['import_id']}").status_code == 200  # not linked, so it stays


def test_the_imported_boundary_can_become_a_plot(api):
    record = created(upload(api, "b.kml", sample("demo-boundary.kml")))
    plot = api.post(
        "/api/v1/plots",
        json={
            "name": "From KML",
            "country": "IN",
            "source": "import",
            "geometry": record["boundary"]["geometry"],
        },
    )
    assert plot.status_code == 201
    body = plot.json()
    assert body["source"] == "import" and body["boundary_quality"] == "exact"
    assert body["area_hectares"] == pytest.approx(record["boundary"]["area_hectares"], rel=0.01)


def test_the_raw_file_is_never_stored(api):
    marker = "UNIQUE-MARKER-9f3a7c"
    rows = (
        "name,lat,lon,secret_note\n"
        f"A,13.2931,77.5387,{marker}\nB,13.2925,77.5391,{marker}\n"
        f"C,13.2918,77.5391,{marker}\nD,13.2915,77.5384,{marker}\n"
    )
    record = created(upload(api, "private-notes.csv", rows.encode(), purpose="boundary"))
    context = api.app.state.context
    stored = json.dumps(context.repo.list_records("import", None, limit=10_000))
    assert marker not in stored and marker not in json.dumps(record)
    events = [e for e in context.repo.audit_events() if e["event"] == "import.created"]
    assert events and marker not in json.dumps(events) and "private-notes" not in json.dumps(events)
    assert all(set(e["detail"]) == {"format", "kind", "size_bytes"} for e in events)


def test_deleting_an_import_is_audited_without_coordinates(api):
    record = created(upload(api, "b.kml", sample("demo-boundary.kml")))
    assert api.delete(f"{URL}/{record['import_id']}").status_code == 204
    deleted = [
        e for e in api.app.state.context.repo.audit_events() if e["event"] == "import.deleted"
    ]
    assert deleted and deleted[-1]["detail"] == {"kind": "boundary"}


# ---------------------------------------------------------------------------- API key
def test_writing_needs_the_api_key_when_keys_are_configured(keyed_api):
    data = sample("demo-boundary.kml")
    no_key = upload(keyed_api, "b.kml", data)
    assert no_key.status_code == 401 and no_key.headers["content-type"].startswith(PROBLEM)
    wrong = upload(keyed_api, "b.kml", data, headers={"X-API-Key": "nope"})
    assert wrong.status_code == 403
    record = created(upload(keyed_api, "b.kml", data, headers={"X-API-Key": "s3cret"}))

    # reading stays open
    assert keyed_api.get(URL).status_code == 200
    assert keyed_api.get(f"{URL}/{record['import_id']}").status_code == 200
    # deleting does not
    assert keyed_api.delete(f"{URL}/{record['import_id']}").status_code == 401
    assert (
        keyed_api.delete(f"{URL}/{record['import_id']}", headers={"X-API-Key": "nope"}).status_code
        == 403
    )
    assert (
        keyed_api.delete(
            f"{URL}/{record['import_id']}", headers={"X-API-Key": "s3cret"}
        ).status_code
        == 204
    )


def test_a_rejected_upload_is_not_read_or_stored(keyed_api):
    before = len(keyed_api.get(URL).json()["items"])
    assert upload(keyed_api, "b.kml", sample("demo-boundary.kml")).status_code == 401
    assert len(keyed_api.get(URL).json()["items"]) == before


# ---------------------------------------------------------------------------- privacy
def test_coordinates_are_never_logged(api, caplog):
    secrets = ("13.29314", "77.53876", "13.2917", "77.5380", "774927", "1470776")
    with caplog.at_level(logging.DEBUG):
        records = [
            created(upload(api, "b.kml", sample("demo-boundary.kml"), plot_id=PLOT_ID)),
            created(upload(api, "c.csv", sample("demo-corners.csv"), plot_id=PLOT_ID)),
            created(upload(api, "crowns.geojson", sample("demo-crowns.geojson"), plot_id=PLOT_ID)),
            created(upload(api, "o.laz", sample("demo-orchard.laz"), plot_id=PLOT_ID)),
        ]
        upload(api, "bad.geojson", b'{"type": "Point", "coordinates": [77.53876, 13.29314, "x"]}')
        upload(api, "evil.kml", XXE_KML)
        for record in records:
            api.get(f"{URL}/{record['import_id']}")
        api.delete(f"{URL}/{records[0]['import_id']}")
    logged = " ".join(
        f"{r.getMessage()} {r.__dict__.get('path', '')} {r.exc_text or ''}" for r in caplog.records
    )
    assert logged  # something was logged (requests), so the check below is meaningful
    for fragment in secrets:
        assert fragment not in logged
    assert "demo-orchard" not in logged  # file names are not logged either


def test_import_problems_never_carry_coordinates(api):
    kml = (
        b'<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><Polygon><outerBoundaryIs>'
        b"<LinearRing><coordinates>77.123456,13.654321 77.2,abc 77.3,13.7</coordinates>"
        b"</LinearRing></outerBoundaryIs></Polygon></Placemark></kml>"
    )
    tiny = b"name,lat,lon\nA,13.654321,77.123456\nB,13.654322,77.123457\nC,13.654323,77.123458\n"
    cases = [
        (
            "far.geojson",
            b'{"type": "Point", "coordinates": [977.123456, 13.654321]}',
            "auto",
            "coordinate_out_of_range",
        ),
        (
            "line.geojson",
            b'{"type": "LineString", '
            b'"coordinates": [[77.123456, 13.654321], [77.123457, 13.654322]]}',
            "auto",
            "no_features",
        ),
        ("tiny.csv", tiny, "boundary", "invalid_boundary"),
        ("bad.kml", kml, "auto", "invalid_content"),
    ]
    for name, data, purpose, code in cases:
        response = upload(api, name, data, purpose=purpose)
        assert_problem(response, 422, "invalid-file", code)
        for fragment in ("77.123456", "13.654321", "977.123456", "77.123457"):
            assert fragment not in response.text, (name, fragment)
