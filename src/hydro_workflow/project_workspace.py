"""Create a safe, site-agnostic workspace and record processing provenance.

This module contains no ArcPy import so its safety rules can be tested outside ArcGIS Pro.
ArcGIS entry points pass an ArcPy adapter into :func:`create_project_workspace`.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


PROJECT_FOLDERS = (
    "intake",
    "data/original",
    "data/working",
    "gis",
    "terrain",
    "watersheds",
    "crossings",
    "rainfall",
    "hec_ras_inputs",
    "qa_qc",
    "reports",
    "logs",
)


class ArcPyWorkspaceAdapter(Protocol):
    """Small ArcPy surface used by workspace creation."""

    class management(Protocol):
        @staticmethod
        def CreateFileGDB(out_folder_path: str, out_name: str): ...


@dataclass(frozen=True)
class WorkspaceManifest:
    project_name: str
    project_id: str
    created_at: str
    project_root: str
    geodatabase: str
    overwrite_allowed: bool
    engineering_notice: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def safe_project_id(project_name: str) -> str:
    """Return a filesystem-safe identifier without changing the display name."""
    if not re.search(r"[A-Za-z0-9]", project_name):
        raise ValueError("Project name must contain at least one letter or number")
    identifier = re.sub(r"[^A-Za-z0-9_-]+", "_", project_name.strip()).strip("_")
    if not identifier:
        raise ValueError("Project name must contain at least one letter or number")
    return identifier


def create_project_workspace(
    project_name: str,
    output_root: Path,
    arcpy_adapter: ArcPyWorkspaceAdapter,
) -> WorkspaceManifest:
    """Create a new workspace without overwriting any existing project."""
    project_id = safe_project_id(project_name)
    root = output_root.expanduser().resolve()
    project_root = root / project_id
    if project_root.exists():
        raise FileExistsError(
            f"Project workspace already exists and will not be overwritten: {project_root}"
        )

    created: list[Path] = []
    try:
        project_root.mkdir(parents=True, exist_ok=False)
        created.append(project_root)
        for relative in PROJECT_FOLDERS:
            folder = project_root / relative
            folder.mkdir(parents=True, exist_ok=False)
            created.append(folder)

        geodatabase = project_root / "gis" / "site_hydrology.gdb"
        arcpy_adapter.management.CreateFileGDB(str(geodatabase.parent), geodatabase.name)
        if not geodatabase.exists():
            # Real ArcPy creates the directory. Test adapters may model it explicitly.
            raise RuntimeError(f"ArcGIS did not create the project geodatabase: {geodatabase}")

        manifest = WorkspaceManifest(
            project_name=project_name.strip(),
            project_id=project_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            project_root=str(project_root),
            geodatabase=str(geodatabase),
            overwrite_allowed=False,
            engineering_notice=(
                "REVIEW REQUIRED: this workspace stores preliminary GIS and hydrology "
                "screening outputs and does not provide final engineering approval."
            ),
        )
        manifest_path = project_root / "qa_qc" / "workspace_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
    except Exception:
        # Clean up only paths created in this failed call. Never remove a pre-existing path.
        for path in reversed(created):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        raise
