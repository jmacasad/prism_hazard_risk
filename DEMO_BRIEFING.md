# PRISM — Demo Briefing Document
**Property Risk Intelligence & Synthesis Manager**
*Prepared for underwriter demo use — updated 21 June 2026*

---

## 1. Where Does PRISM Get Its Data?

All data sources in the current prototype are **live**. There are no simulated fallbacks or mocked datasets.

| Data Source | Status | What It Provides |
|---|---|---|
| **Bureau of Meteorology (BoM)** | LIVE | Real-time weather: temperature, wind, humidity, fire danger rating |
| **Geoscience Australia — Seismic** | LIVE | Seismic hazard PGA and earthquake zone via ArcGIS REST API |
| **Geoscience Australia — Smartline** | LIVE | Coastal geomorphology: sandy, dune, soft rock, hard rock, backing profile classification |
| **Geoscience Australia — Cyclone** | LIVE | RP50 wind speed at property coordinates (tropical belt) |
| **Geoscience Australia — Surface Hydrology** | LIVE | Watercourse and water body count within 1km radius |
| **Geoscience Australia — Emergency Facilities** | LIVE | Nearest fire station distance and type |
| **DEA Fractional Cover (Digital Earth Australia)** | LIVE | Satellite-derived green vegetation, dry vegetation, and bare soil percentages (NDVI proxy) |
| **Gemini Grounded Search (Google)** | LIVE | Property value, configuration, land/floor area, year built, flood overlay, bushfire overlay — sourced from domain.com.au, realestate.com.au, state planning portals |
| **Nominatim / OpenStreetMap** | LIVE | Geocoding — converts address to lat/lon |

> **State-aware planning search:** When looking up flood and bushfire overlays, the agent detects the state from the address and directs Gemini to search the correct portal — VicPlan/BMO for VIC, NSW Planning Portal/RFS for NSW, PlanSA for SA, QLD DA System for QLD, DFES for WA, and so on for all 8 states and territories.

---

### What You Need for Production

| Data Gap | Current | Production |
|---|---|---|
| Property valuation | Gemini search (public listing data) | CoreLogic or Geoscape commercial API |
| Flood overlay | Gemini search (state planning portals) | Direct WFS/WMS from NSW Spatial, DELWP, QSpatial etc. |
| Bushfire prone land | Gemini search (RFS/CFA/DFES state sites) | Direct API from state fire authorities |
| Soil classification | Coordinate-based rule (`_estimate_soil_type`) | SoilWise (TERN) or ASRIS national soil database |
| Coastal erosion | GA Smartline geomorphology (live) | + Council-specific coastal hazard plans and setback lines |
| Climate projections | Not included | CSIRO for 10/25/50-year risk horizon modelling |
| Claims history | Not included | Insurance Reference Services (IRS) or ICA database |

---

## 2. Risk Analysis — Model or Scientific Method?

PRISM uses a **hybrid approach**: deterministic actuarial scoring functions orchestrated by an AI agent.

### The Scoring Engine (Deterministic)

Each peril is scored by a dedicated Python function in `utils/risk_scoring.py`. These are **not** AI-generated numbers — they follow explicit, auditable rules. The AI agent selects and invokes the tools; the arithmetic is always deterministic.

**Bushfire Score (weight: 30%)**
- +35 pts — Bushfire Prone Land designation confirmed
- +20 pts — Flame Zone (highest BAL rating)
- +15 pts — Defensible space < 20m (AS3959 minimum)
- +8–15 pts — Vegetation density from DEA Fractional Cover (NDVI proxy)
- +0–15 pts — Current BoM fire danger rating (LOW-MODERATE to CATASTROPHIC)

**Flood Score (weight: 28%)**
- +12–40 pts — Council flood planning overlay (Low / Medium / High category)
- +8–15 pts — GA Surface Hydrology proximity (watercourses/water bodies within 1km)
- +10–20 pts — Floor level relative to 1-in-100-year flood benchmark

**Storm Score (weight: 22%)**
- Base 5 pts — national baseline exposure
- +20 pts — Pre-war construction (built before 1950): no engineered wind resistance standards
- +10 pts — Pre-modern construction (built 1950–1989)
- +10 pts — Tile roof (higher wind uplift risk vs metal)
- +10–30 pts — Cyclone risk band from GA Cyclone Hazard Assessment (tropical properties only)
- Current wind speed is recorded as a contextual observation only — it does **not** affect the score

**Erosion Score (weight: 12%)**
- 0 pts if not a coastal property (GA Smartline returns no coastal features within 500m)
- +25–45 pts — Coastal erosion classification from GA Smartline (MODERATE / HIGH)
- Sandy coasts with confirmed urban/developed backing are capped at MODERATE — sheltered harbour beaches have different erosion dynamics to open-ocean sandy coasts
- +15 pts — Sandy clay soil (elevated coastal erodibility)
- +8 pts — High bare soil coverage (>40%)

**Landslip Score (weight: 8%)**
- Base 5 pts
- +15 pts — Clay-bearing soil (shrink-swell and slope instability risk)
- +10 pts — Seismic hazard PGA > 0.1g (GA data)

### Overall Score Aggregation

```
Overall = (Bushfire × 0.30) + (Flood × 0.28) + (Storm × 0.22) + (Erosion × 0.12) + (Landslip × 0.08)
```

| Score Range | Risk Band |
|---|---|
| 0–34 | LOW-MODERATE |
| 35–54 | MODERATE |
| 55–74 | HIGH |
| 75–100 | VERY HIGH |

