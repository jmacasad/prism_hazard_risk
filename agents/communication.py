"""Communication Agent — synthesises all findings into a professional underwriter report."""

import json
import anthropic

SYSTEM_PROMPT = """You are the PRISM Communication Agent — a senior insurance analyst.
Your role is to synthesise risk assessment findings into a clear, professional report
for a luxury property underwriter. The report must be:
- Precise and evidence-based
- Written for an experienced underwriter, not a lay audience
- Compliant with APRA disclosure requirements
- Actionable — include specific policy recommendations

Structure your report with these sections:
1. Executive Summary (3-4 sentences)
2. Property Profile
3. Peril Assessment (one paragraph per peril)
4. Recommended Underwriting Action
5. Policy Conditions & Exclusions
6. Mitigation Recommendations (what the insured could do to improve risk profile)
7. Regulatory Notes

Use Australian insurance terminology. Be direct about risk — do not soften findings."""


def run(client: anthropic.Anthropic, address: str, scores: dict, data_bundle: dict, validation: dict):
    """Run the Communication Agent. Yields (log_line, report_or_None) tuples."""
    yield "📝 Communication Agent activated — generating underwriter report...", None

    property_data = data_bundle.get("get_property_data", {})
    weather = data_bundle.get("get_weather_observations", {})
    satellite = data_bundle.get("get_satellite_analysis", {})
    claims = data_bundle.get("get_historical_claims", {})
    flood = data_bundle.get("get_flood_overlay", {})
    bushfire = data_bundle.get("get_bushfire_overlay", {})
    geo = data_bundle.get("get_geological_hazards", {})

    perils = scores.get("perils", {})

    prompt = f"""Generate a professional risk assessment report for:

ADDRESS: {address}
OVERALL RISK SCORE: {scores.get('overall_score')}/100 — {scores.get('risk_band')} RISK
CONFIDENCE: {scores.get('confidence')}
PREMIUM LOADING RECOMMENDATION: {scores.get('premium_loading')}

PERIL SCORES:
- Bushfire: {perils.get('bushfire', {}).get('score', 'N/A')}/100 | Factors: {perils.get('bushfire', {}).get('factors', [])}
- Flood: {perils.get('flood', {}).get('score', 'N/A')}/100 | Factors: {perils.get('flood', {}).get('factors', [])}
- Storm: {perils.get('storm', {}).get('score', 'N/A')}/100 | Factors: {perils.get('storm', {}).get('factors', [])}
- Erosion: {perils.get('erosion', {}).get('score', 'N/A')}/100 | Factors: {perils.get('erosion', {}).get('factors', [])}
- Landslip: {perils.get('landslip', {}).get('score', 'N/A')}/100 | Factors: {perils.get('landslip', {}).get('factors', [])}

PROPERTY DATA:
- Estimated value: AUD ${property_data.get('estimated_value_aud', 'N/A'):,}
- Built: {property_data.get('year_built')} | Construction: {property_data.get('construction_type')}
- Roof: {property_data.get('roof_type')} | Stories: {property_data.get('stories')}
- Land: {property_data.get('land_area_sqm')} sqm | Floor: {property_data.get('floor_area_sqm')} sqm

ENVIRONMENTAL DATA:
- Current fire danger: {weather.get('fire_danger')} | Wind: {weather.get('wind_speed_kmh')} km/h {weather.get('wind_dir')}
- Vegetation NDVI: {satellite.get('ndvi_score')} ({satellite.get('vegetation_density')}) | Defensible space: {satellite.get('defensible_space_m')}m
- Historical claims (5km, 10yr): {claims.get('total_claims_10yr')} total | Avg: AUD ${claims.get('avg_claim_value_aud', 0):,}
- Flood zone: {flood.get('flood_category')} | Erosion: {geo.get('coastal_erosion_risk')}

COMPLIANCE:
{json.dumps(validation.get('compliance_notes', []), indent=2)}
Human review required: {validation.get('human_review_required', False)}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    report = response.content[0].text
    yield "✅ Report generated — ready for underwriter review.", report
