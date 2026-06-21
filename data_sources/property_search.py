"""Property data via Gemini + Google Search grounding — replaces Tavily stack."""

import os
import json
import re

# Per-assessment cache — keyed by address
_cache: dict[str, dict] = {}

# State-specific planning portals for flood and bushfire overlays
_STATE_PLANNING = {
    "NSW": {
        "flood": (
            "NSW Planning Portal (flood.nsw.gov.au) or the relevant council's flood planning certificate. "
            "Search '[council name] flood planning certificate' or '[address] flood overlay NSW planning portal'."
        ),
        "bushfire": (
            "NSW Rural Fire Service Bushfire Prone Land Map (rfs.nsw.gov.au/check-your-risk). "
            "Search '[address] bushfire prone land NSW RFS'."
        ),
    },
    "VIC": {
        "flood": (
            "VicPlan (planning.vic.gov.au/tools-and-resources/vicplan) or the relevant council's planning scheme "
            "flood overlay (LSIO/SBO/FO). Search '[address] flood overlay Victorian planning scheme' or "
            "'[council name] land subject to inundation overlay'."
        ),
        "bushfire": (
            "Bushfire Management Overlay (BMO) in the relevant Victorian planning scheme, administered by DEECA. "
            "Search '[address] bushfire management overlay VIC planning scheme' or check VicPlan."
        ),
    },
    "QLD": {
        "flood": (
            "Queensland Development Assessment System or the relevant council's flood mapping portal. "
            "Search '[address] flood overlay QLD development assessment' or '[council] flood awareness map'."
        ),
        "bushfire": (
            "QFES Bushfire Hazard Assessment or the relevant council's planning scheme. "
            "Search '[address] bushfire hazard QLD planning scheme'."
        ),
    },
    "SA": {
        "flood": (
            "PlanSA planning portal (plan.sa.gov.au) — Flood Hazard Overlay. "
            "Search '[address] flood hazard overlay PlanSA'."
        ),
        "bushfire": (
            "PlanSA Bushfire Risk Overlay or SA CFS. "
            "Search '[address] bushfire risk overlay PlanSA'."
        ),
    },
    "WA": {
        "flood": (
            "WA Planning Commission or the relevant local government planning scheme flood provisions. "
            "Search '[address] flood risk WA local planning scheme'."
        ),
        "bushfire": (
            "DFES Bushfire Prone Area mapping (dfes.wa.gov.au). "
            "Search '[address] bushfire prone area WA DFES'."
        ),
    },
    "TAS": {
        "flood": (
            "The relevant council's planning scheme or Land Tasmania flood mapping. "
            "Search '[address] flood zone Tasmania planning scheme'."
        ),
        "bushfire": (
            "Tasmania Fire Service or the relevant council's planning scheme bushfire provisions. "
            "Search '[address] bushfire prone area Tasmania'."
        ),
    },
    "ACT": {
        "flood": (
            "ACTmapi (actmapi.act.gov.au) — Flood Area Overlay. "
            "Search '[address] flood overlay ACT planning'."
        ),
        "bushfire": (
            "ACT Emergency Services Agency bushfire risk mapping. "
            "Search '[address] bushfire risk ACT planning directorate'."
        ),
    },
    "NT": {
        "flood": (
            "NT Planning or the relevant local government flood provisions. "
            "Search '[address] flood risk NT planning scheme'."
        ),
        "bushfire": (
            "NT Fire and Rescue Service bushfire risk mapping. "
            "Search '[address] bushfire risk NT'."
        ),
    },
}


def _extract_state(address: str) -> str | None:
    """Extract Australian state/territory abbreviation from address string."""
    match = re.search(r'\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b', address.upper())
    return match.group(1) if match else None


