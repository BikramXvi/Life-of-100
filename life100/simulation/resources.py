"""Natural resources. SRS §6.7.

Tracked as city-level stocks, updated additively alongside the existing
(tested, demo-verified) food-price mechanism in economy.py — this adds the
SRS-named resource entity and gives `RESOURCE_EXTRACTED` a real emitter
without touching the price cascade that's already working end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass

FOOD_YIELD_PER_WORKER = 15.0
FOOD_CONSUMPTION_PER_CAPITA = 3.0
RAW_MATERIAL_USE_PER_WORKER = 5.0
DROUGHT_PRODUCTION_MULTIPLIER = 0.5


@dataclass
class Resources:
    food_stock: float = 2000.0
    water_stock: float = 2000.0
    energy_stock: float = 2000.0
    land_available: float = 500.0
    raw_materials_stock: float = 5000.0
