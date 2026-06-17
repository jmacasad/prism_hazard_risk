---
title: PRISM Hazard Risk
emoji: 🏠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.22.0
app_file: app.py
pinned: false
---

# PRISM — Property Risk Intelligence & Synthesis Manager

A multi-agent AI application that assesses natural hazard risk for Australian properties. Designed to help insurance underwriters evaluate luxury coastal and bushland properties — reducing assessment time from 5–10 days to hours.

## How it works

Enter any Australian property address and PRISM runs four AI agents in sequence:

1. **Data Harvesting** — pulls real-time data from Bureau of Meteorology, Geoscience Australia, and Nominatim geocoding
2. **Risk Analysis** — scores the property across flood, bushfire, storm, and coastal erosion hazards
3. **Validation & Compliance** — cross-checks scores against regulatory overlays and flags anomalies
4. **Communication** — generates a structured underwriting report with risk band and recommendations

Results include a numeric risk score (0–100), risk band (LOW / MODERATE / HIGH / VERY HIGH), an interactive Folium map, and a full written report.

## Stack

- Python 3.12
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) (`claude-sonnet-4-6`)
- [Gradio](https://gradio.app/) — UI
- [Folium](https://python-visualization.github.io/folium/) — interactive maps
- Real APIs: Bureau of Meteorology, Geoscience Australia, Nominatim
- Mocked: CoreLogic, Sentinel-2 NDVI, ISI claims, council overlays

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/jmacasad/prism_hazard_risk.git
cd prism_hazard_risk
```

**2. Create a virtual environment and install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Add your Anthropic API key**
```bash
cp .env.example .env
# Edit .env and paste your ANTHROPIC_API_KEY
```

**4. Run the app**
```bash
python app.py
```

Open [http://localhost:7860](http://localhost:7860) in your browser.

## Project structure

```
prism_hazard_risk/
├── app.py                  # Gradio UI entry point
├── agents/
│   ├── orchestrator.py     # Runs the 4-agent pipeline
│   ├── data_harvesting.py
│   ├── risk_analysis.py
│   ├── validation.py
│   └── communication.py
├── data_sources/
│   ├── bom_api.py          # Bureau of Meteorology
│   ├── geoscience_api.py   # Geoscience Australia
│   └── mock_data.py        # Mocked data sources
├── utils/
│   ├── map_utils.py        # Geocoding + Folium map builder
│   └── risk_scoring.py
├── requirements.txt
└── .env.example
```

## Demo addresses

- 42 Whale Beach Road, Whale Beach NSW 2107
- 15 Ocean View Drive, Byron Bay NSW 2481
- 8 Kangaroo Point Road, Kangaroo Point QLD 4169
- 22 Firetrack Road, Upwey VIC 3158
