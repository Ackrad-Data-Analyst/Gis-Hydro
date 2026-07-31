"""Read-only, in-memory inspection of ZIP-based KMZ files."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def inspect_kmz(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "valid_kmz": False, "kml_files": [], "folder_count": 0,
        "placemark_count": 0, "approximate_bounds": None, "error": "",
    }
    try:
        with zipfile.ZipFile(path, "r") as archive:
            kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
            result["kml_files"] = kml_names
            if not kml_names:
                result["error"] = "ZIP contains no KML file"
                return result
            coordinates: list[tuple[float, float]] = []
            for name in kml_names:
                root = ElementTree.fromstring(archive.read(name))
                result["folder_count"] += sum(element.tag.endswith("}Folder") or element.tag == "Folder" for element in root.iter())
                result["placemark_count"] += sum(element.tag.endswith("}Placemark") or element.tag == "Placemark" for element in root.iter())
                for element in root.iter():
                    if (element.tag.endswith("}coordinates") or element.tag == "coordinates") and element.text:
                        for token in re.split(r"\s+", element.text.strip()):
                            try:
                                lon, lat = token.split(",")[:2]
                                coordinates.append((float(lon), float(lat)))
                            except (ValueError, IndexError):
                                continue
            if coordinates:
                lons, lats = zip(*coordinates)
                result["approximate_bounds"] = {"west": min(lons), "south": min(lats), "east": max(lons), "north": max(lats)}
            result["valid_kmz"] = True
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        result["error"] = str(exc)
    return result
