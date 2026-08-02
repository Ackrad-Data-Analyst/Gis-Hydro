"""Validate acquired GIS outputs and create standardized working copies."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StandardizationResult:
    source_name: str
    input_dataset: str
    standardized_dataset: str | None
    data_type: str | None
    feature_count: int | None
    rows: int | None
    columns: int | None
    native_cell_width: float | None
    native_cell_height: float | None
    source_crs: str | None
    target_crs: str
    extent_coverage_percent: float | None
    resampling: str | None
    processed_at: str
    status: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")[:110]


def _count(result: Any) -> int:
    try:
        return int(result[0])
    except (TypeError, IndexError):
        return int(result.getOutput(0))


def _coverage_percent(dataset_extent: Any, boundary_extent: Any) -> float:
    width = max(0.0, min(dataset_extent.XMax, boundary_extent.XMax) - max(dataset_extent.XMin, boundary_extent.XMin))
    height = max(0.0, min(dataset_extent.YMax, boundary_extent.YMax) - max(dataset_extent.YMin, boundary_extent.YMin))
    boundary_area = max(0.0, boundary_extent.XMax - boundary_extent.XMin) * max(
        0.0, boundary_extent.YMax - boundary_extent.YMin
    )
    return round((width * height / boundary_area * 100.0), 3) if boundary_area else 0.0


def _latest_acquisition_manifest(root: Path) -> Path:
    manifests = sorted((root / "qa_qc").glob("acquisition_manifest_*.json"), key=lambda path: path.stat().st_mtime)
    if not manifests:
        raise ValueError("No acquisition manifest found; download authoritative data first")
    return manifests[-1]


def validate_standardize_data(project_root: Path, target_crs: Any, arcpy_adapter: Any) -> list[StandardizationResult]:
    """Inspect each acquired output and create a projected working copy.

    Extent coverage is a screening metric, not proof of valid pixel/feature coverage.
    Original downloaded files and first-stage working datasets remain unchanged.
    """
    root = project_root.expanduser().resolve()
    workspace = json.loads((root / "qa_qc" / "workspace_manifest.json").read_text(encoding="utf-8"))
    boundary_info = json.loads((root / "qa_qc" / "boundary_validation.json").read_text(encoding="utf-8"))
    geodatabase = Path(workspace["geodatabase"])
    boundary = boundary_info["imported_boundary"]
    boundary_extent = arcpy_adapter.Describe(boundary).extent
    target_name = str(getattr(target_crs, "name", target_crs))
    if not target_name or target_name == "Unknown":
        raise ValueError("A known target coordinate system is required")

    acquisitions = json.loads(_latest_acquisition_manifest(root).read_text(encoding="utf-8"))
    results: list[StandardizationResult] = []
    for record in acquisitions:
        source_name = record["source_name"]
        input_dataset = record.get("working_output")
        if record["status"] == "FAIL" or not input_dataset or not arcpy_adapter.Exists(input_dataset):
            results.append(StandardizationResult(
                source_name, input_dataset or "", None, None, None, None, None, None, None,
                None, target_name, None, record.get("query_parameters", {}).get("resampling"),
                datetime.now(timezone.utc).isoformat(), "FAIL", "Acquired working dataset is unavailable.",
            ))
            continue

        description = arcpy_adapter.Describe(input_dataset)
        data_type = str(getattr(description, "dataType", "Unknown"))
        source_crs = str(getattr(getattr(description, "spatialReference", None), "name", "Unknown"))
        output = str(geodatabase / f"std_{_safe_name(source_name)}")
        if arcpy_adapter.Exists(output):
            raise FileExistsError(f"Standardized dataset exists and will not be overwritten: {output}")

        is_raster = "raster" in data_type.lower()
        feature_count = None if is_raster else _count(arcpy_adapter.management.GetCount(input_dataset))
        rows = int(getattr(description, "height", 0)) or None if is_raster else None
        columns = int(getattr(description, "width", 0)) or None if is_raster else None
        cell_width = float(getattr(description, "meanCellWidth", 0)) or None if is_raster else None
        cell_height = float(getattr(description, "meanCellHeight", 0)) or None if is_raster else None
        coverage = _coverage_percent(description.extent, boundary_extent)
        resampling = record.get("query_parameters", {}).get("resampling") or "NEAREST"

        if is_raster:
            arcpy_adapter.management.ProjectRaster(input_dataset, output, target_crs, resampling)
        else:
            arcpy_adapter.management.Project(input_dataset, output, target_crs)
        results.append(StandardizationResult(
            source_name, input_dataset, output, data_type, feature_count, rows, columns,
            cell_width, cell_height, source_crs, target_name, coverage, resampling,
            datetime.now(timezone.utc).isoformat(), "REVIEW",
            ("Projection completed. Extent overlap is a screening value only; datum transformation, "
             "true data coverage, schema, NoData, currency, accuracy, and suitability are REVIEW REQUIRED."),
        ))

    report = root / "qa_qc" / "data_standardization_report.json"
    report.write_text(json.dumps([item.to_dict() for item in results], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results
