"""Peril score calculations and overall risk aggregation."""


def score_bushfire(satellite: dict, bushfire: dict, weather: dict) -> dict:
    score = 0
    factors = []

    if bushfire.get("bushfire_prone_land"):
        score += 35
        factors.append(f"Property is on Bushfire Prone Land ({bushfire.get('bpl_category')})")
    if bushfire.get("flame_zone"):
        score += 20
        factors.append("Located in Flame Zone — highest BAL rating")

    if not satellite.get("defensible_space_adequate"):
        score += 15
        factors.append(f"Defensible space only {satellite.get('defensible_space_m')}m (minimum 20m required)")
    else:
        score -= 5

    ndvi = satellite.get("ndvi_score", 0.4)
    if ndvi > 0.6:
        score += 15
        factors.append(f"High vegetation density (NDVI {ndvi})")
    elif ndvi > 0.4:
        score += 8
        factors.append(f"Moderate vegetation density (NDVI {ndvi})")

    fire_danger = weather.get("fire_danger", "MODERATE")
    danger_scores = {"CATASTROPHIC": 15, "EXTREME": 12, "SEVERE": 8, "HIGH": 5, "MODERATE": 2, "LOW-MODERATE": 0}
    score += danger_scores.get(fire_danger, 3)
    factors.append(f"Current fire danger rating: {fire_danger}")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_flood(flood: dict, property_data: dict, claims: dict) -> dict:
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

    if flood.get("overland_flow_path"):
        score += 12
        factors.append("Property on overland flow path")

    if flood.get("stormwater_infrastructure") == "Undersized":
        score += 8
        factors.append("Stormwater infrastructure rated undersized")

    flood_claims = claims.get("flood_claims", 0)
    if flood_claims >= 5:
        score += 15
        factors.append(f"{flood_claims} flood claims in 5km radius (10yr)")
    elif flood_claims >= 2:
        score += 8

    return {"score": min(100, max(0, score)), "factors": factors}


def score_storm(weather: dict, property_data: dict, claims: dict) -> dict:
    score = 20  # Base for coastal properties
    factors = ["Coastal location — elevated storm surge exposure"]

    wind_kmh = weather.get("wind_speed_kmh", 0) or 0
    if wind_kmh > 60:
        score += 15
        factors.append(f"Current wind speed {wind_kmh} km/h — elevated")

    roof = property_data.get("roof_type", "")
    if "Tile" in roof:
        score += 10
        factors.append(f"{roof} — higher wind uplift risk than metal")

    storm_claims = claims.get("storm_claims", 0)
    if storm_claims >= 6:
        score += 20
        factors.append(f"{storm_claims} storm claims in 5km radius (10yr)")
    elif storm_claims >= 3:
        score += 10

    year_built = property_data.get("year_built", 2000)
    if year_built < 1990:
        score += 10
        factors.append(f"Built {year_built} — pre-modern wind resistance standards")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_erosion(geoscience: dict, satellite: dict) -> dict:
    score = 0
    factors = []

    erosion = geoscience.get("coastal_erosion_risk", "LOW")
    if "HIGH" in erosion:
        score += 45
        factors.append(erosion)
    elif "MODERATE" in erosion:
        score += 25
        factors.append(erosion)

    soil = geoscience.get("soil_type", "")
    if "Sandy" in soil or "shrink-swell" in soil.lower():
        score += 15
        factors.append(f"Soil type: {soil}")

    return {"score": min(100, max(0, score)), "factors": factors}


def score_landslip(geoscience: dict, property_data: dict) -> dict:
    score = 5
    factors = []

    soil = geoscience.get("soil_type", "")
    if "Clay" in soil:
        score += 15
        factors.append(f"Clay-bearing soil — slope instability risk")

    seismic = geoscience.get("seismic_hazard_pga", 0.05)
    if seismic and seismic > 0.1:
        score += 10
        factors.append(f"Moderate seismic hazard PGA: {seismic}")

    return {"score": min(100, max(0, score)), "factors": factors}


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

    if overall >= 75:
        risk_band = "VERY HIGH"
        premium_loading = "65–90%"
        confidence = "81%"
    elif overall >= 55:
        risk_band = "HIGH"
        premium_loading = "35–65%"
        confidence = "85%"
    elif overall >= 35:
        risk_band = "MODERATE"
        premium_loading = "15–35%"
        confidence = "88%"
    else:
        risk_band = "LOW-MODERATE"
        premium_loading = "0–15%"
        confidence = "91%"

    return {
        "overall_score": overall,
        "risk_band": risk_band,
        "premium_loading": premium_loading,
        "confidence": confidence,
        "perils": perils,
    }
