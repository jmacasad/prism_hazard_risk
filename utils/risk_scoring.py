"""Peril score calculations and overall risk aggregation."""


def score_bushfire(satellite: dict, bushfire: dict, weather: dict) -> dict:
    score = 0
    factors = []

    # Structural / classification risk
    if bushfire.get("bushfire_prone_land"):
        score += 35
        factors.append(f"Bushfire Prone Land mapped ({bushfire.get('bpl_category')}) — structural risk")
    else:
        factors.append("Not mapped as Bushfire Prone Land — no structural bushfire classification")

    if bushfire.get("flame_zone"):
        score += 20
        factors.append("Flame Zone — highest BAL rating")

    if satellite.get("defensible_space_adequate") is False:
        score += 15
        factors.append(f"Defensible space {satellite.get('defensible_space_m')}m (minimum 20m required)")
    elif satellite.get("defensible_space_adequate") is True:
        score -= 5

    ndvi = satellite.get("ndvi_score", 0.4)
    if ndvi > 0.6:
        score += 15
        factors.append(f"High vegetation density (NDVI {ndvi})")
    elif ndvi > 0.4:
        score += 8
        factors.append(f"Moderate vegetation density (NDVI {ndvi})")

    # Ambient meteorological condition — applies region-wide, not property-specific
    fire_danger = weather.get("fire_danger", "MODERATE")
    danger_scores = {"CATASTROPHIC": 15, "EXTREME": 12, "SEVERE": 8, "HIGH": 5, "MODERATE": 2, "LOW-MODERATE": 0}
    score += danger_scores.get(fire_danger, 3)
    factors.append(f"Ambient fire danger rating: {fire_danger} (regional/seasonal — not property-specific)")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_flood(flood: dict, property_data: dict) -> dict:
    score = 0
    factors = []

    if flood.get("in_flood_planning_zone"):
        cat = flood.get("flood_category", "")
        if "High" in cat:
            score += 40
        elif "Medium" in cat:
            score += 25
        else:
            score += 12
        factors.append(f"Council flood overlay: {cat}")
    elif flood.get("in_flood_planning_zone") is None:
        factors.append("Council flood overlay: data unavailable — manual lookup required")

    hydro = flood.get("hydrology", {})
    flood_prox = hydro.get("flood_proximity_risk", "")
    if "HIGH" in flood_prox:
        score += 15
        wc = hydro.get("watercourses_within_1km", 0) or 0
        wb = hydro.get("water_bodies_within_1km", 0) or 0
        parts = []
        if wc:
            parts.append(f"{wc} watercourse{'s' if wc != 1 else ''}")
        if wb:
            parts.append(f"{wb} water bod{'ies' if wb != 1 else 'y'}")
        proximity_desc = ", ".join(parts) if parts else "water feature"
        factors.append(f"GA hydrology: HIGH proximity — {proximity_desc} within 1km")
    elif "MODERATE" in flood_prox:
        score += 8
        wc = hydro.get("watercourses_within_1km", 0) or 0
        wb = hydro.get("water_bodies_within_1km", 0) or 0
        parts = []
        if wc:
            parts.append(f"{wc} watercourse{'s' if wc != 1 else ''}")
        if wb:
            parts.append(f"{wb} water bod{'ies' if wb != 1 else 'y'}")
        proximity_desc = ", ".join(parts) if parts else "water feature"
        factors.append(f"GA hydrology: MODERATE proximity — {proximity_desc} within 1km")

    floor_diff = flood.get("floor_level_above_flood_m")
    if floor_diff is not None:
        if floor_diff < 0:
            score += 20
            factors.append(f"Floor level {abs(floor_diff):.1f}m BELOW 1-in-100-year flood level")
        elif floor_diff < 0.5:
            score += 10
            factors.append("Floor level marginally above flood benchmark")
        else:
            score -= 5
            factors.append(f"Floor level {floor_diff:.1f}m above flood benchmark — positive factor")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_storm(weather: dict, property_data: dict) -> dict:
    score = 5  # Base storm exposure for all Australian properties
    factors = []

    # Cyclone / tropical context
    cyclone_risk = weather.get("cyclone_risk", "") or ""
    if "EXTREME" in cyclone_risk:
        score += 30
        factors.append(f"Cyclone risk: {cyclone_risk}")
    elif "HIGH" in cyclone_risk:
        score += 20
        factors.append(f"Cyclone risk: {cyclone_risk}")
    elif "MODERATE" in cyclone_risk:
        score += 10
        factors.append(f"Cyclone risk: {cyclone_risk}")
    elif "NEGLIGIBLE" in cyclone_risk or "LOW" in cyclone_risk:
        factors.append(f"Cyclone risk: {cyclone_risk} — outside tropical belt")

    # Current wind is an observation, not a risk driver — storm risk is assessed on return-period
    # wind events (1-in-50 year), not today's conditions.
    wind_kmh = weather.get("wind_speed_kmh", 0) or 0
    wind_dir = weather.get("wind_dir", "") or ""
    if wind_kmh:
        factors.append(f"Observed wind {wind_kmh} km/h {wind_dir} (contextual — not scored)")
    else:
        factors.append("Current wind speed: not available")

    # Construction vulnerability
    roof = property_data.get("roof_type", "") or ""
    if "Tile" in roof:
        score += 10
        factors.append(f"{roof} — higher wind uplift risk than metal")

    year_built = property_data.get("year_built") or 0
    if year_built and year_built < 1950:
        score += 20
        factors.append(f"Built {year_built} — pre-war construction, no engineered wind resistance standards")
    elif year_built and year_built < 1990:
        score += 10
        factors.append(f"Built {year_built} — pre-modern wind resistance standards")
    elif year_built:
        factors.append(f"Built {year_built} — post-1990 wind resistance standards apply")

    # Temperature / humidity context
    temp = weather.get("temperature_c")
    humidity = weather.get("relative_humidity")
    if temp is not None and humidity is not None:
        factors.append(f"Conditions: {temp}°C, {humidity}% humidity")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_erosion(geoscience: dict, satellite: dict, flood_data: dict = None) -> dict:
    """Coastal erosion only — GA Smartline data.
    Fluvial/soil/watercourse risk belongs to flood and landslip perils."""
    score = 0
    factors = []
    is_coastal = geoscience.get("is_coastal", False)

    if not is_coastal:
        factors.append("Not a coastal property — coastal erosion peril not applicable")
        return {"score": 0, "factors": factors}

    # Coastal erosion classification (GA Smartline)
    erosion = geoscience.get("coastal_erosion_risk", "LOW")
    if "HIGH" in erosion:
        score += 45
        factors.append(erosion)
    elif "MODERATE" in erosion:
        score += 25
        factors.append(erosion)
    else:
        factors.append(f"Coastal erosion risk: {erosion}")

    # Sandy/soft soil amplifies coastal erosion (coastal context only)
    soil = geoscience.get("soil_type", "")
    if "Sandy" in soil or "shrink-swell" in soil.lower():
        score += 15
        factors.append(f"Soil type: {soil} — elevated coastal erodibility")

    # Bare soil amplifies erosion at coastal sites
    bare_soil = satellite.get("bare_soil_pct", 0) or 0
    if bare_soil >= 40:
        score += 8
        factors.append(f"{bare_soil}% bare soil — unprotected coastal surface")

    factors.append("GA Smartline confirmed coastal classification")
    return {"score": min(100, max(0, score)), "factors": factors}


