"""Geoscience Australia Digital Atlas API integrations."""

import math
import requests

GA_REST = "https://services.ga.gov.au/gis/rest/services"


def fetch_coastal_geomorphology(lat: float, lon: float) -> dict:
    """Query Smartline for coastal geomorphology within 500m of property."""
    km = 0.5
    lat_d = km / 111.0
    lon_d = km / (111.0 * math.cos(math.radians(abs(lat))))
    url = f"{GA_REST}/Geomorphology_Smartline/MapServer/10/query"
    params = {
        "geometry": f"{lon - lon_d},{lat - lat_d},{lon + lon_d},{lat + lat_d}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "backprof_v,sandy_n,dunes_n,softrock_n,hardrock_n,backprox_v",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if features:
            attrs_list = [f["attributes"] for f in features]
            has_sandy = any(a.get("sandy_n", "000") not in ("000", None) for a in attrs_list)
            has_dunes = any(a.get("dunes_n", "000") not in ("000", None) for a in attrs_list)
            has_softrock = any(a.get("softrock_n", "000") not in ("000", None) for a in attrs_list)
            has_hardrock = any(a.get("hardrock_n", "000") not in ("000", None) for a in attrs_list)
            coastal_profile = features[0]["attributes"].get("backprof_v") or "Unclassified"
            # Collect all backing profile values to detect urban/developed shorelines
            backing_profiles = [a.get("backprof_v") for a in attrs_list if a.get("backprof_v")]
            erosion_risk = _geomorphology_to_erosion_risk(
                has_sandy, has_dunes, has_softrock, has_hardrock, coastal_profile, backing_profiles
            )
            return {
                "source": "GA Smartline (live)",
                "coastal_profile": coastal_profile,
                "has_sandy_shore": has_sandy,
                "has_dune_coast": has_dunes,
                "coastal_erosion_risk": erosion_risk,
                "is_coastal": True,
            }
        return {
            "source": "GA Smartline (live)",
            "coastal_profile": None,
            "coastal_erosion_risk": "LOW",
            "is_coastal": False,
        }
    except Exception:
        return {"source": "GA Smartline (fallback)", "coastal_profile": None, "coastal_erosion_risk": None}


def _geomorphology_to_erosion_risk(
    has_sandy: bool,
    has_dunes: bool,
    has_softrock: bool,
    has_hardrock: bool,
    profile: str,
    backing_profiles: list = None,
) -> str:
    # Urban or developed backing indicates property is set back from an active shoreline.
    # Sheltered harbour beaches with residential/urban backing have fundamentally different
    # erosion dynamics than open-ocean sandy coasts — cap at MODERATE in that case.
    is_urban_backed = any(
        any(kw in (bp or "").lower() for kw in ("urban", "developed", "residential", "built", "anthropogenic", "infrastructure"))
        for bp in (backing_profiles or [])
    )

    if has_dunes:
        # Dune systems are high erosion regardless of backing — dune migration risk persists
        return "HIGH — dune coast, active erosion zone"
    elif has_sandy:
        if is_urban_backed:
            # Sandy but sheltered harbour / urban backing: established suburb with low active erosion front
            return "MODERATE — sandy coast, sheltered by urban/developed backing"
        return "HIGH — sandy coast, active erosion zone"
    elif has_softrock:
        return "MODERATE — soft rock coast, coastal erosion risk"
    elif has_hardrock:
        return "LOW — hard rock/cliff coast, minimal erosion risk"
    profile_lower = (profile or "").lower()
    if "beach" in profile_lower or "bay" in profile_lower or "low" in profile_lower:
        return "MODERATE — coastal influence area"
    elif "cliff" in profile_lower or "high" in profile_lower:
        return "LOW — cliffed coast, minimal erosion risk"
    return "MODERATE — coastal influence area"


def fetch_nearest_fire_station(lat: float, lon: float) -> dict:
    """Find nearest fire station using GA Emergency Management Facilities."""
    nearest_km = None
    station_type = None

    for layer_id, label in [(3, "Metro Fire Station"), (4, "Rural Fire Station")]:
        url = f"{GA_REST}/Emergency_Management_Facilities/MapServer/{layer_id}/query"
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": "30000",
            "units": "esriSRUnit_Meter",
            "outFields": "objectid",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            features = resp.json().get("features", [])
            for feat in features:
                geom = feat.get("geometry", {})
                fx, fy = geom.get("x"), geom.get("y")
                if fx is not None and fy is not None:
                    dist_km = _haversine_km(lat, lon, fy, fx)
                    if nearest_km is None or dist_km < nearest_km:
                        nearest_km = dist_km
                        station_type = label
        except Exception:
            pass

    return {
        "source": "GA Emergency Management Facilities (live)",
        "nearest_fire_station_km": round(nearest_km, 1) if nearest_km is not None else None,
        "nearest_station_type": station_type,
    }


def fetch_cyclone_hazard(lat: float, lon: float) -> dict:
    """Get RP50 cyclone wind speed at location (northern Australia only)."""
    if lat < -30:
        return {
            "source": "GA Cyclone Hazard 2018",
            "cyclone_risk": "NEGLIGIBLE",
            "note": "Outside tropical cyclone belt",
        }

    url = f"{GA_REST}/Tropical_Cyclone_Hazard_Assessment_2018/MapServer/identify"
    delta = 0.05
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "layers": "visible:6",  # RP50
        "tolerance": "3",
        "mapExtent": f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}",
        "imageDisplay": "800,600,96",
        "returnGeometry": "false",
        "f": "json",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        results = resp.json().get("results", [])
        if results:
            pixel_val = (
                results[0].get("attributes", {}).get("Pixel Value")
                or results[0].get("value")
            )
            if pixel_val is not None:
                wind_ms = float(pixel_val)
                return {
                    "source": "GA Cyclone Hazard Assessment 2018 (live)",
                    "rp50_wind_speed_ms": round(wind_ms, 1),
                    "cyclone_risk": _cyclone_risk_band(wind_ms),
                }
    except Exception:
        pass
    return {"source": "GA Cyclone Hazard (fallback)", "cyclone_risk": "LOW"}


