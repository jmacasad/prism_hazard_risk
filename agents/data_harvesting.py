"""Data Harvesting Agent — collects all property data from real and mocked sources."""

import json
import anthropic
from data_sources.bom_api import fetch_weather_observations, state_hint_from_coords
from data_sources.geoscience_api import fetch_geological_hazards
from data_sources.mock_data import (
    fetch_property_data,
    fetch_satellite_analysis,
    fetch_historical_claims,
    fetch_flood_overlay,
    fetch_bushfire_overlay,
)
from data_sources.tavily_property import (
    fetch_property_data_tavily,
    fetch_flood_overlay_tavily,
    fetch_bushfire_overlay_tavily,
    clear_cache as tavily_clear_cache,
)
from utils.map_utils import geocode_address

SYSTEM_PROMPT = """You are the PRISM Data Harvesting Agent.
Your role is to collect comprehensive risk-relevant data for a given property address.
You must call ALL available data collection tools and compile a complete data bundle.
Be systematic: always collect property details, weather, geological data, satellite imagery,
historical claims, flood overlay, and bushfire overlay for every assessment.
Return a structured JSON summary of all collected data."""

TOOLS = [
    {
        "name": "get_property_data",
        "description": "Retrieves property details from CoreLogic/PSMA: value, construction, size, year built.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Full property address"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_weather_observations",
        "description": "Fetches live weather conditions from BoM including temperature, wind, fire danger.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state_hint": {"type": "string", "description": "State or region hint e.g. 'nsw_coast'"}
            },
            "required": [],
        },
    },
    {
        "name": "get_geological_hazards",
        "description": "Queries Geoscience Australia for seismic hazard, soil type, and coastal erosion risk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lon": {"type": "number", "description": "Longitude"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "get_satellite_analysis",
        "description": "Returns Sentinel-2 NDVI vegetation analysis and defensible space assessment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Property address"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_historical_claims",
        "description": "Retrieves historical insurance claims within 5km radius from Insurance Reference Services (IRS) database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Property address"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_flood_overlay",
        "description": "Checks council flood planning overlay and stormwater infrastructure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Property address"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_bushfire_overlay",
        "description": "Checks RFS/CFA bushfire prone land mapping and BAL rating factors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Property address"}
            },
            "required": ["address"],
        },
    },
]


def _execute_tool(name: str, inputs: dict, address: str, lat: float, lon: float) -> str:
    if name == "get_property_data":
        target = inputs.get("address", address)
        mock = fetch_property_data(target)
        live = fetch_property_data_tavily(target)
        if live:
            mock.update({k: v for k, v in live.items() if v is not None})
        return json.dumps(mock)
    elif name == "get_weather_observations":
        hint = state_hint_from_coords(lat, lon)
        return json.dumps(fetch_weather_observations(hint))
    elif name == "get_geological_hazards":
        return json.dumps(fetch_geological_hazards(inputs.get("lat", lat), inputs.get("lon", lon)))
    elif name == "get_satellite_analysis":
        return json.dumps(fetch_satellite_analysis(inputs.get("address", address)))
    elif name == "get_historical_claims":
        return json.dumps(fetch_historical_claims(inputs.get("address", address)))
    elif name == "get_flood_overlay":
        target = inputs.get("address", address)
        mock = fetch_flood_overlay(target)
        live = fetch_flood_overlay_tavily(target)
        if live:
            mock.update({k: v for k, v in live.items() if v is not None})
        return json.dumps(mock)
    elif name == "get_bushfire_overlay":
        target = inputs.get("address", address)
        mock = fetch_bushfire_overlay(target)
        live = fetch_bushfire_overlay_tavily(target)
        if live:
            mock.update({k: v for k, v in live.items() if v is not None})
        return json.dumps(mock)
    return json.dumps({"error": f"Unknown tool: {name}"})


def run(client: anthropic.Anthropic, address: str, lat: float, lon: float):
    """Run the Data Harvesting Agent. Yields (log_line, data_bundle_or_None) tuples."""
    tavily_clear_cache()
    yield "🔍 Data Harvesting Agent activated — collecting property intelligence...", None

    messages = [
        {
            "role": "user",
            "content": f"Collect all available data for this property: {address}\nCoordinates: lat={lat:.4f}, lon={lon:.4f}",
        }
    ]

    collected = {}
    iterations = 0

    while iterations < 10:
        iterations += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    yield f"   ↳ Querying: **{block.name.replace('_', ' ').title()}**...", None
                    result = _execute_tool(block.name, block.input, address, lat, lon)
                    collected[block.name] = json.loads(result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Agent finished — extract final text
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            yield "✅ Data collection complete — 7 sources harvested.", collected
            return

    yield "⚠️ Data harvesting reached iteration limit.", collected
