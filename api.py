"""PRISM FastAPI backend — streams agent events via SSE."""

import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from agents.orchestrator import run_assessment
from utils.map_utils import build_risk_map

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssessRequest(BaseModel):
    address: str


def event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/api/assess")
async def assess(req: AssessRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    def generate():
        if not api_key:
            yield event({"type": "error", "message": "No ANTHROPIC_API_KEY found."})
            return

        for stage, log_line, payload in run_assessment(req.address, api_key):
            if stage == "log" and log_line:
                yield event({"type": "log", "line": log_line})

            elif stage == "scores" and payload:
                yield event({"type": "scores", "data": payload})

            elif stage == "report" and payload:
                yield event({"type": "report", "markdown": payload})

            elif stage == "map_data" and payload:
                map_html = build_risk_map(
                    payload["address"], payload["lat"], payload["lon"],
                    payload["scores"], payload["flood_data"], payload["bushfire_data"],
                )
                yield event({"type": "map", "html": map_html})

            elif stage == "error":
                yield event({"type": "error", "message": log_line})
                return

        yield event({"type": "done"})

    return StreamingResponse(generate(), media_type="text/event-stream")
