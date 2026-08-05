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
    readiness_report: str
    created_at: str
    status: str
    ras_readiness: str
    review_notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _readiness_report(
    *,
    package: Path,
    terrain_output: Path,
    projection_file: Path,
    copied_layers: dict[str, str],
    missing_optional_inputs: list[str],
    qa_files: dict[str, str],
) -> dict[str, object]:
    """Describe HEC-RAS readiness honestly without inventing design inputs."""
    required_for_runnable_model = {
        "verified_project_boundary": "Approved project boundary and CRS reviewed by Civil Engineering.",
        "approved_terrain": "DEM/terrain source, vertical datum, units, resolution, voids, and clipping reviewed.",
        "bank_lines": "Left and right bank lines for each modeled reach.",
        "flow_paths": "Reviewed channel/left/right overbank flow paths.",
        "cross_sections": "Reviewed cross-section cut lines and stationing.",
        "hydraulic_structures": "Bridge, culvert, road crossing, and ineffective-flow geometry reviewed.",
        "roughness_values": "Approved Manning's n zones/values; no defaults invented by the prototype.",
        "flow_boundary_conditions": "Reviewed hydrology, hydrographs, normal-depth/slope, and downstream controls.",
        "model_plan_geometry": "A HEC-RAS project, plan, geometry, unsteady/steady flow file, and computation settings.",
        "calibration_or_reasonableness": "Engineering reasonableness checks, calibration basis, and reviewer signoff.",
    }
    available_review_inputs = sorted(copied_layers)
    missing_model_inputs = [
        name for name in required_for_runnable_model
        if name not in {"verified_project_boundary"}
    ]
    return {
        "created_at": _now(),
        "status": "REVIEW",
        "ras_readiness": "NOT_RUNNABLE_HEC_RAS_MODEL",
        "package_purpose": (
            "Preliminary review package for Civil Engineering screening. It is not a HEC-RAS "
            "project and is not sufficient for final hydraulic modeling."
        ),
        "terrain_snapshot": str(terrain_output),
        "projection_file": str(projection_file),
        "available_review_inputs": available_review_inputs,
        "copied_layers": copied_layers,
        "missing_or_unavailable_review_inputs": missing_optional_inputs,
        "required_before_runnable_hec_ras": required_for_runnable_model,
        "missing_required_model_inputs": missing_model_inputs,
        "qa_report_hashes": qa_files,
        "engineering_notice": (
            "REVIEW REQUIRED: use this package to identify and organize inputs. Do not treat it as "
            "a final or runnable HEC-RAS engineering model until the listed missing inputs "
            "are supplied and approved."
        ),
    }


def build_hec_ras_review_package(
    project_root: Path,
    terrain: str,
    arcpy_adapter: Any,
    layers: dict[str, str | None],
) -> HecRasPackageResult:
    """Export supplied candidates and provenance; never create final model geometry."""
    if not arcpy_adapter.Exists(terrain):
        raise ValueError(f"Terrain is missing and no HEC-RAS review package can be built: {terrain}")
    root = project_root.expanduser().resolve()
    package = _available_package_root(root / "hec_ras_inputs" / "preliminary_review_package")
    for folder in ("terrain", "vectors", "rasters", "rainfall", "infiltration", "boundary_conditions", "qa_qc"):
        (package / folder).mkdir(parents=True, exist_ok=False)

    terrain_output = package / "terrain" / "preliminary_terrain.tif"
    arcpy_adapter.management.CopyRaster(terrain, str(terrain_output))
    if not terrain_output.exists():
        raise RuntimeError(f"Terrain snapshot was not created: {terrain_output}")
    description = arcpy_adapter.Describe(terrain)
    projection_file = package / "terrain" / "projection.prj"
    projection_file.write_text(description.spatialReference.exportToString(), encoding="utf-8")

    copied, missing = {}, []
    for name, dataset in layers.items():
        if not dataset:
            missing.append(name)
            continue
        if not arcpy_adapter.Exists(dataset):
            missing.append(name)
            continue

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
                if not raster_output.exists():
                    raise RuntimeError(f"Raster snapshot was not created: {raster_output}")
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
    readiness_path = package / "qa_qc" / "hec_ras_readiness_report.json"
    readiness_data = _readiness_report(
        package=package,
        terrain_output=terrain_output,
        projection_file=projection_file,
        copied_layers=copied,
        missing_optional_inputs=missing,
        qa_files=qa_files,
    )
    readiness_path.write_text(json.dumps(readiness_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = package / "qa_qc" / "hec_ras_input_manifest.json"
    manifest_data = {
        "terrain_source": terrain,
        "terrain_output": str(terrain_output),
        "terrain_sha256": _hash(terrain_output),
        "projection": str(projection_file),
        "layers": copied,
        "missing_optional_inputs": missing,
        "qa_report_hashes": qa_files,
        "readiness_report": str(readiness_path),
        "ras_readiness": readiness_data["ras_readiness"],
        "engineering_notice": readiness_data["engineering_notice"],
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = HecRasPackageResult(
        str(package), str(terrain_output), str(projection_file), copied, missing,
        str(manifest_path), str(readiness_path), _now(), "REVIEW",
        str(readiness_data["ras_readiness"]),
        ("REVIEW REQUIRED: this package is not a runnable HEC-RAS model. Manning's n, "
         "cross sections, banks, flow paths, structures, rainfall/inflow, boundary conditions, "
         "calibration, and model suitability were not invented."),
    )
    (root / "qa_qc" / "hec_ras_package_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
