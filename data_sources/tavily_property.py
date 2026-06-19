"""Real property data via Tavily web search — replaces simulated CoreLogic/overlay data where possible."""

import os
import re

# Module-level cache so one Tavily search covers all tool calls in the same assessment
_cache: dict[str, dict] = {}


def _parse_land_area(text: str) -> int | None:
    patterns = [
        r'land[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2|sq\s*m)',
        r'(\d[\d,]*)\s*(?:sqm|m²|m2|sq\s*m)\s+land',
        r'lot\s+size[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
        r'block\s+size[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
        r'sits\s+on\s+a\s+([\d,]+)\s*(?:sqm|m²|m2)',
        r'(\d[\d,]*)\s*(?:sqm|m²|m2)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1).replace(',', ''))
            if 100 <= val <= 500_000:
                return val
    return None


def _parse_floor_area(text: str) -> int | None:
    # Only match when explicitly labelled — avoids confusing land size for floor area
    patterns = [
        r'building\s+size[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
        r'floor\s+area[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
        r'house\s+size[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
        r'internal\s+(?:area|size)[:\s]+(\d[\d,]*)\s*(?:sqm|m²|m2)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = int(match.group(1).replace(',', ''))
            if 50 <= val <= 5_000:
                return val
    return None


def _parse_property_type(text: str) -> str | None:
    # Check unambiguous rural/multi types first, then House, then unit/apartment last
    for t in ['Acreage', 'Rural', 'Townhouse', 'Villa', 'Duplex']:
        if t.lower() in text.lower():
            return t
    if re.search(r'\bhouse\b', text, re.IGNORECASE):
        return 'House'
    for t in ['Apartment', 'Unit']:
        if re.search(rf'\b{t}\b', text, re.IGNORECASE):
            return t
    return None


def _parse_estimated_value(text: str) -> int | None:
    def to_int(val: str, suffix: str | None) -> int:
        v = float(val.replace(',', ''))
        return int(v * 1_000_000) if suffix else int(v)

    # "estimated property value ... is $1,772,000" (realestate.com.au)
    match = re.search(r'estimated\s+property\s+value[^$]{0,80}\$([\d,]+)', text, re.IGNORECASE)
    if match:
        val = int(match.group(1).replace(',', ''))
        if val > 50_000:
            return val

    # "$1,772,000 estimated value" (property.com.au)
    match = re.search(r'\$([\d,]+)\s+estimated\s+value', text, re.IGNORECASE)
    if match:
        val = int(match.group(1).replace(',', ''))
        if val > 50_000:
            return val

    # "between $2.89m and $3.73m"
    match = re.search(
        r'between\s+\$([\d,.]+)\s*([Mm])?\s+and\s+\$([\d,.]+)\s*([Mm])?',
        text, re.IGNORECASE
    )
    if match:
        low = to_int(match.group(1), match.group(2))
        high = to_int(match.group(3), match.group(4))
        if low > 50_000:
            return (low + high) // 2

    # Dash range e.g. $850,000 – $935,000 or $2.89m – $3.73m
    match = re.search(r'\$([\d,.]+)\s*([Mm])?\s*[-–]\s*\$([\d,.]+)\s*([Mm])?', text)
    if match:
        low = to_int(match.group(1), match.group(2))
        high = to_int(match.group(3), match.group(4))
        if low > 50_000:
            return (low + high) // 2

    # Nearest dollar to "estimate" / "value"
    match = re.search(
        r'(?:estimate[d]?|value|worth)[^\$]{0,30}\$([\d,.]+)\s*([Mm])?',
        text, re.IGNORECASE
    )
    if match:
        return to_int(match.group(1), match.group(2))

    # Plain million e.g. $1.2M (last resort)
    match = re.search(r'\$([\d.]+)\s*(?:million|[Mm])', text, re.IGNORECASE)
    if match:
        return int(float(match.group(1)) * 1_000_000)

    return None


def _parse_stories(text: str) -> int | None:
    if re.search(r'single[\s-]storey|one[\s-]storey|1[\s-]storey', text, re.IGNORECASE):
        return 1
    if re.search(r'double[\s-]storey|two[\s-]storey|2[\s-]storey', text, re.IGNORECASE):
        return 2
    if re.search(r'triple[\s-]storey|three[\s-]storey|3[\s-]storey', text, re.IGNORECASE):
        return 3
    return None


def _parse_flood_overlay(text: str) -> bool | None:
    clean = re.sub(r'\*+', '', text)
    if re.search(
        r'not\s+located\s+within\s+a\s+flood'
        r'|no\s+flood\s+(?:or\s+\w+\s+)?overlays?'
        r'|no\s+flood\s+zones?'
        r'|not\s+in\s+a\s+flood'
        r'|no\s+(?:recorded\s+)?flood\s+overlays?',
        clean, re.IGNORECASE
    ):
        return False
    if re.search(r'flood\s+overlays?|in\s+a\s+flood\s+zone|flood\s+prone\s+land|flood\s+planning\s+area', clean, re.IGNORECASE):
        return True
    return None


def _parse_bushfire_overlay(text: str) -> bool | None:
    clean = re.sub(r'\*+', '', text)
    if re.search(
        r'bushfire\s+overlays?|bushfire\s+prone|bushfire\s+risk\s+area'
        r'|fire\s+prone\s+land|BAL\s+rating|detected\s+(?:a\s+)?bushfire'
        r'|located\s+within\s+a\s+bushfire',
        clean, re.IGNORECASE
    ):
        return True
    if re.search(
        r'not\s+(?:located\s+within\s+a\s+)?bushfire|no\s+(?:recorded\s+)?bushfire|no\s+fire\s+overlays?',
        clean, re.IGNORECASE
    ):
        return False
    return None


def _search_tavily(address: str) -> tuple[str, str]:
    """Run a single Tavily search. Returns (top_result_content, all_combined_content). Cached per address."""
    if address in _cache:
        return _cache[address]

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        _cache[address] = ("", "")
        return ("", "")

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(
            query=f"{address} property details land size floor level storey flood overlay bushfire overlay estimated value",
            max_results=5,
            search_depth="basic",
        )
        items = results.get("results", [])
        top = items[0].get("content", "") if items else ""
        combined = " ".join(r.get("content", "") for r in items)
        _cache[address] = (top, combined)
        return (top, combined)
    except Exception:
        _cache[address] = ("", "")
        return ("", "")


def fetch_property_data_tavily(address: str) -> dict | None:
    """Extract property details from Tavily search. Physical attributes from top result only
    (avoids neighbouring property noise); value from combined (may be in any result)."""
    top, combined = _search_tavily(address)
    if not top and not combined:
        return None

    land_area = _parse_land_area(top)
    property_type = _parse_property_type(top)
    stories = _parse_stories(top)
    # Labeled fields are safe to pull from combined — specific enough to avoid neighbour noise
    floor_area = _parse_floor_area(combined)
    estimated_value = _parse_estimated_value(combined)

    if not any([land_area, floor_area, property_type, estimated_value, stories]):
        return None

    return {
        "source": "Tavily Web Search (live)",
        "land_area_sqm": land_area,
        "floor_area_sqm": floor_area,
        "property_type": property_type,
        "estimated_value_aud": estimated_value,
        "stories": stories,
    }


def fetch_flood_overlay_tavily(address: str) -> dict | None:
    """Extract flood overlay status from all Tavily results."""
    _, combined = _search_tavily(address)
    if not combined:
        return None

    in_flood_zone = _parse_flood_overlay(combined)
    if in_flood_zone is None:
        return None

    result = {
        "source": "Tavily Web Search (live) + Simulated",
        "in_flood_planning_zone": in_flood_zone,
    }
    if not in_flood_zone:
        result["flood_category"] = "No Overlay"

    return result


def fetch_bushfire_overlay_tavily(address: str) -> dict | None:
    """Extract bushfire overlay status from all Tavily results."""
    _, combined = _search_tavily(address)
    if not combined:
        return None

    in_bushfire_zone = _parse_bushfire_overlay(combined)
    if in_bushfire_zone is None:
        return None

    return {
        "source": "Tavily Web Search (live) + Simulated",
        "bushfire_prone_land": in_bushfire_zone,
    }


def clear_cache():
    """Call between assessments if needed."""
    _cache.clear()
