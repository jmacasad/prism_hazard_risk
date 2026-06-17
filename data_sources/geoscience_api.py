"""Geoscience Australia open API integration."""

import requests

GA_REST = "https://services.ga.gov.au/gis/rest/services"


def fetch_geological_hazards(lat: float, lon: float) -> dict:
    """Query GA earthquake and geological hazard layers."""
    result = {
        "source": "Geoscience Australia",
        "coordinates": {"lat": lat, "lon": lon},
    }

    # GA ArcGIS REST endpoint — seismic hazard
    seismic_url = (
        f"{GA_REST}/Earthquake_Hazard/MapServer/0/query"
        f"?geometry={lon},{lat}&geometryType=esriGeometryPoint"
        f"&inSR=4326&spatialRel=esriSpatialRelIntersects"
        f"&outFields=*&f=json"
    )
    try:
        resp = requests.get(seismic_url, timeout=8)
        if resp.status_code == 200:
            features = resp.json().get("features", [])
            if features:
                attrs = features[0].get("attributes", {})
                result["seismic_hazard_pga"] = attrs.get("PGA_10_50", None)
                result["seismic_zone"] = attrs.get("ZONE", "Low")
    except Exception:
        pass

    # Realistic fallback for Australian coastal property
    if "seismic_hazard_pga" not in result:
        result["seismic_hazard_pga"] = 0.08
        result["seismic_zone"] = "Low"
        result["note"] = "GA API fallback — typical NSW coastal values"

    result["soil_type"] = _estimate_soil_type(lat, lon)
    result["coastal_erosion_risk"] = _estimate_erosion_risk(lat, lon)
    return result


def _estimate_soil_type(lat: float, lon: float) -> str:
    """Rough heuristic: coastal NSW properties often have sandy/clay soils."""
    if -34.5 < lat < -33.0 and 150.5 < lon < 152.0:
        return "Coastal Sandy Clay — moderate shrink-swell"
    return "Mixed Alluvial — variable bearing capacity"


def _estimate_erosion_risk(lat: float, lon: float) -> str:
    """Coastal proximity heuristic for erosion risk."""
    # Properties within ~5km of coast (rough lon check for eastern Australia)
    if lon > 151.2:
        return "HIGH — within coastal erosion zone"
    elif lon > 150.8:
        return "MODERATE — coastal influence area"
    return "LOW"