def score_landslip(geoscience: dict, property_data: dict) -> dict:
    score = 5
    factors = []

    soil = geoscience.get("soil_type", "")
    if "Clay" in soil:
        score += 15
        factors.append("Clay-bearing soil — shrink-swell and slope instability risk")
    elif "Alluvial" in soil:
        score += 10
        factors.append(f"Alluvial soil — variable bearing capacity, subsidence and settlement risk")

    seismic = geoscience.get("seismic_hazard_pga", 0.05)
    if seismic and seismic > 0.1:
        score += 10
        factors.append(f"Moderate seismic hazard PGA: {seismic}")

    return {"score": min(100, max(0, score)), "factors": factors}


def peril_band(score: int) -> str:
    if score <= 10:
        return "LOW"
    elif score <= 30:
        return "LOW-MODERATE"
    elif score <= 50:
        return "MODERATE"
    elif score <= 70:
        return "HIGH"
    return "VERY HIGH"


def aggregate_scores(perils: dict) -> dict:
    weights = {
        "bushfire": 0.30,
        "flood": 0.28,
        "storm": 0.22,
        "erosion": 0.12,
        "landslip": 0.08,
    }
    overall = sum(perils[p]["score"] * weights[p] for p in weights)
    overall = round(overall, 1)

    # Risk band thresholds
    if overall >= 75:
        risk_band = "VERY HIGH"
        band_lo, band_hi = 75, 100
        load_lo, load_hi = 65, 90
    elif overall >= 55:
        risk_band = "HIGH"
        band_lo, band_hi = 55, 75
        load_lo, load_hi = 35, 65
    elif overall >= 35:
        risk_band = "MODERATE"
        band_lo, band_hi = 35, 55
        load_lo, load_hi = 15, 35
    else:
        risk_band = "LOW-MODERATE"
        band_lo, band_hi = 0, 35
        load_lo, load_hi = 0, 15

    return {
        "overall_score": overall,
        "risk_band": risk_band,
        "perils": perils,
    }