def _cyclone_risk_band(wind_ms: float) -> str:
    if wind_ms >= 60:
        return "EXTREME"
    elif wind_ms >= 45:
        return "HIGH"
    elif wind_ms >= 30:
        return "MODERATE"
    return "LOW"


def fetch_surface_hydrology_proximity(lat: float, lon: float, radius_m: int = 1000) -> dict:
    """Count watercourses and water bodies within radius using GA Surface Hydrology."""
    base_params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": str(radius_m),
        "units": "esriSRUnit_Meter",
        "outFields": "objectid",
        "returnGeometry": "false",
        "returnCountOnly": "true",
        "f": "json",
    }

    watercourse_count = 0
    water_body_count = 0

    try:
        resp = requests.get(
            f"{GA_REST}/Surface_Hydrology/MapServer/2/query",
            params=base_params,
            timeout=8,
        )
        watercourse_count = resp.json().get("count", 0)
    except Exception:
        pass

    try:
        resp2 = requests.get(
            f"{GA_REST}/Surface_Hydrology/MapServer/4/query",
            params=base_params,
            timeout=8,
        )
        water_body_count = resp2.json().get("count", 0)
    except Exception:
        pass

    return {
        "source": "GA Surface Hydrology (live)",
        "watercourses_within_1km": watercourse_count,
        "water_bodies_within_1km": water_body_count,
        "flood_proximity_risk": _hydrology_to_flood_risk(watercourse_count, water_body_count),
        "search_radius_m": radius_m,
    }


def _hydrology_to_flood_risk(watercourses: int, water_bodies: int) -> str:
    if water_bodies > 0 or watercourses >= 3:
        return "HIGH — adjacent to waterway/water body"
    elif watercourses >= 1:
        return "MODERATE — watercourse within 1km"
    return "LOW — no watercourses nearby"


def fetch_vegetation_data(lat: float, lon: float) -> dict:
    """Fetch DEA Fractional Cover annual percentile at property location."""
    import io
    import numpy as np
    from PIL import Image

    delta = 0.05
    params = {
        "service": "WMS",
        "version": "1.3.0",
        "request": "GetMap",
        "layers": "ga_ls_fc_pc_cyear_3",
        "styles": "fc_rgb",
        "crs": "EPSG:4326",
        "bbox": f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}",
        "width": "11",
        "height": "11",
        "format": "image/png",
    }
    try:
        resp = requests.get("https://ows.dea.ga.gov.au/wms", params=params, timeout=15)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        arr = np.array(img)
        cy, cx = arr.shape[0] // 2, arr.shape[1] // 2
        r, g, b = int(arr[cy, cx, 0]), int(arr[cy, cx, 1]), int(arr[cy, cx, 2])
        if r == 0 and g == 0 and b == 0:
            raise ValueError("No-data pixel returned")
        # DEA fc_rgb: R=bare soil, G=photosynthetic veg, B=non-photosynthetic veg
        # Pixel values 0-255 scaled from 0-100%
        bare_soil_pct = round(r / 2.55)
        green_veg_pct = round(g / 2.55)
        dry_veg_pct = round(b / 2.55)
        ndvi_approx = round(0.1 + (green_veg_pct / 100) * 0.75, 3)
        return {
            "source": "DEA Fractional Cover Annual Percentile (live)",
            "ndvi_score": ndvi_approx,
            "green_veg_pct": green_veg_pct,
            "dry_veg_pct": dry_veg_pct,
            "bare_soil_pct": bare_soil_pct,
            "vegetation_density": _fc_density(green_veg_pct),
            "vegetation_type": _fc_type(green_veg_pct, dry_veg_pct, bare_soil_pct),
            "tree_canopy_cover_pct": green_veg_pct,
            "defensible_space_m": None,
            "defensible_space_adequate": None,
            "last_image_date": "DEA Annual Composite 2025",
        }
    except Exception:
        return {
            "source": "DEA Fractional Cover (fallback — data unavailable for this location)",
            "ndvi_score": None,
            "vegetation_density": None,
            "defensible_space_m": None,
            "defensible_space_adequate": None,
        }


def _fc_density(green_pct: int) -> str:
    if green_pct >= 60:
        return "High"
    elif green_pct >= 30:
        return "Moderate"
    return "Low"


def _fc_type(green: int, dry: int, bare: int) -> str:
    if green >= 60:
        return "Dense Vegetation / Canopy"
    elif green >= 30 and dry >= 20:
        return "Mixed Woodland"
    elif dry >= 40:
        return "Sparse/Dry Vegetation — elevated fuel load"
    elif bare >= 50:
        return "Sparse Vegetation / Cleared Land"
    elif green >= 20:
        return "Manicured Garden with Trees"
    return "Urban / Low Vegetation"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
