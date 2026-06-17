"""Folium map generation with hazard overlays."""

import folium
import json


def build_risk_map(
    address: str,
    lat: float,
    lon: float,
    scores: dict,
    flood_data: dict,
    bushfire_data: dict,
) -> str:
    """Return HTML string of interactive Folium map."""
    overall = scores.get("overall_score", 50)
    risk_band = scores.get("risk_band", "MODERATE")

    color = _score_to_color(overall)
    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")

    # Property marker
    popup_html = f"""
    <div style="font-family:sans-serif;width:220px">
        <b style="font-size:14px">{address[:40]}</b><br>
        <hr style="margin:4px 0">
        <span style="font-size:22px;font-weight:bold;color:{color}">{overall}</span>
        <span style="font-size:11px;color:#666"> / 100</span><br>
        <b style="color:{color}">{risk_band} RISK</b><br>
        <span style="font-size:11px">Premium loading: {scores.get('premium_loading','N/A')}</span>
    </div>
    """
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup_html, max_width=240),
        icon=folium.Icon(color=_band_to_folium_color(risk_band), icon="home", prefix="fa"),
        tooltip=f"PRISM Score: {overall}/100 — {risk_band}",
    ).add_to(m)

    # Flood zone circle
    if flood_data.get("in_flood_planning_zone"):
        folium.Circle(
            [lat, lon],
            radius=400,
            color="#1a6fba",
            fill=True,
            fill_color="#4da6ff",
            fill_opacity=0.2,
            tooltip=f"Flood Zone: {flood_data.get('flood_category', 'N/A')}",
        ).add_to(m)

    # Bushfire prone land circle
    if bushfire_data.get("bushfire_prone_land"):
        folium.Circle(
            [lat, lon],
            radius=700,
            color="#cc4400",
            fill=True,
            fill_color="#ff6633",
            fill_opacity=0.12,
            tooltip=f"Bushfire Prone: {bushfire_data.get('bpl_category', 'N/A')}",
        ).add_to(m)

    # Coastal erosion buffer — only shown when erosion score is meaningful
    erosion_score = scores.get("perils", {}).get("erosion", {}).get("score", 0)
    if erosion_score >= 20:
        folium.Circle(
            [lat, lon],
            radius=250,
            color="#8B6914",
            fill=True,
            fill_color="#D4A843",
            fill_opacity=0.15,
            tooltip=f"Coastal Erosion Buffer Zone (score: {erosion_score}/100)",
        ).add_to(m)

    # Legend
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:12px;border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);font-family:sans-serif;font-size:12px">
        <b>PRISM Hazard Overlays</b><br>
        <span style="color:#4da6ff">&#9646;</span> Flood Zone<br>
        <span style="color:#ff6633">&#9646;</span> Bushfire Prone Land<br>
        <span style="color:#D4A843">&#9646;</span> Coastal Erosion Buffer<br>
        <span style="color:{color}">&#9679;</span> Property ({overall}/100)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m._repr_html_()


def _score_to_color(score: float) -> str:
    if score >= 75:
        return "#d32f2f"
    elif score >= 55:
        return "#f57c00"
    elif score >= 35:
        return "#f9a825"
    return "#388e3c"


def _band_to_folium_color(band: str) -> str:
    mapping = {
        "VERY HIGH": "red",
        "HIGH": "orange",
        "MODERATE": "beige",
        "LOW-MODERATE": "green",
    }
    return mapping.get(band, "blue")


def geocode_address(address: str) -> tuple[float, float]:
    """Geocode using Nominatim. Raises ValueError if address cannot be resolved."""
    import requests
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "au"}
    headers = {"User-Agent": "PRISM-Prototype/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        raise ValueError(f"Geocoding failed: {e}")
    raise ValueError(f"Address not found in Australia: '{address}' — check spelling or try a nearby suburb.")
