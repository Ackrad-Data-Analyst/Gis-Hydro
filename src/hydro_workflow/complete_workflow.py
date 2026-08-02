"""End-to-end orchestration for the site hydrology ArcGIS workflow."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .authoritative_acquisition import acquire_catalog_sources
from .boundary_validation import import_and_validate_boundary
from .crossing_screening import screen_crossings
from .data_standardization import validate_standardize_data
from .hec_ras_package import build_hec_ras_review_package
from .project_workspace import create_project_workspace
from .qa_package import generate_qa_package
from .terrain_hydrology import prepare_terrain_hydrology


@dataclass(frozen=True)
class CompleteWorkflowResult:
    project_root: str
    boundary: str
    acquired_sources: int
    standardized_sources: int
    terrain_report: str
    crossings_report: str
    hec_ras_package: str
    qa_package: str
    completed_at: str
    status: str
    review_notes: str
    def to_dict(self) -> dict[str, object]: return asdict(self)


def run_complete_workflow(
    project_name: str,
    projects_root: Path,
    boundary: str,
    target_crs: Any,
    sources: list[dict[str, str]],
    dem_source_name: str,
    roads_source_name: str,
    stream_threshold_cells: int,
    fill_dem: bool,
    arcpy_adapter: Any,
    bridges_source_name: str | None = None,
    culverts_source_name: str | None = None,
    structure_search_distance: str | None = None,
    pour_points: str | None = None,
    snap_distance: float | None = None,
    land_cover_source_name: str | None = None,
) -> CompleteWorkflowResult:
    """Run all implemented operations and stop at the first unsafe condition."""
    workspace = create_project_workspace(project_name, projects_root, arcpy_adapter)
    root = Path(workspace.project_root)
    boundary_result = import_and_validate_boundary(boundary, root, arcpy_adapter, target_crs)
    acquired = acquire_catalog_sources(root, sources, arcpy_adapter)
    failures = [item.source_name for item in acquired if item.status == "FAIL"]
    if failures: raise RuntimeError(f"Acquisition failed for: {', '.join(failures)}")
    standardized = validate_standardize_data(root, target_crs, arcpy_adapter)
    failed_standard = [item.source_name for item in standardized if item.status == "FAIL"]
    if failed_standard: raise RuntimeError(f"Standardization failed for: {', '.join(failed_standard)}")
    by_name = {item.source_name: item.standardized_dataset for item in standardized}
    if not by_name.get(dem_source_name): raise ValueError(f"DEM source was not standardized: {dem_source_name}")
    if not by_name.get(roads_source_name): raise ValueError(f"Road source was not standardized: {roads_source_name}")

    terrain = prepare_terrain_hydrology(
        root, by_name[dem_source_name], stream_threshold_cells, fill_dem, arcpy_adapter,
        pour_points, snap_distance,
    )
    crossings = screen_crossings(
        root, by_name[roads_source_name], terrain.drainage_paths, arcpy_adapter,
        by_name.get(bridges_source_name) if bridges_source_name else None,
        by_name.get(culverts_source_name) if culverts_source_name else None,
        structure_search_distance,
    )
    hec = build_hec_ras_review_package(
        root, terrain.filled_dem or by_name[dem_source_name], arcpy_adapter,
        {
            "stream_centerlines": terrain.drainage_paths,
            "bank_lines": None,
            "flow_paths": terrain.drainage_paths,
            "cross_sections": None,
            "crossings": crossings.screened_crossings,
            "land_cover": by_name.get(land_cover_source_name) if land_cover_source_name else None,
        },
    )
    qa_json, _ = generate_qa_package(root)
    result = CompleteWorkflowResult(
        str(root), boundary_result.imported_boundary, len(acquired), len(standardized),
        str(root / "qa_qc" / "terrain_hydrology_report.json"),
        str(root / "qa_qc" / "crossing_screening_report.json"), hec.package_root,
        str(qa_json), datetime.now(timezone.utc).isoformat(), "REVIEW",
        "REVIEW REQUIRED: preliminary screening workflow; not final engineering approval or a runnable HEC-RAS model.",
    )
    (root / "qa_qc" / "complete_workflow_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
