"""Validated workflow preferences and hydrologic classification policy."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


UNIT_SYSTEMS = ("Imperial", "Metric")


@dataclass(frozen=True)
class UnitPreferences:
    name: str
    horizontal_distance: str
    elevation: str
    area: str
    rainfall: str


def unit_preferences(value: str) -> UnitPreferences:
    """Return explicit display/output units without changing source measurements."""
    normalized = value.strip().lower()
    if normalized == "imperial":
        return UnitPreferences("Imperial", "feet", "feet", "acres", "inches")
    if normalized == "metric":
        return UnitPreferences("Metric", "meters", "meters", "hectares", "millimeters")
    raise ValueError(f"Unit system must be one of: {', '.join(UNIT_SYSTEMS)}")


def conservative_soil_group(value: str | None) -> str:
    """Normalize NRCS hydrologic soil groups using the approved conservative policy.

    Dual groups such as A/D, B/D, and C/D represent drained/undrained alternatives.
    This workflow assigns every dual or mixed group to D for preliminary screening.
    Final interpretation remains REVIEW REQUIRED.
    """
    if value is None or not value.strip():
        return "UNKNOWN"
    normalized = value.upper().replace(" ", "")
    if any(separator in normalized for separator in ("/", "-", ",", ";")):
        return "D"
    if normalized in {"A", "B", "C", "D"}:
        return normalized
    return "UNKNOWN"


def load_engineering_lookup(path: Path) -> dict[str, object]:
    """Load an explicitly approved lookup; never invent CN, n, or infiltration values."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("approval_status") != "APPROVED":
        raise ValueError("Engineering lookup must have approval_status=APPROVED")
    if not payload.get("approved_by") or not payload.get("approved_date"):
        raise ValueError("Engineering lookup requires approved_by and approved_date")
    for key in ("curve_numbers", "mannings_n", "infiltration_rates"):
        if not isinstance(payload.get(key), dict) or not payload[key]:
            raise ValueError(f"Engineering lookup requires a non-empty {key} table")
    return payload
