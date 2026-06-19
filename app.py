"""PRISM — Property Risk Intelligence & Synthesis Manager
Gradio demo application.
"""

import os
import base64
import gradio as gr
from dotenv import load_dotenv
from agents.orchestrator import run_assessment
from utils.map_utils import build_risk_map

load_dotenv()


def _load_logo_src():
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo-color-white.svg")
    try:
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/svg+xml;base64,{b64}"
    except Exception:
        return ""


def _make_honeycomb_svg():
    r, hw, hh, dx, dy = 26, 23, 13, 45, 39
    row0_x = list(range(0, 480, dx))
    row1_x = list(range(23, 503, dx))
    rows = [(row0_x, 26), (row1_x, 65), (row0_x, 104), (row1_x, 143), (row0_x, 182)]
    polys = "".join(
        f'<polygon points="{cx},{cy-r} {cx+hw},{cy-hh} {cx+hw},{cy+hh} {cx},{cy+r} {cx-hw},{cy+hh} {cx-hw},{cy-hh}"/>'
        for xs, cy in rows for cx in xs
    )
    return (
        '<svg viewBox="0 0 480 210" preserveAspectRatio="xMaxYMax meet"'
        ' xmlns="http://www.w3.org/2000/svg"'
        ' style="position:absolute;right:0;bottom:0;width:380px;height:120px;pointer-events:none;'
        'transform:perspective(380px) rotateX(45deg);transform-origin:bottom right;">'
        '<defs>'
        '<radialGradient id="hc-grad" cx="1" cy="1" r="1.3" gradientUnits="objectBoundingBox">'
        '<stop offset="0%" stop-color="white"/>'
        '<stop offset="55%" stop-color="white" stop-opacity="0.5"/>'
        '<stop offset="100%" stop-color="black"/>'
        '</radialGradient>'
        '<mask id="hc-mask">'
        '<rect width="480" height="210" fill="url(#hc-grad)"/>'
        '</mask>'
        '</defs>'
        f'<g mask="url(#hc-mask)" fill="none" stroke="rgba(190,230,210,0.55)" stroke-width="1.5">{polys}</g>'
        '</svg>'
    )


LOGO_SRC = _load_logo_src()
HONEYCOMB_SVG = _make_honeycomb_svg()

DEMO_ADDRESSES = [
    "42 Whale Beach Road, Whale Beach NSW 2107",
    "15 Ocean View Drive, Byron Bay NSW 2481",
    "8 Kangaroo Point Road, Kangaroo Point QLD 4169",
    "22 Firetrack Road, Upwey VIC 3158",
]

AGENTS = [
    ("🔍", "Data Harvesting"),
    ("📊", "Risk Analysis"),
    ("✔", "Validation"),
    ("📝", "Report"),
]

CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.prism-header {
    background: #304E4D;
    padding: 24px 52px;
    border-radius: 12px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    box-sizing: border-box;
}
.prism-header h1 {
    color: #fff;
    margin: 0;
    font-size: 72px;
    font-weight: 900;
    letter-spacing: 4px;
    line-height: 1;
}
.prism-header p { color: #D2B589; margin: 10px 0 0; font-size: 13px; letter-spacing: 0.3px; }
.score-display { font-size: 72px; font-weight: 900; text-align: center; line-height: 1; }
.score-low       { color: #388e3c; }
.score-moderate  { color: #f9a825; }
.score-high      { color: #f57c00; }
.score-very-high { color: #d32f2f; }
#run-btn {
    background: #D2B589 !important;
    color: #304E4D !important;
    border: none !important;
    border-radius: 999px !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    padding: 10px 32px !important;
    width: fit-content !important;
    min-width: 140px !important;
}
#search-row {
    align-items: flex-end !important;
}
#run-btn {
    margin-left: auto !important;
}
#search-row .block {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}
#search-row > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
"""

# ── helpers ──────────────────────────────────────────────────────────────────

def _score_color(score):
    if score >= 75: return "#d32f2f"
    if score >= 55: return "#f57c00"
    if score >= 35: return "#f9a825"
    return "#388e3c"

def _score_css(score):
    if score >= 75: return "score-very-high"
    if score >= 55: return "score-high"
    if score >= 35: return "score-moderate"
    return "score-low"

def _badge(score):
    c = _score_color(score)
    return f'<span style="background:{c};color:#fff;padding:2px 10px;border-radius:4px;font-weight:700">{score}</span>'

# ── pipeline header HTML ──────────────────────────────────────────────────────

def _pipeline_html(current: int, done: bool = False) -> str:
    """Render a 4-stage pipeline progress bar.
    current: 0 = not started, 1-4 = that agent is active, 5 = all done.
    """
    cards = ""
    for i, (icon, name) in enumerate(AGENTS, start=1):
        if i < current or (done and i <= 4):
            state = "complete"
            bg, border, text_color = "#e8f5e9", "#388e3c", "#1b5e20"
            status_html = '<span style="color:#388e3c;font-size:11px;font-weight:600">✓ COMPLETE</span>'
        elif i == current and not done:
            state = "running"
            bg, border, text_color = "#e3f2fd", "#1565c0", "#0d47a1"
            status_html = '<span style="color:#1565c0;font-size:11px;font-weight:600">⟳ RUNNING…</span>'
        else:
            state = "waiting"
            bg, border, text_color = "#fafafa", "#e0e0e0", "#9e9e9e"
            status_html = '<span style="color:#bdbdbd;font-size:11px">○ WAITING</span>'

        cards += f"""
        <div style="flex:1;background:{bg};border:2px solid {border};border-radius:10px;
                    padding:12px 10px;text-align:center;min-width:120px">
            <div style="font-size:22px">{icon}</div>
            <div style="font-size:13px;font-weight:700;color:{text_color};margin:4px 0 2px">{name}</div>
            {status_html}
        </div>"""

    return f'<div style="display:flex;gap:10px;margin-bottom:12px">{cards}</div>'

# ── log lines → styled HTML ───────────────────────────────────────────────────

def _log_html(lines: list[str]) -> str:
    rows = ""
    for line in lines:
        if line.startswith("─"):
            rows += '<div style="border-top:1px solid #e0e0e0;margin:6px 0"></div>'
            continue
        if line.startswith("✅"):
            color, fw = "#2e7d32", "600"
        elif line.startswith("❌") or line.startswith("⚠️"):
            color, fw = "#c62828", "600"
        elif line.startswith("🏁"):
            color, fw = "#1565c0", "700"
        elif line.startswith("📍") or line.startswith("🔍") or line.startswith("📊") or \
             line.startswith("🔎") or line.startswith("📝"):
            color, fw = "#0d2137", "700"
        elif line.strip().startswith("↳"):
            color, fw = "#555", "400"
        else:
            color, fw = "#333", "400"

        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # re-allow bold markdown **text**
        import re
        safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
        rows += f'<div style="padding:2px 0;color:{color};font-weight:{fw};font-size:13px">{safe}</div>'

    return f"""
    <div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;
                padding:14px 16px;min-height:240px;font-family:'SF Mono',monospace;
                max-height:420px;overflow-y:auto">
        {rows if rows else '<span style="color:#aaa">Waiting for assessment to start…</span>'}
    </div>"""

def _activity_html(lines: list[str], current_stage: int, done: bool = False) -> str:
    return _pipeline_html(current_stage, done) + _log_html(lines)

# ── detect which agent is active from log lines ───────────────────────────────

def _detect_stage(lines: list[str]) -> int:
    stage = 0
    for line in lines:
        if "Data Harvesting Agent activated" in line:
            stage = 1
        elif "Risk Analysis Agent activated" in line:
            stage = 2
        elif "Validation" in line and "Agent activated" in line:
            stage = 3
        elif "Communication Agent activated" in line:
            stage = 4
    return stage

# ── scores HTML ───────────────────────────────────────────────────────────────

def _scores_html(scores: dict) -> str:
    perils = scores.get("perils", {})
    overall = scores.get("overall_score", 0)
    band = scores.get("risk_band", "")
    loading = scores.get("premium_loading", "")
    confidence = scores.get("confidence", "")
    css_class = _score_css(overall)

    rows = ""
    for name, data in perils.items():
        ps = data.get("score", 0)
        factors = " &nbsp;·&nbsp; ".join(data.get("factors", []))
        rows += f"""<tr>
            <td style="padding:9px 14px;font-weight:600;text-transform:capitalize;
                       border-bottom:1px solid #f0f0f0">{name}</td>
            <td style="padding:9px 14px;text-align:center;border-bottom:1px solid #f0f0f0">{_badge(ps)}</td>
            <td style="padding:9px 14px;font-size:12px;color:#666;border-bottom:1px solid #f0f0f0">{factors}</td>
        </tr>"""

    return f"""
    <div style="font-family:-apple-system,sans-serif">
        <div style="text-align:center;padding:24px 0 16px">
            <div class="score-display {css_class}">{overall}</div>
            <div style="font-size:20px;font-weight:800;margin-top:6px;color:#222">{band} RISK</div>
            <div style="color:#777;font-size:13px;margin-top:4px">
                Confidence: <b>{confidence}</b> &nbsp;·&nbsp; Recommended premium loading: <b>{loading}</b>
            </div>
        </div>
        <table style="width:100%;border-collapse:collapse;border:1px solid #e8e8e8;border-radius:8px;overflow:hidden">
            <thead><tr style="background:#f5f7fa">
                <th style="padding:10px 14px;text-align:left;color:#444;font-size:13px">Peril</th>
                <th style="padding:10px 14px;text-align:center;color:#444;font-size:13px">Score /100</th>
                <th style="padding:10px 14px;text-align:left;color:#444;font-size:13px">Key Risk Factors</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""

# ── main generator ─────────────────────────────────────────────────────────────

def run_prism(address: str):
    """Gradio generator — yields (activity_html, scores_html, report_md, map_html, dl_text)."""
    if not address.strip():
        yield (
            _activity_html(["⚠️ Please enter a property address."], 0),
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False),
        )
        return

    effective_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not effective_key:
        yield (
            _activity_html(["❌ No API key found. Paste your ANTHROPIC_API_KEY above or add it to .env"], 0),
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False),
        )
        return

    log_lines = []
    scores_html = ""
    report_md = ""
    map_html = None

    def _emit(done=False):
        stage = _detect_stage(log_lines)
        activity = _activity_html(log_lines, stage, done)
        return (
            activity,
            gr.update(value=scores_html, visible=bool(scores_html)),
            gr.update(value=report_md, visible=bool(report_md)),
            gr.update(value=map_html or "", visible=map_html is not None),
            gr.update(value=report_md, visible=bool(report_md) and done),
        )

    for stage, log_line, payload in run_assessment(address, effective_key):

        if stage == "log" and log_line:
            log_lines.append(log_line)
            yield _emit()

        elif stage == "scores" and payload:
            scores_html = _scores_html(payload)
            yield _emit()

        elif stage == "report" and payload:
            report_md = payload
            yield _emit()

        elif stage == "map_data" and payload:
            map_html = build_risk_map(
                payload["address"], payload["lat"], payload["lon"],
                payload["scores"], payload["flood_data"], payload["bushfire_data"],
            )
            yield _emit()

        elif stage == "error":
            log_lines.append(log_line)
            yield _emit()
            return

    yield _emit(done=True)


