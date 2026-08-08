"""End-to-end orchestration for the site hydrology ArcGIS workflow."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .authoritative_acquisition import acquire_catalog_sources, stage_existing_map_sources
from .boundary_validation import import_and_validate_boundary, import_kml_boundary
from .crossing_screening import screen_crossings
from .data_standardization import validate_standardize_data
from .hec_ras_package import build_hec_ras_review_package
from .hydrologic_response import combine_land_cover_soils
from .project_workspace import create_project_workspace
from .qa_package import generate_qa_package
from .terrain_hydrology import prepare_terrain_hydrology
from .kmz_inspector import list_kml_polygon_names
from .workflow_preferences import unit_preferences


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
    boundary_polygon_name: str | None = None,
    unit_system: str = "Imperial",
    soil_group_source_name: str | None = None,
    existing_map_sources: dict[str, str] | None = None,
) -> CompleteWorkflowResult:
    """Run all implemented operations and stop at the first unsafe condition."""
    units = unit_preferences(unit_system)
    workspace = create_project_workspace(project_name, projects_root, arcpy_adapter)
    root = Path(workspace.project_root)
    boundary_path = Path(boundary)
    if boundary_path.suffix.lower() in {".kml", ".kmz"}:
        polygon_names = list_kml_polygon_names(boundary_path)
        selected_name = boundary_polygon_name
        if not selected_name:
            preferred = [
                name for name in polygon_names
                if "boundary" in name.lower()
                and not any(token in name.lower() for token in ("row", "right of way", "corridor"))
            ]
            if len(polygon_names) == 1:
                selected_name = polygon_names[0]
            elif len(preferred) == 1:
                selected_name = preferred[0]
            else:
                raise ValueError(
                    "Select the project boundary polygon from the KMZ. Available names: "
                    + ", ".join(polygon_names)
                )
        _, boundary_result = import_kml_boundary(
            boundary_path, root, arcpy_adapter, selected_name, target_crs, polygon_names
        )
    else:
        boundary_result = import_and_validate_boundary(boundary, root, arcpy_adapter, target_crs)

    (root / "qa_qc" / "workflow_preferences.json").write_text(
        json.dumps({
            "unit_system": units.name,
            "horizontal_distance": units.horizontal_distance,
            "elevation": units.elevation,
            "area": units.area,
            "rainfall": units.rainfall,
            "soil_group_policy": "Dual or mixed hydrologic soil groups are screened as D; REVIEW REQUIRED.",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    acquired = (
        stage_existing_map_sources(root, existing_map_sources, arcpy_adapter)
        if existing_map_sources
        else acquire_catalog_sources(root, sources, arcpy_adapter)
    )
    acquisition_failures = [item for item in acquired if item.status == "FAIL"]
    failed_by_name = {item.source_name: item for item in acquisition_failures}
    if dem_source_name in failed_by_name:
        failure = failed_by_name[dem_source_name]
        raise RuntimeError(
            f"Required DEM acquisition failed for {dem_source_name}: {failure.message}. "
            f"Review the acquisition record under {root / 'data' / 'original' / 'authoritative'} "
            "or rerun with Existing Map Layers and select an approved DEM."
        )
    standardized = validate_standardize_data(root, target_crs, arcpy_adapter)
    failed_standard = [item.source_name for item in standardized if item.status == "FAIL"]
    if dem_source_name in failed_standard:
        raise RuntimeError(
            f"Required DEM standardization failed for {dem_source_name}. "
            f"Review {root / 'qa_qc' / 'data_standardization_report.json'}."
        )
    by_name = {item.source_name: item.standardized_dataset for item in standardized}
    if not by_name.get(dem_source_name): raise ValueError(f"DEM source was not standardized: {dem_source_name}")

    terrain = prepare_terrain_hydrology(
        root, by_name[dem_source_name], stream_threshold_cells, fill_dem, arcpy_adapter,
        pour_points, snap_distance,
    )
    crossings_output = None
    crossings_report = root / "qa_qc" / "crossing_screening_report.json"
    if by_name.get(roads_source_name):
        crossings = screen_crossings(
            root, by_name[roads_source_name], terrain.drainage_paths, arcpy_adapter,
            by_name.get(bridges_source_name) if bridges_source_name else None,
            by_name.get(culverts_source_name) if culverts_source_name else None,
            structure_search_distance,
        )
        crossings_output = crossings.screened_crossings
    else:
        crossings_report.write_text(
            json.dumps({
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "status": "REVIEW",
                "roads_source": roads_source_name,
                "screened_crossings": None,
                "review_notes": (
                    "REVIEW REQUIRED: road acquisition was unavailable, so road/drainage "
                    "crossing screening was skipped. Rerun with Existing Map Layers and an "
                    "approved road layer, or add a validated DOT/local road service."
                ),
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if land_cover_source_name and soil_group_source_name:
        land_cover_dataset = by_name.get(land_cover_source_name)
        soil_group_dataset = by_name.get(soil_group_source_name)
        if land_cover_dataset and soil_group_dataset:
            combine_land_cover_soils(
                root, land_cover_dataset, soil_group_dataset, arcpy_adapter
            )
    hec = build_hec_ras_review_package(
        root, terrain.filled_dem or by_name[dem_source_name], arcpy_adapter,
        {
            "stream_centerlines": terrain.drainage_paths,
            "bank_lines": None,
            "flow_paths": terrain.drainage_paths,
            "cross_sections": None,
            "crossings": crossings_output,
        },
    )
    qa_json, _ = generate_qa_package(root)
    optional_failures = sorted({item.source_name for item in acquisition_failures} | set(failed_standard))
    acquisition_messages = {
        item.source_name: " ".join(str(item.message).split())[:300]
        for item in acquisition_failures
    }
    optional_details = "; ".join(
        f"{name}: {acquisition_messages.get(name, 'working dataset was not standardized')}"
        for name in optional_failures
    )
    optional_note = (
        " Optional sources unavailable and recorded for follow-up: " + optional_details + "."
        if optional_failures else ""
    )
    result = CompleteWorkflowResult(
        str(root), boundary_result.imported_boundary, len(acquired), len(standardized),
        str(root / "qa_qc" / "terrain_hydrology_report.json"),
        str(crossings_report), hec.package_root,
        str(qa_json), datetime.now(timezone.utc).isoformat(), "REVIEW",
        ("REVIEW REQUIRED: preliminary screening workflow; not final engineering approval "
         "or a runnable HEC-RAS model." + optional_note),
    )
    (root / "qa_qc" / "complete_workflow_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
