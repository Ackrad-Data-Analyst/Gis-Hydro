"""Site-agnostic reviewed-source catalog and acquisition planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .file_classifier import load_json_yaml
from .kmz_inspector import inspect_kmz

REQUIRED_FIELDS = {
    "name", "category", "source_agency", "source_type", "item_id", "rest_url",
    "authentication", "operation", "filter", "resampling",
}
ALLOWED_AUTHENTICATION = {"none", "arcgis_org"}
ALLOWED_OPERATIONS = {"extract", "spatial_query_clip", "select_intersecting_copy", "reference_only"}

# Catalog rows are intentionally not restricted to a fixed list of agencies or dataset
# names. A team can add any number of reviewed sources using the supported operations.


@dataclass(frozen=True)
class AcquisitionPlanRecord:
    project_name: str
    boundary_file: str
    source_name: str
    category: str
    source_agency: str
    source_type: str
    item_id: str
    rest_url: str
    authentication: str
    operation: str
    source_filter: str
    resampling: str
    boundary_west: float | None
    boundary_south: float | None
    boundary_east: float | None
    boundary_north: float | None
    plan_status: str
    review_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_source_catalog(path: Path) -> list[dict[str, str]]:
    """Load and strictly validate an editable reviewed-source catalog."""
    config = load_json_yaml(path)
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"Source catalog must contain a non-empty sources list: {path}")
    names: set[str] = set()
    validated: list[dict[str, str]] = []
    for index, raw in enumerate(sources, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Source catalog row {index} must be an object")
        missing = REQUIRED_FIELDS - set(raw)
        if missing:
            raise ValueError(f"Source catalog row {index} is missing: {', '.join(sorted(missing))}")
        row = {field: str(raw[field]).strip() for field in REQUIRED_FIELDS}
        if not row["name"] or row["name"] in names:
            raise ValueError(f"Source catalog has an empty or duplicate name: {row['name']!r}")
        names.add(row["name"])
        parsed = urlparse(row["rest_url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Source {row['name']} must use a valid HTTPS REST URL")
        if row["authentication"] not in ALLOWED_AUTHENTICATION:
            raise ValueError(f"Source {row['name']} has unsupported authentication: {row['authentication']}")
        if row["operation"] not in ALLOWED_OPERATIONS:
            raise ValueError(f"Source {row['name']} has unsupported operation: {row['operation']}")
        validated.append(row)
    return validated


def build_acquisition_plan(project_name: str, boundary: Path, sources: list[dict[str, str]]) -> list[AcquisitionPlanRecord]:
    """Build a reviewable source plan from a KMZ boundary without downloading data."""
    if not boundary.is_file():
        raise ValueError(f"Boundary is not an existing file: {boundary}")
    if boundary.suffix.lower() != ".kmz":
        raise ValueError("This planning increment accepts KMZ boundaries only; other boundary formats are future adapters.")
    details = inspect_kmz(boundary)
    if not details["valid_kmz"]:
        raise ValueError(f"Boundary KMZ is invalid: {details['error']}")
    bounds = details["approximate_bounds"] or {}
    records: list[AcquisitionPlanRecord] = []
    for source in sources:
        auth_note = "ArcGIS organization authentication is required. " if source["authentication"] != "none" else ""
        records.append(AcquisitionPlanRecord(
            project_name=project_name,
            boundary_file=str(boundary.resolve()),
            source_name=source["name"],
            category=source["category"],
            source_agency=source["source_agency"],
            source_type=source["source_type"],
            item_id=source["item_id"],
            rest_url=source["rest_url"],
            authentication=source["authentication"],
            operation=source["operation"],
            source_filter=source["filter"],
            resampling=source["resampling"],
            boundary_west=bounds.get("west"), boundary_south=bounds.get("south"),
            boundary_east=bounds.get("east"), boundary_north=bounds.get("north"),
            plan_status="REVIEW",
            review_notes=auth_note + "Service availability, coverage, schema, CRS, resolution, licensing, and engineering suitability require validation before download.",
        ))
    return records