def _gemini_search(address: str) -> dict:
    """Query Gemini with Google Search grounding. Returns structured property dict. Cached."""
    if address in _cache:
        return _cache[address]

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        result = {}
        _cache[address] = result
        return result

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        state = _extract_state(address)
        planning = _STATE_PLANNING.get(state, {})
        flood_source = planning.get(
            "flood",
            "the relevant state or council planning portal flood overlay or planning certificate."
        )
        bushfire_source = planning.get(
            "bushfire",
            "the relevant state fire authority bushfire prone land mapping."
        )

        prompt = f"""You are a property data extraction assistant for Australian insurance underwriting.

Search for and extract property details for this exact address: {address}

Search specifically for:
- Property listing pages (realestate.com.au, domain.com.au, property.com.au)
- Estimated value or appraisal (look for phrases like "estimated value", "appraised between", "property value", "median valuation", "price estimate")
- Property configuration (bedrooms, bathrooms, parking)
- Land and floor area
- Year of construction or build era — look for phrases like "built in", "built circa", "c.", "Federation-era", "Victorian-era", "Edwardian", "interwar", "post-war", "constructed in", "heritage-listed". Convert any era or approximate description to the best integer year (e.g. "Federation-era circa 1905" → 1905, "built c.1920" → 1920, "interwar" → 1935).
- Flood overlay: search {flood_source}
- Bushfire overlay: search {bushfire_source}

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "property": {{
    "land_area_sqm": <integer or null>,
    "floor_area_sqm": <integer or null>,
    "property_type": <"House"|"Unit"|"Apartment"|"Townhouse"|"Villa"|"Duplex"|null>,
    "estimated_value_aud": <integer — if a range like $3.2M-$3.95M use the midpoint → 3575000. IMPORTANT: do not leave this null if a value or range appears in the search results>,
    "stories": <integer or null>,
    "bedrooms": <integer or null>,
    "bathrooms": <integer or null>,
    "year_built": <4-digit integer or null — extract from ANY historical description: "built circa 1905" → 1905, "Federation-era" → 1905, "Victorian-era" → 1890, "Edwardian" → 1910, "interwar" → 1930, "post-war" → 1950, "c.1920" → 1920, "early 1900s" → 1905. Use the best integer approximation available — do NOT return null if a historical era or approximate year appears in the results>,
    "council": <full council name string or null>
  }},
  "flood": {{
    "in_flood_planning_zone": <true|false|null — null only if no mention at all>,
    "flood_category": <string or null>
  }},
  "bushfire": {{
    "bushfire_prone_land": <true|false|null — null only if no mention at all>,
    "bpl_category": <string or null>
  }}
}}

Rules:
- Use null ONLY when data is genuinely not found in search results.
- For estimated value: convert any range to its integer midpoint ($3.2M–$3.95M → 3575000). If the estimated value is paywalled (shown as "$X,XXX,XXX") use the most recent sale price or any unit estimate from the same complex instead.
- For multi-unit complexes where the bare address has multiple units, use data from the 4-bedroom or largest unit as representative.
- "n/a" year built → null. "circa", "c.", "approximately", "early/mid/late [decade]" → extract the best integer year approximation, do NOT return null.
- Search the exact address only — do not substitute a different property."""

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw.strip())
        _cache[address] = result
        return result

    except Exception as e:
        result = {}
        _cache[address] = result
        return result


def _fetch_year_built(address: str) -> int | None:
    """Targeted fallback: searches specifically for construction era/year when main call misses it."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        prompt = f"""Search for the year of construction for this Australian property: {address}
Look specifically for: "built circa", "built in", "c.", "Federation-era", "Victorian-era", "Edwardian", "interwar", "post-war", heritage listings, council records.
Return ONLY valid JSON (no markdown): {{"year_built": <integer year or null>, "source": <exact phrase found or null>}}
Convert era descriptions to best integer: Federation-era → 1905, Victorian → 1890, Edwardian → 1910, interwar → 1930, post-war → 1950."""
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        raw = response.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip()).get("year_built")
    except Exception:
        return None


def fetch_property_data(address: str) -> dict | None:
    data = _gemini_search(address)
    prop = data.get("property", {})
    if not any(prop.get(k) for k in ["bedrooms", "floor_area_sqm", "estimated_value_aud", "land_area_sqm", "property_type"]):
        return None
    # If main search didn't capture year_built, run a targeted construction-era search
    year_built = prop.get("year_built")
    if not year_built:
        year_built = _fetch_year_built(address)
    return {
        "source": "Google Search (Gemini grounded)",
        "land_area_sqm": prop.get("land_area_sqm"),
        "floor_area_sqm": prop.get("floor_area_sqm"),
        "property_type": prop.get("property_type"),
        "estimated_value_aud": prop.get("estimated_value_aud"),
        "stories": prop.get("stories"),
        "bedrooms": prop.get("bedrooms"),
        "bathrooms": prop.get("bathrooms"),
        "year_built": year_built,
        "council": prop.get("council"),
    }


def fetch_flood_overlay(address: str) -> dict | None:
    data = _gemini_search(address)
    flood = data.get("flood", {})
    in_zone = flood.get("in_flood_planning_zone")
    if in_zone is None:
        return None
    return {
        "source": "Google Search (Gemini grounded)",
        "in_flood_planning_zone": in_zone,
        "flood_category": flood.get("flood_category") or ("No Overlay" if not in_zone else None),
    }


def fetch_bushfire_overlay(address: str) -> dict | None:
    data = _gemini_search(address)
    bushfire = data.get("bushfire", {})
    in_zone = bushfire.get("bushfire_prone_land")
    if in_zone is None:
        return None
    return {
        "source": "Google Search (Gemini grounded)",
        "bushfire_prone_land": in_zone,
        "bpl_category": bushfire.get("bpl_category"),
    }


def clear_cache():
    _cache.clear()
