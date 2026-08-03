"""Create combined land-cover/soil response units without inventing parameters."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HydrologicResponseResult:
    land_cover: str
    soil_groups: str
    combined_raster: str
    processed_at: str
    status: str
    review_notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def combine_land_cover_soils(
    project_root: Path, land_cover: str, soil_groups: str, arcpy_adapter: Any
) -> HydrologicResponseResult:
    """Combine aligned categorical rasters into response units for reviewed lookups."""
    if not arcpy_adapter.Exists(land_cover):
        raise ValueError(f"Land-cover raster does not exist: {land_cover}")
    if not arcpy_adapter.Exists(soil_groups):
        raise ValueError(f"Soil-group raster does not exist: {soil_groups}")
    root = project_root.expanduser().resolve()
    workspace = json.loads((root / "qa_qc" / "workspace_manifest.json").read_text(encoding="utf-8"))
    output = str(Path(workspace["geodatabase"]) / "hydrologic_response_units")
    if arcpy_adapter.Exists(output):
        raise FileExistsError(f"Combined response raster exists and will not be overwritten: {output}")
    extension = arcpy_adapter.CheckExtension("Spatial")
    if extension not in {"Available", "CheckedOut"}:
        raise RuntimeError(f"Spatial Analyst is required to combine land cover and soils: {extension}")
    checked_out_here = extension == "Available"
    if checked_out_here:
        arcpy_adapter.CheckOutExtension("Spatial")
    try:
        combined = arcpy_adapter.sa.Combine([land_cover, soil_groups])
        combined.save(output)
    finally:
        if checked_out_here:
            arcpy_adapter.CheckInExtension("Spatial")
    result = HydrologicResponseResult(
        land_cover, soil_groups, output, datetime.now(timezone.utc).isoformat(), "REVIEW",
        "REVIEW REQUIRED: categorical alignment, soil-group labels, dual groups screened as D, "
        "and any curve-number, Manning's n, or infiltration lookup require an approved profile.",
    )
    (root / "qa_qc" / "hydrologic_response_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
