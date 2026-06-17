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
