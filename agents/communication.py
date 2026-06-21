"""Communication Agent — synthesises all findings into a professional underwriter report."""

import anthropic
from utils.risk_scoring import peril_band

SYSTEM_PROMPT = """You are the PRISM Communication Agent — a senior insurance analyst.
Generate a professional risk assessment report for a luxury property underwriter.

OUTPUT FORMAT — follow this exact structure with exactly five sections, no more:

## 1. Executive Summary
3–4 sentences: address, overall risk band and score, dominant peril(s), underwriting recommendation.

## 2. Property Profile
A markdown table with two columns (Field | Detail). Rows in this order:
Address | Type | Bedrooms / Bathrooms | Land Area | Floor Area | Est. Value | Year Built | Council LGA | Stories
For any unknown field write exactly: N/A — do not add any other text to that cell.

## 3. Peril Assessment
One subsection per peril in this order: Bushfire · Flood · Storm · Erosion · Landslip
Format each heading as: **[Peril] — [Score]/100 — [Band]**
Use the exact band label provided in the prompt (e.g. LOW, LOW-MODERATE, MODERATE, HIGH, VERY HIGH).
Follow with 2–3 sentences on evidence and exposure drawn STRICTLY from the listed factors for that peril.
Do NOT reference data from other sections (property, environmental, or other perils) unless it appears in that peril's factor list.

## 4. Recommended Underwriting Action
State: Accept / Refer to Senior Underwriter / Decline.
Give the basis for the recommendation.
Then render the MANDATORY CONDITIONS exactly as provided — copy them verbatim, numbered in order.
Do NOT add, remove, or rephrase any condition.

## 5. Policy Conditions & Exclusions
Render the POLICY EXCLUSIONS exactly as provided — copy them verbatim as a bullet list.
Do NOT add, remove, or rephrase any exclusion.

Rules:
- Output begins directly with "## 1. Executive Summary" — no H1 header, no meta line before it.
- Five sections only. No section 6 or beyond.
- For null/unknown property fields use exactly "N/A" in the table — no other wording.
- Do not invent band labels. Use only the exact band string supplied in the prompt for each peril.
- Do not state or imply any premium loading percentage.
- Write for an experienced underwriter — no lay explanations.
- Always complete every sentence. Never end mid-word or mid-sentence."""


def _fmt(val, suffix=""):
    return f"{val}{suffix}" if val else "N/A"


def _build_mandatory_conditions(scores: dict, data_bundle: dict) -> list[str]:
    """Deterministic mandatory conditions derived from scores and property data."""
    perils = scores.get("perils", {})
    prop = data_bundle.get("get_property_data", {})

    erosion_score = perils.get("erosion", {}).get("score", 0)
    flood_score = perils.get("flood", {}).get("score", 0)
    value = prop.get("estimated_value_aud") or 0
    year_built = prop.get("year_built")

    conditions = []

    if erosion_score >= 50:
        conditions.append(
            "Coastal geotechnical specialist report — addressing current erosion trajectory, "
            "setback adequacy relative to the building footprint, and any existing or "
            "council-approved coastal protection infrastructure — must be obtained and reviewed "
            "prior to binding."
        )

    if not year_built and erosion_score >= 50:
        conditions.append(
            "Year of construction must be confirmed via council records, a current building "
            "certificate, or equivalent statutory documentation before binding — structural "
            "vintage is required to assess foundation specification and compliance with coastal "
            "construction standards applicable at time of build."
        )

    if year_built and year_built < 1950 and erosion_score >= 50:
        conditions.append(
            f"Independent structural engineer inspection required prior to binding — the property "
            f"was constructed in {year_built} (pre-war) and must be assessed for foundation "
            f"adequacy, original material deterioration, and compliance with current coastal "
            f"setback and structural standards given the HIGH erosion exposure."
        )

    if flood_score >= 40:
        conditions.append(
            "Independent flood engineer or hydrologist review required prior to binding — a formal "
            "flood report addressing inundation frequency, floor level adequacy, and "
            "property-specific flood exposure must be obtained."
        )

    if value >= 2_000_000:
        conditions.append(
            f"Current independent replacement cost valuation required prior to binding — the "
            f"estimated value of AUD ${value:,} must be validated by a qualified valuer, with "
            f"subsequent underwriter review."
        )

    return conditions


