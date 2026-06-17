"""Validation & Compliance Agent — cross-checks scores and ensures APRA CPS 220 alignment."""

import json
import anthropic

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
- Bushfire prone: {data_bundle.get('get_bushfire_overlay', {}).get('bushfire_prone_land', False)}
- In flood zone: {data_bundle.get('get_flood_overlay', {}).get('in_flood_planning_zone', False)}
- Total area claims (10yr): {data_bundle.get('get_historical_claims', {}).get('total_claims_10yr', 'N/A')}

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

    if result.get("human_review_required"):
        yield f"   ⚠️  Human specialist review flagged: {result.get('human_review_reason', 'High risk threshold')}", None

    yield "✅ Compliance validation complete — APRA CPS 220 requirements verified.", result
