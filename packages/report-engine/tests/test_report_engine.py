from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from report_engine import (
    FORMATS,
    MEDIA_TYPES,
    PdfNotAvailableError,
    ReportIdSequencer,
    ReportRenderer,
    new_report_id,
    pdf_available,
)


def sample_context() -> dict:
    return {
        "report_id": "RPT-2026-10-04-0001",
        "generated_at": "2026-10-04T09:12:00Z",
        "language": "en",
        "mode": "demo",
        "api_version": "1",
        "plot": {
            "plot_id": "PLT-DEMOIN",
            "name": "Demo mango farm <script>",
            "country": "IN",
            "region": "Karnataka",
            "area_hectares": 2.13,
            "area_acres": 5.26,
            "perimeter_m": 612.4,
            "public_centroid": {"lat": 13.30, "lon": 77.55},
            "source": "synthetic-demo",
        },
        "inventory": {
            "species": {"common_name": "Mango", "scientific_name": "Mangifera indica"},
            "tree_count": 420,
            "density_per_ha": 197.2,
            "plantation_year": 2023,
            "age_years": 3,
            "average_dbh_cm": None,
            "average_height_m": None,
            "survival_rate": 0.85,
            "measurement_source": "user-reported",
            "data_quality": {"confidence": "medium"},
        },
        "analysis": {
            "landcover": {
                "dataset": "ESA WorldCover",
                "version": "2021 v200",
                "resolution_m": 10,
                "classes": [{"code": 40, "name": "Cropland", "share": 0.62, "area_ha": 1.32}],
            },
            "vegetation": {
                "indices": {
                    "ndvi": {"value": 0.76, "class": "healthy"},
                    "ndmi": {"value": 0.21, "class": "moderate"},
                },
                "time_series": [
                    {
                        "date": "2026-09-21",
                        "ndvi": 0.76,
                        "ndmi": 0.21,
                        "cloud_cover": 3.0,
                        "scene_id": "S2X",
                    }
                ],
                "trend": {
                    "statement": "Vegetation index increased approximately 23% during the evaluated period."
                },
            },
            "climate": {
                "zone_label": "Tropical dry",
                "mean_annual_temp_c": 24.1,
                "annual_precip_mm": 820,
                "elevation_m": 880,
            },
            "soil": {"soc_0_30cm_g_per_kg": 9.8},
            "data_quality": {"warnings": ["demo mode: synthetic observations"]},
        },
        "estimate": {
            "model": {"id": "tree-biomass", "version": "0.1.0", "tier": "1"},
            "methodology": {"name": "IPCC 2006 Vol.4 Ch.4 Tier 1"},
            "estimate": {"low": 7.7, "central": 11.0, "high": 14.3, "unit": "tCO2e/yr"},
            "stock": {"low": 16.1, "central": 23.0, "high": 29.9, "unit": "tCO2e"},
            "components": {"above_ground_tco2e_yr": 8.1, "below_ground_tco2e_yr": 2.9},
            "annual_series": [
                {
                    "year": 2023 + i,
                    "age": i,
                    "low": i,
                    "central": i * 1.5,
                    "high": i * 2,
                    "cum_central": i * 3,
                }
                for i in range(11)
            ],
            "parameters_used": [
                {
                    "name": "carbon_fraction",
                    "value": 0.47,
                    "unit": "t C/t d.m.",
                    "source": "IPCC 2006 Table 4.3",
                    "verification_status": "verified",
                }
            ],
            "confidence": "medium",
            "readiness": {
                "score": 55,
                "grade": "medium",
                "present_evidence": [{"id": "polygon", "label": "Land polygon"}],
                "missing_evidence": [
                    {"id": "dbh", "label": "Tree diameter measurements", "weight": 15}
                ],
            },
            "provenance": {"parameter_set": {"verification_status": "pending"}},
            "notes": ["Headline estimate: mean annual removal over the horizon."],
        },
        "policy": {
            "disclaimer": "Initial screening only — not an eligibility determination.",
            "programmes": [
                {
                    "name": "Green Credit Programme",
                    "authority": "MoEFCC",
                    "kind": "government_programme",
                    "status": "requires_assessment",
                    "requirements": ["Registration"],
                    "notes": ["Green Credits are distinct from carbon credits."],
                    "references": [{"title": "MoEFCC", "url": "https://moef.gov.in/"}],
                }
            ],
        },
        "market": {
            "currency": "INR",
            "currency_symbol": "₹",
            "scenarios": [
                {
                    "id": "low",
                    "price_per_tco2e": 480,
                    "value_per_year": {"low": 3696, "central": 5280, "high": 6864},
                }
            ],
            "basis": {
                "source": "config/market/carbon-price-scenarios.yaml",
                "as_of": "2025",
                "note": "Illustrative.",
            },
            "other_income": [
                {
                    "id": "fruit_yield",
                    "label": "Fruit yield",
                    "value": None,
                    "unit": "INR/yr",
                    "source": "records",
                }
            ],
            "disclaimer": "Market-value scenario — not guaranteed revenue.",
        },
        "sources": [
            {
                "id": "esa-worldcover",
                "name": "ESA WorldCover 2021 v200",
                "version": "v200",
                "license": "CC BY 4.0",
                "attribution": "© ESA WorldCover project 2021",
            }
        ],
        "disclaimer": "Scenario estimate; not an issued carbon credit.",
    }