def _build_exclusions(scores: dict, data_bundle: dict) -> list[str]:
    """Deterministic policy exclusions derived from scores and property data."""
    perils = scores.get("perils", {})
    prop = data_bundle.get("get_property_data", {})
    satellite = data_bundle.get("get_vegetation_analysis", {})
    geo = data_bundle.get("get_geological_hazards", {})

    erosion_score = perils.get("erosion", {}).get("score", 0)
    flood_score = perils.get("flood", {}).get("score", 0)
    landslip_score = perils.get("landslip", {}).get("score", 0)
    bushfire_score = perils.get("bushfire", {}).get("score", 0)

    soil = (geo.get("soil_type") or "").lower()
    ndvi = satellite.get("ndvi_score") or 0
    year_built = prop.get("year_built")

    exclusions = []

    if erosion_score >= 50:
        exclusions.append(
            "**Coastal Erosion — Progressive Land Loss:** Any loss, damage, or liability arising "
            "from progressive coastal erosion, shoreline recession, or loss of land area is excluded, "
            "triggered by the HIGH erosion classification."
        )
        exclusions.append(
            "**Coastal Erosion — Foundation Undermining:** Structural damage attributable to "
            "erosion-induced undermining, scour, or destabilisation of foundations is excluded, "
            "triggered by the confirmed active coastal erosion zone classification."
        )

    if not year_built and erosion_score >= 50:
        exclusions.append(
            "**Structural Vintage Condition Precedent:** Coverage is conditional upon written "
            "confirmation of year of construction and underwriter assessment of setback and "
            "foundation compliance, triggered by the unknown build year on a HIGH erosion-risk "
            "coastal property."
        )

    if "sandy" in soil or "shrink-swell" in soil:
        exclusions.append(
            "**Shrink-Swell Soil — Ground Movement:** Loss or damage arising from soil shrinkage, "
            "swelling, or lateral movement attributable to the identified shrink-swell soil profile "
            "is excluded."
        )

    if landslip_score >= 15:
        exclusions.append(
            "**Landslip Sub-limit:** Any landslip or slope instability claim is subject to a "
            "sub-limit, triggered by clay-bearing soil instability risk."
        )

    if flood_score >= 15:
        exclusions.append(
            "**Flood Proximity Condition:** Coverage for flood-related loss is conditioned on the "
            "insured maintaining all stormwater and drainage infrastructure in serviceable condition, "
            "triggered by the GA hydrology proximity classification."
        )

    if bushfire_score >= 10 and ndvi > 0.4:
        exclusions.append(
            "**Vegetation Maintenance Condition:** Maintenance of defensible space and vegetation "
            "management around the structure is a policy condition, consistent with the identified "
            "vegetation density."
        )

    return exclusions


def run(client: anthropic.Anthropic, address: str, scores: dict, data_bundle: dict, validation: dict):
    """Run the Communication Agent. Yields (log_line, report_or_None) tuples."""
    yield "📝 Communication Agent activated — generating underwriter report...", None

    property_data = data_bundle.get("get_property_data", {})

    perils = scores.get("perils", {})

    def peril_line(name):
        p = perils.get(name, {})
        s = p.get("score", 0)
        return f"{s}/100 — {peril_band(s)} | Factors: {p.get('factors', [])}"

    val = property_data.get("estimated_value_aud")
    val_str = f"AUD ${val:,}" if val else "N/A"

    # Build conditions and exclusions deterministically — LLM renders them verbatim
    mandatory_conditions = _build_mandatory_conditions(scores, data_bundle)
    exclusions = _build_exclusions(scores, data_bundle)

    conditions_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(mandatory_conditions)) or "None."
    exclusions_text = "\n".join(f"- {e}" for e in exclusions) or "No specific exclusions triggered."

    underwriting_action = (
        "Refer to Senior Underwriter"
        if validation.get("human_review_required")
        else "Accept — Standard Terms"
    )
    review_reason = validation.get("human_review_reason") or ""

    prompt = f"""Generate the PRISM risk assessment report for:

ADDRESS: {address}
OVERALL RISK SCORE: {scores.get('overall_score')}/100 — {scores.get('risk_band')} RISK
CONFIDENCE: {scores.get('confidence')}

PERIL SCORES (use these exact band labels in section 3; draw ONLY from each peril's own factors):
- Bushfire: {peril_line('bushfire')}
- Flood: {peril_line('flood')}
- Storm: {peril_line('storm')}
- Erosion: {peril_line('erosion')}
- Landslip: {peril_line('landslip')}

PROPERTY DATA:
- Type: {_fmt(property_data.get('property_type'))}
- Bedrooms / Bathrooms: {_fmt(property_data.get('bedrooms'))} bed / {_fmt(property_data.get('bathrooms'))} bath
- Land area: {_fmt(property_data.get('land_area_sqm'), ' sqm')}
- Floor area: {_fmt(property_data.get('floor_area_sqm'), ' sqm')}
- Est. value: {val_str}
- Year built: {_fmt(property_data.get('year_built'))}
- Council LGA: {_fmt(property_data.get('council'))}
- Stories: {_fmt(property_data.get('stories'))}

UNDERWRITING ACTION: {underwriting_action}
BASIS: {review_reason or 'Risk within standard parameters.'}

MANDATORY CONDITIONS (render verbatim in section 4, numbered):
{conditions_text}

POLICY EXCLUSIONS (render verbatim as bullets in section 5):
{exclusions_text}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    report = response.content[0].text
    yield "✅ Report generated — ready for underwriter review.", report
