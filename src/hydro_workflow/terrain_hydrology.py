"""License-gated terrain and preliminary drainage processing with explicit inputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TerrainHydrologyResult:
    input_dem: str
    fill_requested: bool
    stream_threshold_cells: int
    pour_points: str | None
    snap_distance: float | None
    filled_dem: str | None
    flow_direction: str
    flow_accumulation: str
    stream_raster: str
    drainage_paths: str
    snapped_pour_points: str | None
    watersheds: str | None
    dem_has_nodata: str
    spatial_analyst_status: str
    processed_at: str
    status: str
    review_notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _property(arcpy_adapter: Any, raster: str, property_name: str) -> str:
    result = arcpy_adapter.management.GetRasterProperties(raster, property_name)
    try:
        return str(result[0])
    except (TypeError, IndexError):
        return str(result.getOutput(0))


def prepare_terrain_hydrology(
    project_root: Path,
    dem: str,
    stream_threshold_cells: int,
    fill_dem: bool,
    arcpy_adapter: Any,
    pour_points: str | None = None,
    snap_distance: float | None = None,
) -> TerrainHydrologyResult:
    """Create flow rasters, stream candidates, and optional watershed candidates.

    The threshold, fill choice, pour points, and snap distance are supplied by the user;
    this function does not invent engineering parameters.
    """
    if stream_threshold_cells <= 0:
        raise ValueError("Stream threshold must be a positive number of contributing cells")
    if pour_points and (snap_distance is None or snap_distance <= 0):
        raise ValueError("A positive snap distance is required when pour points are supplied")
    if not arcpy_adapter.Exists(dem):
        raise ValueError(f"Standardized DEM does not exist: {dem}")
    extension_status = arcpy_adapter.CheckExtension("Spatial")
    if extension_status not in {"Available", "CheckedOut"}:
        raise RuntimeError(f"Spatial Analyst is required: {extension_status}")

    root = project_root.expanduser().resolve()
    workspace = json.loads((root / "qa_qc" / "workspace_manifest.json").read_text(encoding="utf-8"))
    geodatabase = Path(workspace["geodatabase"])
    outputs = {
        "filled": str(geodatabase / "terrain_filled"),
        "flow_direction": str(geodatabase / "flow_direction"),
        "flow_accumulation": str(geodatabase / "flow_accumulation"),
        "stream_raster": str(geodatabase / "stream_candidates"),
        "drainage_paths": str(geodatabase / "drainage_path_candidates"),
        "snapped": str(geodatabase / "snapped_pour_points"),
        "watersheds": str(geodatabase / "watershed_candidates"),
    }
    required = [outputs["flow_direction"], outputs["flow_accumulation"], outputs["stream_raster"], outputs["drainage_paths"]]
    if fill_dem: required.append(outputs["filled"])
    if pour_points: required.extend([outputs["snapped"], outputs["watersheds"]])
    existing = [path for path in required if arcpy_adapter.Exists(path)]
    if existing:
        raise FileExistsError(f"Terrain outputs already exist and will not be overwritten: {existing}")

    checked_out_here = extension_status == "Available"
    if checked_out_here:
        arcpy_adapter.CheckOutExtension("Spatial")
    try:
        dem_has_nodata = _property(arcpy_adapter, dem, "ANYNODATA")
        processing_dem = dem
        filled_output = None
        if fill_dem:
            filled = arcpy_adapter.sa.Fill(dem)
            filled.save(outputs["filled"])
            processing_dem = outputs["filled"]
            filled_output = outputs["filled"]

        flow_direction = arcpy_adapter.sa.FlowDirection(processing_dem, "NORMAL", None, "D8")
        flow_direction.save(outputs["flow_direction"])
        flow_accumulation = arcpy_adapter.sa.FlowAccumulation(outputs["flow_direction"], None, "FLOAT", "D8")
        flow_accumulation.save(outputs["flow_accumulation"])
        stream_raster = arcpy_adapter.sa.Con(flow_accumulation >= stream_threshold_cells, 1)
        stream_raster.save(outputs["stream_raster"])
        arcpy_adapter.sa.StreamToFeature(
            outputs["stream_raster"], outputs["flow_direction"], outputs["drainage_paths"], "NO_SIMPLIFY"
        )

        snapped_output = None
        watershed_output = None
        if pour_points:
            snapped = arcpy_adapter.sa.SnapPourPoint(
                pour_points, outputs["flow_accumulation"], snap_distance
            )
            snapped.save(outputs["snapped"])
            watershed = arcpy_adapter.sa.Watershed(outputs["flow_direction"], outputs["snapped"])
            watershed.save(outputs["watersheds"])
            snapped_output, watershed_output = outputs["snapped"], outputs["watersheds"]

        result = TerrainHydrologyResult(
            input_dem=dem, fill_requested=fill_dem,
            stream_threshold_cells=stream_threshold_cells, pour_points=pour_points,
            snap_distance=snap_distance, filled_dem=filled_output,
            flow_direction=outputs["flow_direction"], flow_accumulation=outputs["flow_accumulation"],
            stream_raster=outputs["stream_raster"], drainage_paths=outputs["drainage_paths"],
            snapped_pour_points=snapped_output, watersheds=watershed_output,
            dem_has_nodata=dem_has_nodata, spatial_analyst_status=extension_status,
            processed_at=datetime.now(timezone.utc).isoformat(), status="REVIEW",
            review_notes=(
                "REVIEW REQUIRED: fill choice, threshold, NoData, DEM fitness, stream candidates, "
                "pour points, snap distance, watershed boundaries, and all engineering use require approval."
            ),
        )
        (root / "qa_qc" / "terrain_hydrology_report.json").write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result
    finally:
        if checked_out_here:
            arcpy_adapter.CheckInExtension("Spatial")
