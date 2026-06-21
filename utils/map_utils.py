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
) -> tuple[str, dict]:
    """Return (html, layers_data) where layers_data flags which overlays have geometry."""
    overall = scores.get("overall_score", 50)
    risk_band = scores.get("risk_band", "MODERATE")
    color = _score_to_color(overall)

    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles="OpenStreetMap",
    )

    # Property marker
    popup_html = f"""
    <div style="font-family:sans-serif;width:220px">
        <b style="font-size:14px">{address[:40]}</b><br>
        <hr style="margin:4px 0">
        <span style="font-size:22px;font-weight:bold;color:{color}">{overall}</span>
        <span style="font-size:11px;color:#666"> / 100</span><br>
        <b style="color:{color}">{risk_band} RISK</b><br>
        <span style="font-size:11px">Confidence: {scores.get('confidence','N/A')}</span>
    </div>
    """
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup_html, max_width=240),
        icon=folium.Icon(color=_band_to_folium_color(risk_band), icon="home", prefix="fa"),
        tooltip=f"PRISM Score: {overall}/100 — {risk_band}",
    ).add_to(m)

    # Flood zone layer
    flood_has_data = bool(flood_data.get("in_flood_planning_zone"))
    flood_group = folium.FeatureGroup(name="Flood Zone", show=True)
    if flood_has_data:
        folium.Circle(
            [lat, lon], radius=400,
            color="#1a6fba", fill=True, fill_color="#4da6ff", fill_opacity=0.2,
            tooltip=f"Flood Zone: {flood_data.get('flood_category', 'N/A')}",
        ).add_to(flood_group)
    flood_group.add_to(m)

    # Bushfire prone land layer
    bushfire_has_data = bool(bushfire_data.get("bushfire_prone_land"))
    bushfire_group = folium.FeatureGroup(name="Bushfire Prone Land", show=True)
    if bushfire_has_data:
        folium.Circle(
            [lat, lon], radius=700,
            color="#cc4400", fill=True, fill_color="#ff6633", fill_opacity=0.12,
            tooltip=f"Bushfire Prone: {bushfire_data.get('bpl_category', 'N/A')}",
        ).add_to(bushfire_group)
    bushfire_group.add_to(m)

    # Coastal erosion layer
    erosion_score = scores.get("perils", {}).get("erosion", {}).get("score", 0)
    erosion_has_data = erosion_score >= 20
    erosion_group = folium.FeatureGroup(name="Coastal Erosion Buffer", show=True)
    if erosion_has_data:
        folium.Circle(
            [lat, lon], radius=250,
            color="#8B6914", fill=True, fill_color="#D4A843", fill_opacity=0.15,
            tooltip=f"Coastal Erosion Buffer Zone (score: {erosion_score}/100)",
        ).add_to(erosion_group)
    erosion_group.add_to(m)

    # Storm risk radius layer
    storm_score = scores.get("perils", {}).get("storm", {}).get("score", 0)
    storm_has_data = storm_score >= 20
    storm_group = folium.FeatureGroup(name="Storm Risk Radius", show=False)
    if storm_has_data:
        folium.Circle(
            [lat, lon], radius=1000,
            color="#5c35cc", fill=True, fill_color="#9b7fe8", fill_opacity=0.08,
            tooltip=f"Storm Risk Radius (score: {storm_score}/100)",
        ).add_to(storm_group)
    storm_group.add_to(m)

    # PostMessage bridge — lets the React layer toggles control Leaflet layers
    flood_var = flood_group.get_name()
    bushfire_var = bushfire_group.get_name()
    erosion_var = erosion_group.get_name()
    storm_var = storm_group.get_name()
    map_var = m.get_name()

    bridge = f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
  window.addEventListener('message', function(e) {{
    if (!e.data || e.data.type !== 'prism-toggle') return;
    var layerMap = {{
      flood: window['{flood_var}'],
      bushfire: window['{bushfire_var}'],
      erosion: window['{erosion_var}'],
      storm: window['{storm_var}'],
    }};
    var mapObj = window['{map_var}'];
    var layer = layerMap[e.data.layer];
    if (!layer || !mapObj) return;
    if (e.data.visible) {{
      layer.addTo(mapObj);
    }} else {{
      mapObj.removeLayer(layer);
    }}
  }});
}});
</script>
"""
    m.get_root().html.add_child(folium.Element(bridge))

    layers_data = {
        "flood": flood_has_data,
        "bushfire": bushfire_has_data,
        "erosion": erosion_has_data,
        "storm": storm_has_data,
    }
    return m._repr_html_(), layers_data


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
