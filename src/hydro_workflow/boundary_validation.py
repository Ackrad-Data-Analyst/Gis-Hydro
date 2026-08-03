"""Read-only boundary import and validation for an ArcGIS project workspace."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class ArcPyBoundaryAdapter(Protocol):
    def Exists(self, path: str) -> bool: ...
    def Describe(self, value: str) -> Any: ...

    class conversion(Protocol):
        @staticmethod
        def KMLToLayer(value: str, output_folder: str, output_name: str, *args: Any): ...

    class management(Protocol):
        @staticmethod
        def GetCount(value: str): ...
        @staticmethod
        def CheckGeometry(value: str, output_table: str): ...
        @staticmethod
        def CopyFeatures(value: str, output: str): ...
        @staticmethod
        def Project(value: str, output: str, spatial_reference: Any): ...
        @staticmethod
        def MakeFeatureLayer(value: str, output: str, where_clause: str | None = None): ...


@dataclass(frozen=True)
class BoundaryValidationResult:
    source: str
    imported_boundary: str
    validated_at: str
    feature_count: int
    geometry_type: str
    source_spatial_reference: str
    source_wkid: int | None
    output_spatial_reference: str
    extent: dict[str, float]
    source_sha256: str | None
    geometry_error_count: int
    status: str
    review_notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BoundaryCandidateResult:
    """Read-only KML/KMZ conversion result requiring an operator selection."""

    source: str
    source_sha256: str
    converted_at: str
    output_geodatabase: str
    polygon_candidates: tuple[str, ...]
    status: str
    review_notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _result_count(result: Any) -> int:
    try:
        return int(result[0])
    except (TypeError, IndexError):
        return int(result.getOutput(0))


def _hash_file(path_text: str) -> str | None:
    path = Path(path_text)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_workspace(project_root: Path) -> tuple[Path, Path]:
    root = project_root.expanduser().resolve()
    manifest_path = root / "qa_qc" / "workspace_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Not a Site Hydrology project workspace: {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    geodatabase = Path(manifest["geodatabase"])
    if not geodatabase.is_dir():
        raise ValueError(f"Project geodatabase is missing: {geodatabase}")
    return root, geodatabase


def prepare_kml_boundary_candidates(
    source: Path,
    project_root: Path,
    arcpy_adapter: ArcPyBoundaryAdapter,
) -> BoundaryCandidateResult:
    """Convert a KML/KMZ into working polygon candidates without changing it.

    KML/KMZ files can contain rights-of-way, corridors, and other polygons in
    addition to the actual project boundary.  This function deliberately does
    not guess which polygon is the project extent; the operator must review and
    select the correct polygon candidate before boundary validation.
    """
    root, _ = _load_workspace(project_root)
    source_path = source.expanduser().resolve()
    if source_path.suffix.lower() not in {".kml", ".kmz"}:
        raise ValueError("Boundary candidate conversion accepts only .kml or .kmz files")
    if not source_path.is_file():
        raise ValueError(f"Boundary file does not exist: {source_path}")

    before_hash = _hash_file(str(source_path))
    assert before_hash is not None
    conversion_root = root / "intake" / "boundary_candidates"
    if conversion_root.exists():
        report_path = root / "qa_qc" / "boundary_candidate_conversion.json"
        if report_path.is_file():
            previous = json.loads(report_path.read_text(encoding="utf-8"))
            previous_hash = previous.get("source_sha256")
            previous_candidates = tuple(previous.get("polygon_candidates", ()))
            if (
                previous.get("source") == str(source_path)
                and previous_hash == before_hash
                and previous_candidates
                and all(arcpy_adapter.Exists(candidate) for candidate in previous_candidates)
            ):
                return BoundaryCandidateResult(
                    source=previous["source"],
                    source_sha256=previous_hash,
                    converted_at=previous["converted_at"],
                    output_geodatabase=previous["output_geodatabase"],
                    polygon_candidates=previous_candidates,
                    status=previous["status"],
                    review_notes=previous["review_notes"],
                )
        raise FileExistsError(
            "Boundary candidates already exist but do not match this source and will not be overwritten: "
            f"{conversion_root}"
        )
    conversion_root.mkdir(parents=True)
    output_name = "boundary_candidates"
    arcpy_adapter.conversion.KMLToLayer(
        str(source_path), str(conversion_root), output_name, "NO_GROUNDOVERLAY"
    )
    output_gdb = conversion_root / f"{output_name}.gdb"
    if not arcpy_adapter.Exists(str(output_gdb)):
        raise RuntimeError(f"KML/KMZ conversion did not create the expected geodatabase: {output_gdb}")

    candidates: list[str] = []
    for relative in ("Placemarks/Polygons", "Polygons"):
        candidate = str(output_gdb / relative)
        if arcpy_adapter.Exists(candidate):
            candidates.append(candidate)
    if not candidates:
        raise ValueError("The KML/KMZ conversion produced no polygon boundary candidates")
    if _hash_file(str(source_path)) != before_hash:
        raise RuntimeError("Source integrity failure: the KML/KMZ hash changed during conversion")

    result = BoundaryCandidateResult(
        source=str(source_path),
        source_sha256=before_hash,
        converted_at=datetime.now(timezone.utc).isoformat(),
        output_geodatabase=str(output_gdb),
        polygon_candidates=tuple(candidates),
        status="REVIEW",
        review_notes=(
            "REVIEW REQUIRED: select only the actual project-boundary polygon(s). "
            "Do not treat rights-of-way, corridors, or other KML/KMZ polygons as the site boundary."
        ),
    )
    report_path = root / "qa_qc" / "boundary_candidate_conversion.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def import_kml_boundary(
    source: Path,
    project_root: Path,
    arcpy_adapter: ArcPyBoundaryAdapter,
    boundary_name_contains: str,
    target_spatial_reference: Any | None = None,
    available_polygon_names: list[str] | None = None,
) -> tuple[BoundaryCandidateResult, BoundaryValidationResult]:
    """Convert, select, validate, and import a named boundary from KML/KMZ.

    The name fragment is mandatory because a KMZ may also contain rights-of-way
    and corridors. The selection is case-insensitive and must match at least one
    polygon. All matching parts are retained as one project-boundary layer.
    """
    name_fragment = boundary_name_contains.strip()
    if not name_fragment:
        raise ValueError(
            "Boundary Name Contains is required for KML/KMZ so the tool does not guess "
            "between the project boundary, rights-of-way, and other polygons"
        )
    candidate_result = prepare_kml_boundary_candidates(source, project_root, arcpy_adapter)
    polygon_source = candidate_result.polygon_candidates[0]
    escaped = name_fragment.replace("'", "''")
    where_clause = f"UPPER(Name) LIKE '%{escaped.upper()}%'"
    selected_layer = "site_hydrology_selected_boundary"
    arcpy_adapter.management.MakeFeatureLayer(polygon_source, selected_layer, where_clause)
    selected_count = _result_count(arcpy_adapter.management.GetCount(selected_layer))
    if selected_count < 1:
        available_text = ", ".join(available_polygon_names or []) or "none found"
        raise ValueError(
            f"No KML/KMZ polygon name contains {name_fragment!r}. "
            f"Available polygon names: {available_text}"
        )
    validation = import_and_validate_boundary(
        selected_layer, project_root, arcpy_adapter, target_spatial_reference
    )
    return candidate_result, validation


def import_and_validate_boundary(
    source: str,
    project_root: Path,
    arcpy_adapter: ArcPyBoundaryAdapter,
    target_spatial_reference: Any | None = None,
) -> BoundaryValidationResult:
    """Validate a polygon boundary and copy/project it into the working geodatabase.

    The source is never repaired or changed. Geometry errors stop the import.
    """
    root, geodatabase = _load_workspace(project_root)
    if not arcpy_adapter.Exists(source):
        raise ValueError(f"Boundary does not exist or is not accessible: {source}")

    description = arcpy_adapter.Describe(source)
    geometry_type = str(description.shapeType)
    if geometry_type.lower() != "polygon":
        raise ValueError(f"Boundary must be polygon geometry; received {geometry_type}")
    spatial_reference = description.spatialReference
    sr_name = str(getattr(spatial_reference, "name", "Unknown"))
    sr_type = str(getattr(spatial_reference, "type", "Unknown"))
    if sr_name in {"", "Unknown"} or sr_type == "Unknown":
        raise ValueError("Boundary spatial reference is unknown; assign it before processing")

    feature_count = _result_count(arcpy_adapter.management.GetCount(source))
    if feature_count < 1:
        raise ValueError("Boundary contains no polygon features")

    geometry_table = str(geodatabase / "boundary_geometry_check")
    if arcpy_adapter.Exists(geometry_table):
        raise FileExistsError(f"Boundary QA table already exists: {geometry_table}")
    arcpy_adapter.management.CheckGeometry(source, geometry_table)
    geometry_error_count = _result_count(arcpy_adapter.management.GetCount(geometry_table))
    if geometry_error_count:
        raise ValueError(
            f"Boundary has {geometry_error_count} geometry error(s); source was not repaired or imported"
        )

    output = str(geodatabase / "project_boundary")
    if arcpy_adapter.Exists(output):
        raise FileExistsError(f"Imported boundary already exists and will not be overwritten: {output}")
    if target_spatial_reference is None:
        arcpy_adapter.management.CopyFeatures(source, output)
        output_sr_name = sr_name
    else:
        arcpy_adapter.management.Project(source, output, target_spatial_reference)
        output_sr_name = str(getattr(target_spatial_reference, "name", target_spatial_reference))

    extent = description.extent
    result = BoundaryValidationResult(
        source=source,
        imported_boundary=output,
        validated_at=datetime.now(timezone.utc).isoformat(),
        feature_count=feature_count,
        geometry_type=geometry_type,
        source_spatial_reference=sr_name,
        source_wkid=getattr(spatial_reference, "factoryCode", None) or None,
        output_spatial_reference=output_sr_name,
        extent={
            "xmin": float(extent.XMin), "ymin": float(extent.YMin),
            "xmax": float(extent.XMax), "ymax": float(extent.YMax),
        },
        source_sha256=_hash_file(source),
        geometry_error_count=geometry_error_count,
        status="PASS",
        review_notes=(
            "Geometry, feature count, and declared spatial reference passed intake checks. "
            "CRS suitability, datum transformation, analysis extent, and engineering use are REVIEW REQUIRED."
        ),
    )
    report_path = root / "qa_qc" / "boundary_validation.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
