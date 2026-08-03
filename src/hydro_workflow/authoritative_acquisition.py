"""Catalog-driven ArcGIS acquisition for any configured vector or image service."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AcquisitionResult:
    source_name: str
    category: str
    agency: str
    service_url: str
    operation: str
    requested_at: str
    completed_at: str
    query_parameters: dict[str, str]
    original_output: str | None
    working_output: str | None
    sha256: str | None
    coordinate_system: str | None
    resolution_or_scale: str | None
    coverage: str
    status: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not name:
        raise ValueError("Source name cannot be converted to a safe output name")
    return name[:120]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_workspace(project_root: Path) -> tuple[Path, Path, str]:
    root = project_root.expanduser().resolve()
    manifest_path = root / "qa_qc" / "workspace_manifest.json"
    boundary_report = root / "qa_qc" / "boundary_validation.json"
    if not manifest_path.is_file() or not boundary_report.is_file():
        raise ValueError("Create the project workspace and validate its boundary before acquisition")
    workspace = json.loads(manifest_path.read_text(encoding="utf-8"))
    boundary = json.loads(boundary_report.read_text(encoding="utf-8"))["imported_boundary"]
    geodatabase = Path(workspace["geodatabase"])
    if not geodatabase.is_dir():
        raise ValueError(f"Project geodatabase is missing: {geodatabase}")
    return root, geodatabase, boundary


def _describe_output(arcpy_adapter: Any, output: str) -> tuple[str | None, str | None]:
    description = arcpy_adapter.Describe(output)
    spatial_reference = getattr(description, "spatialReference", None)
    crs = getattr(spatial_reference, "name", None)
    cell_width = getattr(description, "meanCellWidth", None)
    cell_height = getattr(description, "meanCellHeight", None)
    resolution = f"cell={cell_width} x {cell_height}" if cell_width and cell_height else None
    return crs, resolution


def _existing_success(source_folder: Path, arcpy_adapter: Any) -> AcquisitionResult | None:
    """Return a completed acquisition without replacing its immutable source file."""
    record_path = source_folder / "acquisition_record.json"
    if not record_path.is_file():
        return None
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        result = AcquisitionResult(**payload)
    except (OSError, ValueError, TypeError):
        return None
    if (
        result.status == "REVIEW"
        and result.original_output
        and Path(result.original_output).is_file()
        and result.working_output
        and arcpy_adapter.Exists(result.working_output)
    ):
        return result
    return None


def acquire_catalog_sources(
    project_root: Path,
    sources: list[dict[str, str]],
    arcpy_adapter: Any,
    selected_names: set[str] | None = None,
) -> list[AcquisitionResult]:
    """Acquire every selected catalog row using its configured operation.

    The function has no fixed agency or dataset-name list. New valid catalog rows are
    processed automatically when their source type and operation are supported.
    """
    root, geodatabase, boundary = _load_workspace(project_root)
    original_root = root / "data" / "original" / "authoritative"
    original_root.mkdir(parents=True, exist_ok=True)
    run_started = datetime.now(timezone.utc).isoformat()
    results: list[AcquisitionResult] = []

    for source in sources:
        if selected_names and source["name"] not in selected_names:
            continue
        requested_at = datetime.now(timezone.utc).isoformat()
        safe_name = _safe_name(source["name"])
        source_folder = original_root / safe_name
        if source_folder.exists():
            completed = _existing_success(source_folder, arcpy_adapter)
            if completed is not None:
                results.append(completed)
                continue
            retry_suffix = requested_at.replace(":", "").replace("+", "_").replace(".", "_")
            source_folder = original_root / f"{safe_name}_retry_{retry_suffix}"
        source_folder.mkdir(parents=True, exist_ok=False)
        original_output: Path | None = None
        working_output: str | None = None
        query = {
            "where": source.get("filter", "") or "1=1",
            "operation": source["operation"],
            "resampling": source["resampling"],
            "boundary": boundary,
        }
        try:
            if source["operation"] in {"spatial_query_clip", "select_intersecting_copy"}:
                layer_name = f"{safe_name}_query"
                arcpy_adapter.management.MakeFeatureLayer(
                    source["rest_url"], layer_name, query["where"]
                )
                arcpy_adapter.management.SelectLayerByLocation(
                    layer_name, "INTERSECT", boundary, selection_type="NEW_SELECTION"
                )
                # ArcGIS writes GeoJSON only when the output has a GeoJSON extension.
                original_output = source_folder / f"{safe_name}.geojson"
                arcpy_adapter.conversion.FeaturesToJSON(
                    layer_name, str(original_output), "FORMATTED", "NO_Z_VALUES", "NO_M_VALUES", "GEOJSON"
                )
                working_output = str(geodatabase / safe_name)
                if arcpy_adapter.Exists(working_output):
                    raise FileExistsError(f"Working dataset exists: {working_output}")
                arcpy_adapter.conversion.JSONToFeatures(str(original_output), working_output)
                if source["operation"] == "spatial_query_clip":
                    clipped = str(geodatabase / f"{safe_name}_clip")
                    arcpy_adapter.analysis.Clip(working_output, boundary, clipped)
                    working_output = clipped
            elif source["operation"] == "extract":
                original_output = source_folder / f"{safe_name}.tif"
                extent = arcpy_adapter.Describe(boundary).extent
                rectangle = f"{extent.XMin} {extent.YMin} {extent.XMax} {extent.YMax}"
                raster_input = source["rest_url"]
                configured_filter = source.get("filter", "").strip()
                if configured_filter:
                    raster_input = f"{safe_name}_filtered_image"
                    arcpy_adapter.management.MakeImageServerLayer(
                        source["rest_url"], raster_input, where_clause=configured_filter
                    )
                arcpy_adapter.management.Clip(
                    raster_input, rectangle, str(original_output), boundary,
                    "", "ClippingGeometry", "NO_MAINTAIN_EXTENT",
                )
                working_output = str(geodatabase / safe_name)
                if arcpy_adapter.Exists(working_output):
                    raise FileExistsError(f"Working raster exists: {working_output}")
                arcpy_adapter.management.CopyRaster(str(original_output), working_output)
            else:
                raise ValueError(f"Unsupported configured operation: {source['operation']}")

            if original_output is None or not original_output.is_file():
                raise RuntimeError("ArcGIS reported success but no original acquisition file was created")
            crs, resolution = _describe_output(arcpy_adapter, working_output)
            result = AcquisitionResult(
                source_name=source["name"], category=source["category"],
                agency=source["source_agency"], service_url=source["rest_url"],
                operation=source["operation"], requested_at=requested_at,
                completed_at=datetime.now(timezone.utc).isoformat(), query_parameters=query,
                original_output=str(original_output), working_output=working_output,
                sha256=_sha256(original_output), coordinate_system=crs,
                resolution_or_scale=resolution, coverage="INTERSECTS_BOUNDARY",
                status="REVIEW",
                message=("Acquisition completed. Coverage percentage, currency, schema, datum, "
                         "resolution, and engineering suitability are REVIEW REQUIRED."),
            )
        except Exception as error:
            result = AcquisitionResult(
                source_name=source["name"], category=source["category"],
                agency=source["source_agency"], service_url=source["rest_url"],
                operation=source["operation"], requested_at=requested_at,
                completed_at=datetime.now(timezone.utc).isoformat(), query_parameters=query,
                original_output=str(original_output) if original_output else None,
                working_output=working_output, sha256=None, coordinate_system=None,
                resolution_or_scale=None, coverage="UNKNOWN", status="FAIL", message=str(error),
            )
        (source_folder / "acquisition_record.json").write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        results.append(result)

    run_report = root / "qa_qc" / f"acquisition_manifest_{run_started.replace(':', '').replace('+', '_')}.json"
    run_report.write_text(
        json.dumps([record.to_dict() for record in results], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return results


def stage_existing_map_sources(
    project_root: Path,
    layer_roles: dict[str, str],
    arcpy_adapter: Any,
) -> list[AcquisitionResult]:
    """Snapshot explicitly selected map layers so they can replace network acquisition.

    Map symbology is not treated as provenance. Each selected dataset is copied to the
    project geodatabase and recorded in the same manifest used by standardization.
    """
    root, geodatabase, boundary = _load_workspace(project_root)
    requested_at = datetime.now(timezone.utc).isoformat()
    results: list[AcquisitionResult] = []
    for source_name, dataset in layer_roles.items():
        safe_name = _safe_name(source_name)
        output = str(geodatabase / safe_name)
        if arcpy_adapter.Exists(output):
            raise FileExistsError(f"Staged map dataset exists and will not be overwritten: {output}")
        description = arcpy_adapter.Describe(dataset)
        data_type = str(getattr(description, "dataType", ""))
        if "raster" in data_type.lower():
            arcpy_adapter.management.CopyRaster(dataset, output)
        else:
            arcpy_adapter.analysis.Clip(dataset, boundary, output)
        crs, resolution = _describe_output(arcpy_adapter, output)
        results.append(AcquisitionResult(
            source_name=source_name, category="Existing approved map layer",
            agency="Supplied ArcGIS map", service_url=str(dataset), operation="snapshot_from_map",
            requested_at=requested_at, completed_at=datetime.now(timezone.utc).isoformat(),
            query_parameters={"boundary": boundary, "selection": "explicit operator layer role"},
            original_output=None, working_output=output, sha256=None, coordinate_system=crs,
            resolution_or_scale=resolution, coverage="CLIPPED_OR_COPIED_FOR_PROJECT", status="REVIEW",
            message="Map layer snapshot completed; ownership, currency, license, and engineering suitability are REVIEW REQUIRED.",
        ))
    report = root / "qa_qc" / f"acquisition_manifest_{requested_at.replace(':', '').replace('+', '_')}.json"
    report.write_text(json.dumps([item.to_dict() for item in results], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results
