"""Screen road/drainage intersections and nearby known structures."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CrossingScreeningResult:
    roads: str
    drainage_paths: str
    bridges: str | None
    culverts: str | None
    structure_search_distance: str | None
    potential_crossings: str
    screened_crossings: str
    known_structures: str | None
    potential_crossing_count: int
    processed_at: str
    status: str
    review_notes: str

    def to_dict(self) -> dict[str, object]: return asdict(self)


def _count(result: Any) -> int:
    try: return int(result[0])
    except (TypeError, IndexError): return int(result.getOutput(0))


def screen_crossings(
    project_root: Path,
    roads: str,
    drainage_paths: str,
    arcpy_adapter: Any,
    bridges: str | None = None,
    culverts: str | None = None,
    structure_search_distance: str | None = None,
) -> CrossingScreeningResult:
    """Create possible crossing points without inventing structure attributes."""
    for label, value in (("roads", roads), ("drainage paths", drainage_paths)):
        if not arcpy_adapter.Exists(value): raise ValueError(f"Required {label} dataset is missing: {value}")
    known_inputs = [value for value in (bridges, culverts) if value]
    for value in known_inputs:
        if not arcpy_adapter.Exists(value): raise ValueError(f"Known structure dataset is missing: {value}")
    if known_inputs and not structure_search_distance:
        raise ValueError("Structure search distance is required when bridge or culvert data is supplied")

    root = project_root.expanduser().resolve()
    workspace = json.loads((root / "qa_qc" / "workspace_manifest.json").read_text(encoding="utf-8"))
    gdb = Path(workspace["geodatabase"])
    potential = str(gdb / "potential_drainage_crossings")
    known = str(gdb / "known_crossing_structures") if known_inputs else None
    screened = str(gdb / "screened_drainage_crossings")
    outputs = [potential, screened] + ([known] if known else [])
    existing = [output for output in outputs if arcpy_adapter.Exists(output)]
    if existing: raise FileExistsError(f"Crossing outputs exist and will not be overwritten: {existing}")

    arcpy_adapter.analysis.Intersect([roads, drainage_paths], potential, "ALL", None, "POINT")
    count = _count(arcpy_adapter.management.GetCount(potential))
    if known_inputs:
        if len(known_inputs) == 1: arcpy_adapter.management.CopyFeatures(known_inputs[0], known)
        else: arcpy_adapter.management.Merge(known_inputs, known)
        arcpy_adapter.analysis.SpatialJoin(
            potential, known, screened, "JOIN_ONE_TO_ONE", "KEEP_ALL", None,
            "WITHIN_A_DISTANCE", structure_search_distance,
        )
    else:
        arcpy_adapter.management.CopyFeatures(potential, screened)

    result = CrossingScreeningResult(
        roads, drainage_paths, bridges, culverts, structure_search_distance,
        potential, screened, known, count, datetime.now(timezone.utc).isoformat(), "REVIEW",
        ("REVIEW REQUIRED: intersections are candidates only. Missing structure type, dimensions, "
         "material, inverts, condition, ownership, and field verification were not invented."),
    )
    (root / "qa_qc" / "crossing_screening_report.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result