# ── UI ────────────────────────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(css=CSS, title="PRISM — Property Risk Intelligence") as demo:

        gr.HTML(f"""
        <div class="prism-header">
          <div style="position:relative;z-index:2;flex:1">
            <h1>PRISM</h1>
            <p>Property Risk Intelligence &amp; Synthesis Manager &nbsp;·&nbsp;
               Natural Hazard Assessment for Luxury Coastal &amp; Bushland Properties</p>
          </div>
          {HONEYCOMB_SVG}
        </div>
        """)

        with gr.Row(elem_id="search-row"):
            address_input = gr.Textbox(
                label="Property Address",
                placeholder="e.g. 42 Whale Beach Road, Whale Beach NSW 2107",
                lines=1,
                scale=9,
            )
            run_btn = gr.Button("SEARCH", variant="primary", size="sm", elem_id="run-btn", scale=1)

        with gr.Row():
            for addr in DEMO_ADDRESSES:
                short = addr.split(",")[0]
                gr.Button(f"▶ {short}", size="sm", variant="secondary").click(
                    fn=lambda a=addr: a,
                    outputs=address_input,
                )

        with gr.Tabs():
            with gr.TabItem("🤖  Agent Activity"):
                activity_output = gr.HTML(
                    value=_activity_html([], 0),
                )

            with gr.TabItem("📊  Risk Report"):
                scores_output = gr.HTML(visible=False)
                report_output = gr.Markdown(visible=False)
                download_output = gr.Textbox(
                    label="Full report text",
                    visible=False, lines=6, interactive=False,
                )

            with gr.TabItem("🗺  Risk Map"):
                map_output = gr.HTML(
                    value="<p style='color:#aaa;padding:60px;text-align:center;font-size:15px'>"
                          "Run an assessment to generate the interactive hazard map.</p>",
                )

        run_outputs = [activity_output, scores_output, report_output, map_output, download_output]

        # Main run button
        run_btn.click(fn=run_prism, inputs=[address_input], outputs=run_outputs)

        # Demo buttons — closures with address baked in, no inputs needed
        with gr.Row():
            for addr in DEMO_ADDRESSES:
                short = addr.split(",")[0]
                def make_runner(a):
                    def _runner():
                        yield from run_prism(a)
                    return _runner
                gr.Button(f"🚀 Demo: {short}", size="sm").click(
                    fn=make_runner(addr),
                    inputs=[],
                    outputs=run_outputs,
                )

        gr.Markdown("""
---
**Live data**: Bureau of Meteorology · Geoscience Australia · OpenStreetMap geocoding
**Simulated**: CoreLogic · ISI Claims · Sentinel-2 NDVI · Council flood/bushfire overlays
*PRISM prototype — not for production underwriting decisions.*
        """)

    return demo


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860)
