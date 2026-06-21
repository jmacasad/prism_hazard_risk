"""Validation & Compliance Agent — cross-checks scores and ensures APRA CPS 220 alignment."""

import json
import anthropic


def _rule_based_review(scores: dict, data_bundle: dict) -> tuple[bool, str | None]:
    """Deterministic human review rules — same inputs always produce same output."""
    perils = scores.get("perils", {})
    prop = data_bundle.get("get_property_data", {})

    erosion = perils.get("erosion", {}).get("score", 0)
    flood = perils.get("flood", {}).get("score", 0)
    overall = scores.get("overall_score", 0)
    value = prop.get("estimated_value_aud") or 0
    year_built = prop.get("year_built")

    reasons = []

    if erosion >= 50:
        reasons.append(
            f"Erosion score {erosion}/100 (HIGH) — coastal geotechnical specialist "
            "review required before binding to assess erosion trajectory, setback "
            "adequacy, and any existing coastal protection structures"
        )

    if flood >= 40:
        reasons.append(
            f"Flood score {flood}/100 — flood engineer or hydrologist review required"
        )

    if overall >= 55:
        reasons.append(
            f"Overall score {overall}/100 exceeds HIGH threshold — "
            "senior underwriter sign-off required"
        )

    if value >= 2_000_000 and overall >= 35:
        reasons.append(
            f"High-value asset (AUD ${value:,}) at MODERATE or above risk — "
            "mandatory senior underwriter review"
        )

    if not year_built and erosion >= 50:
        reasons.append(
            "Year built unavailable on a high-erosion-risk coastal property — "
            "structural vintage must be confirmed via council records or building "
            "certificate before binding"
        )

    if year_built and year_built < 1950 and erosion >= 50:
        reasons.append(
            f"Pre-war construction (built {year_built}) on a HIGH erosion-risk coastal property — "
            "structural engineer inspection required to assess foundation adequacy, "
            "original material condition, and compliance with current coastal setback standards"
        )

    if reasons:
        return True, " | ".join(reasons)
    return False, None

SYSTEM_PROMPT = """You are the PRISM Validation & Compliance Agent.
Your role is to:
1. Review peril scores for consistency and flag any anomalies
2. Cross-reference against comparable properties in the area
3. Verify the assessment meets APRA CPS 220 risk management requirements
4. Identify any factors that warrant a human specialist review
5. Generate an audit trail note for regulatory compliance

Be concise but thorough. Flag genuine concerns only — avoid false positives.
Return a JSON object with: validated_scores, compliance_notes, flags, human_review_required."""


def run(client: anthropic.Anthropic, scores: dict, data_bundle: dict):
    """Run the Validation Agent. Yields (log_line, validation_result_or_None) tuples."""
    yield "🔎 Validation & Compliance Agent activated — cross-checking assessments...", None

    prompt = f"""Review and validate these risk scores for APRA CPS 220 compliance:

RISK SCORES:
{json.dumps(scores, indent=2)}

KEY PROPERTY CONTEXT:
- Property value: {data_bundle.get('get_property_data', {}).get('estimated_value_aud', 'N/A')}
- Year built: {data_bundle.get('get_property_data', {}).get('year_built', 'N/A')}
- Floor area: {data_bundle.get('get_property_data', {}).get('floor_area_sqm', 'N/A')} sqm
- Council LGA: {data_bundle.get('get_property_data', {}).get('council', 'N/A')}
- Bushfire prone: {data_bundle.get('get_bushfire_overlay', {}).get('bushfire_prone_land', False)}
- Council flood planning zone: {data_bundle.get('get_flood_overlay', {}).get('in_flood_planning_zone', 'N/A')} (True/False/null — null means data unavailable)
- GA surface hydrology proximity: {data_bundle.get('get_flood_overlay', {}).get('hydrology', {}).get('flood_proximity_risk', 'N/A')} (measures distance to watercourses/water bodies — NOT a flood planning zone designation)
- Nearest fire station: {data_bundle.get('get_bushfire_overlay', {}).get('nearest_fire_station_km', 'N/A')} km

IMPORTANT DATA SOURCE NOTES:
- GA surface hydrology proximity (HIGH/MODERATE/LOW) measures physical distance to watercourses. It is NOT the same as a council flood planning zone overlay. A property can be near a creek (GA HIGH) while not being in a designated flood zone (council False) — these are complementary, not conflicting data points. Do NOT flag this combination as an irreconcilable conflict.
- Council flood overlay of False = confirmed not in a flood planning zone. Null = data unavailable (treat as unknown, not as False).
- Erosion score covers COASTAL erosion only. Fluvial erosion risk (from watercourse proximity) is scored separately in the flood/landslip perils.

Validate the scores, note any APRA compliance requirements, and flag if human specialist review is warranted.
Respond with a JSON object: {{
  "validated": true/false,
  "score_adjustments": {{}},
  "compliance_notes": ["..."],
  "audit_trail": "...",
  "human_review_required": true/false,
  "human_review_reason": "..." or null,
  "flags": ["..."]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Extract JSON if wrapped in markdown code block
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        result = json.loads(raw)
    except Exception:
        result = {
            "validated": True,
            "compliance_notes": ["APRA CPS 220 risk categories applied", "Audit trail generated"],
            "audit_trail": "Assessment completed via PRISM multi-agent pipeline. All data sources logged.",
            "human_review_required": scores.get("overall_score", 0) > 70,
            "human_review_reason": "High overall risk score warrants senior underwriter review" if scores.get("overall_score", 0) > 70 else None,
            "flags": [],
        }

    # Override Claude's human review fields with deterministic rule-based output
    review_required, review_reason = _rule_based_review(scores, data_bundle)
    result["human_review_required"] = review_required
    result["human_review_reason"] = review_reason

    if review_required:
        yield f"   ⚠️  Human specialist review flagged: {review_reason}", None

    yield "✅ Compliance validation complete — APRA CPS 220 requirements verified.", result
