"""Build a preliminary HEC-RAS review package without authoring engineering values."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HecRasPackageResult:
    package_root: str
    terrain: str
    projection_file: str
    copied_layers: dict[str, str]
    missing_optional_inputs: list[str]
    manifest: str
    created_at: str
    status: str
    review_notes: str
    def to_dict(self) -> dict[str, object]: return asdict(self)



def _available_package_root(base: Path) -> Path:
    """Return a new review-package folder without overwriting a previous run."""
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = base.with_name(f"{base.name}_{index}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available HEC-RAS review package folder beside: {base}")

def _hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest()


def build_hec_ras_review_package(
    project_root: Path,
    terrain: str,
    arcpy_adapter: Any,
    layers: dict[str, str | None],
) -> HecRasPackageResult:
    """Export supplied candidates and provenance; never create final model geometry."""
    if not arcpy_adapter.Exists(terrain): raise ValueError(f"Terrain is missing: {terrain}")
    root = project_root.expanduser().resolve()
    package = _available_package_root(root / "hec_ras_inputs" / "preliminary_review_package")
    for folder in ("terrain", "vectors", "rasters", "rainfall", "infiltration", "boundary_conditions", "qa_qc"):
        (package / folder).mkdir(parents=True, exist_ok=False)

    terrain_output = package / "terrain" / "preliminary_terrain.tif"
    arcpy_adapter.management.CopyRaster(terrain, str(terrain_output))
    description = arcpy_adapter.Describe(terrain)
    projection_file = package / "terrain" / "projection.prj"
    projection_file.write_text(description.spatialReference.exportToString(), encoding="utf-8")

    copied, missing = {}, []
    for name, dataset in layers.items():
        if not dataset:
            missing.append(name); continue
        if not arcpy_adapter.Exists(dataset):
            missing.append(name); continue

        vector_output = package / "vectors" / f"{name}.geojson"
        try:
            arcpy_adapter.conversion.FeaturesToJSON(
                dataset, str(vector_output), "FORMATTED", "NO_Z_VALUES", "NO_M_VALUES", "GEOJSON"
            )
            copied[name] = str(vector_output)
            continue
        except Exception as vector_error:  # ArcGIS raises ExecuteError for raster/non-feature inputs.
            raster_output = package / "rasters" / f"{name}.tif"
            try:
                arcpy_adapter.management.CopyRaster(dataset, str(raster_output))
                copied[name] = str(raster_output)
                missing.append(f"{name}_vector_export_review_required")
                continue
            except Exception as raster_error:
                missing.append(
                    f"{name}_export_failed_REVIEW_REQUIRED: "
                    f"vector export failed ({vector_error}); raster copy failed ({raster_error})"
                )


    qa_files = {}
    for report in sorted((root / "qa_qc").glob("*.json")):
        qa_files[report.name] = _hash(report)
    manifest_path = package / "qa_qc" / "hec_ras_input_manifest.json"
    manifest_data = {
        "terrain_source": terrain, "terrain_output": str(terrain_output),
        "projection": str(projection_file), "layers": copied, "missing_optional_inputs": missing,
        "qa_report_hashes": qa_files,
        "engineering_notice": "REVIEW REQUIRED: this is not a runnable or approved HEC-RAS model.",
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = HecRasPackageResult(
        str(package), str(terrain_output), str(projection_file), copied, missing,
        str(manifest_path), datetime.now(timezone.utc).isoformat(), "REVIEW",
        ("REVIEW REQUIRED: Manning's n, cross sections, banks, flow paths, structures, rainfall, "
         "infiltration, boundary conditions, calibration, and model suitability were not invented."),
    )
    (root / "qa_qc" / "hec_ras_package_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