@pytest.fixture(scope="module")
def renderer() -> ReportRenderer:
    return ReportRenderer()


def test_html_report_contains_sections_design_tokens_and_escapes(renderer):
    html = renderer.render_html(sample_context())
    for heading in (
        "Plot",
        "Plantation",
        "Earth observations",
        "Carbon",
        "Potential programmes (screening)",
        "Financial scenarios",
        "Evidence",
        "Disclaimer",
    ):
        assert heading in html
    assert "#1E6B41" in html and "#14211A" in html and "#F3F6F2" in html
    assert "Space+Grotesk" in html and "IBM+Plex+Sans" in html and "IBM+Plex+Mono" in html
    assert "not an issued carbon credit" in html
    assert "&lt;script&gt;" in html and "<script>" not in html  # autoescaped plot name
    assert "RPT-2026-10-04-0001" in html
    assert "13.30°, 77.55°" in html  # generalized centroid only


def test_markdown_and_json_renderers(renderer):
    md = renderer.render_markdown(sample_context())
    assert md.startswith("# CarbonCreditBuy — Evidence report RPT-2026-10-04-0001")
    assert "| Estimated annual carbon removal | 7.7 | 11.0 | 14.3 | tCO2e/yr |" in md
    assert "<script>" in md  # markdown is not HTML-escaped
    data = json.loads(renderer.render_json(sample_context()))
    assert data["estimate"]["certified"] is False if "certified" in data["estimate"] else True
    assert data["report_id"] == "RPT-2026-10-04-0001"


def test_render_dispatch_and_media_types(renderer):
    ctx = sample_context()
    for fmt in ("html", "markdown", "json"):
        assert isinstance(renderer.render(ctx, fmt), bytes)
        assert fmt in MEDIA_TYPES
    assert set(FORMATS) == set(MEDIA_TYPES)
    with pytest.raises(ValueError):
        renderer.render(ctx, "docx")


def test_pdf_raises_cleanly_when_weasyprint_missing(renderer):
    if pdf_available():
        pytest.skip("WeasyPrint installed; PDF path exercised by integration tests")
    with pytest.raises(PdfNotAvailableError):
        renderer.render_pdf(sample_context())


def test_missing_optional_blocks_render_placeholders(renderer):
    ctx = sample_context()
    ctx.update(
        {"inventory": None, "analysis": None, "estimate": None, "policy": None, "market": None}
    )
    html = renderer.render_html(ctx)
    assert "No tree inventory" in html and "No carbon estimate" in html
    assert "No programme screening" in html and "No market scenario" in html
    md = renderer.render_markdown(ctx)
    assert "No carbon estimate generated." in md


def test_report_ids():
    assert new_report_id(datetime(2026, 10, 4, tzinfo=UTC).date(), 1) == "RPT-2026-10-04-0001"
    seq = ReportIdSequencer()
    when = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    assert seq.next_id(when) == "RPT-2026-10-04-0001"
    assert seq.next_id(when) == "RPT-2026-10-04-0002"
    assert seq.next_id(datetime(2026, 10, 5, tzinfo=UTC)) == "RPT-2026-10-05-0001"
    seq.observe("RPT-2026-10-06-0042")
    assert seq.next_id(datetime(2026, 10, 6, tzinfo=UTC)) == "RPT-2026-10-06-0043"
    with pytest.raises(ValueError):
        new_report_id(when.date(), 0)
