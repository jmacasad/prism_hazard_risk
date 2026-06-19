# PRISM — Property Risk Intelligence & Synthesis Manager

A multi-agent AI application that assesses natural hazard risk for Australian properties. Designed to help insurance underwriters evaluate luxury coastal and bushland properties — reducing assessment time from 5–10 days to hours.

## How it works

Enter any Australian property address and PRISM runs four AI agents in sequence:

1. **Data Harvesting** — pulls real-time data from Bureau of Meteorology, Geoscience Australia, and Nominatim geocoding
2. **Risk Analysis** — scores the property across flood, bushfire, storm, coastal erosion and landslip hazards
3. **Validation & Compliance** — cross-checks scores against APRA CPS 220 requirements and flags anomalies
4. **Communication** — generates a structured underwriting report with risk band and premium loading recommendation

Results include a numeric risk score (0–100), risk band, interactive hazard map with layer toggles, and a full written underwriter report.

## Stack

- **Backend:** Python 3.12, FastAPI, Anthropic SDK (`claude-sonnet-4-6`)
- **Frontend:** React 19 + Vite + Tailwind CSS
- **Maps:** Folium with toggleable hazard overlays
- **Live APIs:** Bureau of Meteorology, Geoscience Australia, Nominatim geocoding
- **Simulated:** CoreLogic, Sentinel-2 NDVI, IRS claims, council flood/bushfire overlays

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- An Anthropic API key

---

### 1. Clone the repo
```bash
git clone https://github.com/jmacasad/prism_hazard_risk.git
cd prism_hazard_risk
```

### 2. Set up the Python backend
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API key
```bash
cp .env.example .env
# Open .env and add: ANTHROPIC_API_KEY=your-key-here
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 5. Run the app (two terminals)

**Terminal 1 — API backend:**
```bash
source .venv/bin/activate
uvicorn api:app --reload --port 8000
```

**Terminal 2 — React frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Project structure

```
prism_hazard_risk/
├── api.py                  # FastAPI backend with SSE streaming
├── agents/
│   ├── orchestrator.py     # Runs the 4-agent pipeline
│   ├── data_harvesting.py
│   ├── risk_analysis.py
│   ├── validation.py
│   └── communication.py
├── data_sources/
│   ├── bom_api.py          # Bureau of Meteorology (live)
│   ├── geoscience_api.py   # Geoscience Australia (live)
│   └── mock_data.py        # Simulated: CoreLogic, IRS, satellite, overlays
├── utils/
│   ├── map_utils.py        # Geocoding + Folium map builder
│   └── risk_scoring.py     # Deterministic peril scoring functions
├── frontend/               # React + Vite + Tailwind UI
├── requirements.txt
├── DEMO_BRIEFING.md        # Demo guide: data sources, methodology, production roadmap
└── .env.example
```

## Demo addresses

- 42 Whale Beach Road, Whale Beach NSW 2107
- 15 Ocean View Drive, Byron Bay NSW 2481
- 8 Kangaroo Point Road, Kangaroo Point QLD 4169
- 22 Firetrack Road, Upwey VIC 3158
