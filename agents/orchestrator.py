"""Central orchestrator — runs the 4-agent PRISM pipeline sequentially."""

import anthropic
from utils.map_utils import geocode_address
from agents import data_harvesting, risk_analysis, validation, communication


def run_assessment(address: str, api_key: str):
    """
    Generator that yields (stage, log_line, payload) tuples.
    stages: 'log', 'scores', 'validation', 'report', 'map_data', 'done', 'error'
    """
    client = anthropic.Anthropic(api_key=api_key)

    try:
        # Geocode
        yield "log", f"📍 Geocoding address: **{address}**", None
        lat, lon = geocode_address(address)
        yield "log", f"   ↳ Coordinates: {lat:.4f}°S, {lon:.4f}°E", None

        # Stage 1: Data Harvesting
        yield "log", "─" * 50, None
        data_bundle = {}
        for log_line, payload in data_harvesting.run(client, address, lat, lon):
            yield "log", log_line, None
            if payload is not None:
                data_bundle = payload

        # Stage 2: Risk Analysis
        yield "log", "─" * 50, None
        scores = None
        for log_line, payload in risk_analysis.run(client, data_bundle):
            yield "log", log_line, None
            if payload is not None:
                scores = payload

        if scores:
            # Compute confidence from data completeness — injected after scoring
            prop = data_bundle.get("get_property_data", {})
            flood_overlay = data_bundle.get("get_flood_overlay", {})
            bushfire_overlay = data_bundle.get("get_bushfire_overlay", {})

            conf = 95
            if not prop.get("estimated_value_aud"):
                conf -= 5
            if not prop.get("floor_area_sqm"):
                conf -= 3
            if not prop.get("year_built"):
                conf -= 3
            if not prop.get("property_type"):
                conf -= 2
            if flood_overlay.get("in_flood_planning_zone") is None:
                conf -= 4
            if bushfire_overlay.get("bushfire_prone_land") is None:
                conf -= 3
            # Missing year_built on a high-erosion coastal property is a material gap —
            # structural vintage directly affects setback compliance assessment.
            erosion_score = scores.get("perils", {}).get("erosion", {}).get("score", 0)
            year_built = prop.get("year_built")
            if not year_built and erosion_score >= 50:
                conf -= 8
            elif year_built and year_built < 1950:
                # Pre-war construction is known but introduces its own uncertainty —
                # original materials and foundation standards are unverifiable without inspection.
                conf -= 3
            scores["confidence"] = f"{max(55, conf)}%"

            yield "scores", None, scores

        # Stage 3: Validation
        yield "log", "─" * 50, None
        validation_result = {}
        for log_line, payload in validation.run(client, scores or {}, data_bundle):
            yield "log", log_line, None
            if payload is not None:
                validation_result = payload

        yield "validation", None, validation_result

        # Stage 4: Communication / Report
        yield "log", "─" * 50, None
        report = ""
        for log_line, payload in communication.run(client, address, scores or {}, data_bundle, validation_result):
            yield "log", log_line, None
            if payload is not None:
                report = payload

        yield "report", None, report

        # Map data
        yield "map_data", None, {
            "address": address,
            "lat": lat,
            "lon": lon,
            "scores": scores or {},
            "flood_data": data_bundle.get("get_flood_overlay", {}),
            "bushfire_data": data_bundle.get("get_bushfire_overlay", {}),
        }

        overall = (scores or {}).get("overall_score", "N/A")
        band = (scores or {}).get("risk_band", "UNKNOWN")
        yield "log", f"\n🏁 **Assessment complete** — Overall Score: **{overall}/100** ({band} RISK)", None
        yield "done", None, None

    except Exception as e:
        yield "error", f"❌ Assessment failed: {str(e)}", None
