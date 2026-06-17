"""Simulated data for proprietary sources (CoreLogic, satellite, claims, ISI)."""

import random
import hashlib


def _seed(address: str) -> int:
    return int(hashlib.md5(address.encode()).hexdigest(), 16) % 10000


def fetch_property_data(address: str) -> dict:
    """Simulated CoreLogic / PSMA property record."""
    r = random.Random(_seed(address))
    year_built = r.randint(1985, 2018)
    stories = r.choice([1, 1, 2, 2, 3])
    return {
        "source": "CoreLogic (simulated)",
        "address": address,
        "estimated_value_aud": r.randint(5_000_000, 28_000_000),
        "land_area_sqm": r.randint(800, 5000),
        "floor_area_sqm": r.randint(350, 1200),
        "year_built": year_built,
        "construction_type": r.choice(["Brick Veneer", "Rendered Masonry", "Steel Frame", "Timber Frame"]),
        "roof_type": r.choice(["Colorbond Steel", "Terracotta Tile", "Concrete Tile"]),
        "stories": stories,
        "pool": r.choice([True, False]),
        "last_sale_price_aud": r.randint(4_500_000, 25_000_000),
        "council_zone": r.choice(["R2 Low Density Residential", "E4 Environmental Living"]),
    }


def fetch_satellite_analysis(address: str) -> dict:
    """Simulated Sentinel-2 NDVI and vegetation analysis."""
    r = random.Random(_seed(address) + 1)
    ndvi = round(r.uniform(0.25, 0.75), 3)
    defensible_space_m = r.randint(8, 45)
    return {
        "source": "Sentinel-2 NDVI Analysis (simulated)",
        "ndvi_score": ndvi,
        "vegetation_density": "High" if ndvi > 0.6 else ("Moderate" if ndvi > 0.4 else "Low"),
        "defensible_space_m": defensible_space_m,
        "defensible_space_adequate": defensible_space_m >= 20,
        "tree_canopy_cover_pct": r.randint(15, 65),
        "vegetation_type": r.choice([
            "Eucalyptus Woodland",
            "Coastal Scrub",
            "Mixed Bushland",
            "Manicured Garden with Trees",
        ]),
        "last_image_date": "2026-05-14",
    }


def fetch_historical_claims(address: str, radius_km: int = 5) -> dict:
    """Simulated ISI claims database — historical claims within radius."""
    r = random.Random(_seed(address) + 2)
    total_claims = r.randint(3, 22)
    return {
        "source": "ISI Claims Database (simulated)",
        "radius_km": radius_km,
        "total_claims_10yr": total_claims,
        "bushfire_claims": r.randint(0, max(1, total_claims // 3)),
        "flood_claims": r.randint(0, max(1, total_claims // 2)),
        "storm_claims": r.randint(1, max(2, total_claims // 2)),
        "avg_claim_value_aud": r.randint(180_000, 2_400_000),
        "largest_claim_aud": r.randint(500_000, 8_500_000),
        "trend": r.choice(["Increasing", "Stable", "Increasing"]),
    }


def fetch_flood_overlay(address: str) -> dict:
    """Simulated council flood planning overlay data."""
    r = random.Random(_seed(address) + 3)
    in_flood_zone = r.random() < 0.45
    return {
        "source": "Council Flood Planning Overlay (simulated)",
        "in_flood_planning_zone": in_flood_zone,
        "flood_category": r.choice(["High Flood Risk", "Medium Flood Risk", "Low Flood Risk"]) if in_flood_zone else "No Overlay",
        "1_in_100_year_level_m": round(r.uniform(1.2, 4.8), 1) if in_flood_zone else None,
        "floor_level_above_flood_m": round(r.uniform(-0.3, 1.5), 2) if in_flood_zone else None,
        "stormwater_infrastructure": r.choice(["Adequate", "Undersized", "Under Review"]),
        "overland_flow_path": r.choice([True, False]),
    }


def fetch_bushfire_overlay(address: str) -> dict:
    """Simulated RFS/CFA bushfire prone land overlay."""
    r = random.Random(_seed(address) + 4)
    bpl = r.random() < 0.60
    return {
        "source": "RFS Bushfire Prone Land (simulated)",
        "bushfire_prone_land": bpl,
        "bpl_category": r.choice(["Vegetation Category 1", "Vegetation Category 2", "Vegetation Buffer"]) if bpl else "Not BPL",
        "flame_zone": r.random() < 0.15 if bpl else False,
        "asset_protection_zone_m": r.randint(10, 50) if bpl else None,
        "nearest_fire_station_km": round(r.uniform(2.5, 18.0), 1),
        "access_road_width_m": r.choice([3.5, 4.0, 6.0, 6.0]),
    }