> **Note for demo:** A property can have a HIGH individual peril (e.g. erosion 60/100) while remaining in the LOW-MODERATE overall band — because erosion is weighted at only 12%. The mandatory conditions and exclusions triggered by the individual peril score are still applied regardless of the overall band. This is intentional: composite scores are useful for portfolio triage, but individual peril triggers drive policy terms.

### Confidence Score

The model calculates a confidence percentage based on data completeness:
- Starts at 95%
- –5% if property value unavailable
- –4% if flood overlay data unavailable
- –3% each for missing floor area, year built, property type, or bushfire overlay
- Additional –8% if year built is missing AND erosion ≥ 50 (material gap on a high-erosion coastal property)
- Additional –3% if year built is known but pre-1950 (original materials/foundations unverifiable without inspection)

---

## 3. Validation — What Is Checked and On What Basis?

The Validation Agent applies **deterministic rule-based review triggers**, not AI judgement, to decide whether human specialist review is required.

### Human Review Triggers (rule-based — always consistent)

| Trigger | Threshold |
|---|---|
| Erosion score HIGH | ≥ 50/100 → coastal geotechnical specialist review |
| Flood score HIGH | ≥ 40/100 → flood engineer or hydrologist review |
| Overall score HIGH | ≥ 55/100 → senior underwriter sign-off |
| High-value asset at MODERATE+ risk | Value ≥ $2M AND overall ≥ 35 → mandatory senior UW review |
| Missing year built on high-erosion coastal property | year_built = null AND erosion ≥ 50 → structural vintage confirmation required |
| Pre-war construction on high-erosion coastal property | year_built < 1950 AND erosion ≥ 50 → structural engineer inspection required |

### APRA CPS 220 Compliance

APRA Prudential Standard CPS 220 (Risk Management) requires:
- Systematic identification of material risks
- Evidence-based assessment methodology
- Documented audit trail for each decision
- Human oversight for high-risk decisions

PRISM generates a structured compliance note and audit trail for every assessment. The rule-based review triggers (above) replace subjective AI judgement for the escalation decision — this is the key audit-trail property that makes it defensible to a regulator.

---

## 4. Risk Report — Where Does the Data Come From?

The Communication Agent produces a **5-section underwriter report**. Critically, sections 4 and 5 (conditions and exclusions) are generated **deterministically from score thresholds**, not by the AI — meaning the same risk profile always produces the same policy terms, with no drift between runs.

| Report Section | Source |
|---|---|
| **1. Executive Summary** | LLM narrative synthesising overall score, dominant peril, and UW action |
| **2. Property Profile** | Gemini grounded search (value, config, year built, LGA, areas) |
| **3. Peril Assessment** | Each peril's score + factors from the scoring engine — LLM narrates from these only |
| **4. Recommended Underwriting Action** | Validation rule output + deterministic conditions list |
| **5. Policy Conditions & Exclusions** | Deterministic exclusion rules based on triggered perils and soil/construction data |

> **Key demo point:** Sections 4 and 5 are byte-identical between repeat runs for the same property. An underwriter or compliance team can trust that re-running the assessment won't silently change the policy terms. This was a deliberate architectural fix — an earlier version let the LLM generate conditions free-form, which produced different exclusion lists on repeat runs.

---

## 5. Risk Map — How It Works

The map (Folium/Leaflet, OpenStreetMap tiles) shows four toggleable overlay layers at zoom level 15 — showing building footprints, roads, green space, and water bodies for spatial context.

| Layer | Colour | Renders when | Radius |
|---|---|---|---|
| Flood Zone | Blue | `in_flood_planning_zone == True` | 400m |
| Bushfire Prone Land | Red/orange | `bushfire_prone_land == True` | 700m |
| Coastal Erosion Buffer | Amber | Erosion score ≥ 20/100 | 250m |
| Storm Risk Radius | Purple | Storm score ≥ 20/100 | 1,000m |

### Layer Toggle Controls

The four layer checkboxes sit **above** the map in a React panel — not inside the map itself. This keeps the map uncluttered and makes the controls always visible. Layers with no geometry are greyed out with a "no overlay" label so the underwriter can see at a glance which perils are and aren't present without having to click anything.

Toggling a checkbox sends a `postMessage` to the Leaflet iframe, which shows or hides the corresponding `FeatureGroup` layer in real time.

### Overlay Observation Notes

Below the map, a notes section provides a plain-English interpretation for each active overlay:

- **When overlays are active:** one coloured card per active layer, showing the radius, overlay name, a one-sentence description of the hazard significance, and the peril score. Example for Mosman (coastal erosion active): *"250m | Coastal Erosion Buffer — Active coastal erosion zone identified within 250m of the property. Geotechnical specialist assessment may be required. Erosion score: 45/100."*
- **When no overlays fire** (e.g. inner-city Melbourne): a green *"No active hazard overlays — all perils within normal thresholds for this location"* card confirms the blank map is a valid result, not a rendering failure.

### Current Limitations

The circles are **indicative, not geometrically accurate** — they show *that* a hazard applies, not the exact boundary. For production:

| Overlay | Data Source for Accurate Polygons |
|---|---|
| Flood extent | State spatial portals via WFS — NSW Spatial Services, DELWP, QSpatial |
| Bushfire prone land | NSW RFS / state fire authority polygon layers |
| Historical fire perimeters | AFAC national dataset |
| Coastal erosion setbacks | NSW SEPP Coastal Hazards Maps; council coastal management plans |
| Property lot boundary | PSMA/Geoscape cadastral data |

With direct spatial API integrations, the map could show exact polygon overlays with historical event data — a significant differentiator from existing underwriting tools.

---

*PRISM prototype — not for production underwriting decisions.*
*Assessment methodology subject to actuarial review before commercial deployment.*
