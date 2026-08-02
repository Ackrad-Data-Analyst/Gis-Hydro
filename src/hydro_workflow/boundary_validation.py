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

    class management(Protocol):
        @staticmethod
        def GetCount(value: str): ...
        @staticmethod
        def CheckGeometry(value: str, output_table: str): ...
        @staticmethod
        def CopyFeatures(value: str, output: str): ...
        @staticmethod
        def Project(value: str, output: str, spatial_reference: Any): ...


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
