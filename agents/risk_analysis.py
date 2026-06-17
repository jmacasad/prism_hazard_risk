"""Risk Analysis Agent — scores each peril using collected data."""

import json
import anthropic
from utils.risk_scoring import (
    score_bushfire,
    score_flood,
    score_storm,
    score_erosion,
    score_landslip,
    aggregate_scores,
)

SYSTEM_PROMPT = """You are the PRISM Risk Analysis Agent.
You receive a property data bundle and must calculate precise risk scores for each peril:
bushfire, flood, storm, coastal erosion, and landslip.
Use the available scoring tools for each peril, then aggregate them into an overall score.
Provide clear reasoning for each score based on the data evidence."""

TOOLS = [
    {
        "name": "calculate_bushfire_score",
        "description": "Calculate bushfire risk score (0-100) from satellite, overlay, and weather data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "satellite_data": {"type": "object"},
                "bushfire_data": {"type": "object"},
                "weather_data": {"type": "object"},
            },
            "required": ["satellite_data", "bushfire_data", "weather_data"],
        },
    },
    {
        "name": "calculate_flood_score",
        "description": "Calculate flood risk score (0-100) from flood overlay, property, and claims data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flood_data": {"type": "object"},
                "property_data": {"type": "object"},
                "claims_data": {"type": "object"},
            },
            "required": ["flood_data", "property_data", "claims_data"],
        },
    },
    {
        "name": "calculate_storm_score",
        "description": "Calculate storm/cyclone risk score (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "weather_data": {"type": "object"},
                "property_data": {"type": "object"},
                "claims_data": {"type": "object"},
            },
            "required": ["weather_data", "property_data", "claims_data"],
        },
    },
    {
        "name": "calculate_erosion_score",
        "description": "Calculate coastal erosion risk score (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "geoscience_data": {"type": "object"},
                "satellite_data": {"type": "object"},
            },
            "required": ["geoscience_data", "satellite_data"],
        },
    },
    {
        "name": "calculate_landslip_score",
        "description": "Calculate landslip/subsidence risk score (0-100).",
        "input_schema": {
            "type": "object",
            "properties": {
                "geoscience_data": {"type": "object"},
                "property_data": {"type": "object"},
            },
            "required": ["geoscience_data", "property_data"],
        },
    },
    {
        "name": "aggregate_risk_scores",
        "description": "Combine all peril scores into an overall risk score and risk band.",
        "input_schema": {
            "type": "object",
            "properties": {
                "perils": {
                    "type": "object",
                    "description": "Dict with keys: bushfire, flood, storm, erosion, landslip. Each has score and factors.",
                }
            },
            "required": ["perils"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> str:
    if name == "calculate_bushfire_score":
        return json.dumps(score_bushfire(
            inputs["satellite_data"], inputs["bushfire_data"], inputs["weather_data"]
        ))
    elif name == "calculate_flood_score":
        return json.dumps(score_flood(
            inputs["flood_data"], inputs["property_data"], inputs["claims_data"]
        ))
    elif name == "calculate_storm_score":
        return json.dumps(score_storm(
            inputs["weather_data"], inputs["property_data"], inputs["claims_data"]
        ))
    elif name == "calculate_erosion_score":
        return json.dumps(score_erosion(
            inputs["geoscience_data"], inputs["satellite_data"]
        ))
    elif name == "calculate_landslip_score":
        return json.dumps(score_landslip(
            inputs["geoscience_data"], inputs["property_data"]
        ))
    elif name == "aggregate_risk_scores":
        return json.dumps(aggregate_scores(inputs["perils"]))
    return json.dumps({"error": f"Unknown tool: {name}"})


def run(client: anthropic.Anthropic, data_bundle: dict):
    """Run the Risk Analysis Agent. Yields (log_line, scores_or_None) tuples."""
    yield "📊 Risk Analysis Agent activated — running ensemble peril models...", None

    messages = [
        {
            "role": "user",
            "content": (
                "Analyse this property data bundle and calculate risk scores for all perils.\n\n"
                f"DATA BUNDLE:\n{json.dumps(data_bundle, indent=2)}"
            ),
        }
    ]

    final_scores = None
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
                    yield f"   ↳ Scoring: **{block.name.replace('calculate_', '').replace('_', ' ').title()}**...", None
                    result = _execute_tool(block.name, block.input)
                    parsed = json.loads(result)
                    if block.name == "aggregate_risk_scores":
                        final_scores = parsed
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            yield "✅ Risk analysis complete — all peril scores calculated.", final_scores
            return

    yield "⚠️ Risk analysis reached iteration limit.", final_scores
