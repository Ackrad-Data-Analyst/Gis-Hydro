"""Compare inventory classifications with configured expected categories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .file_classifier import load_json_yaml
from .models import GapRecord, InventoryRecord


def load_required_inputs(path: Path) -> list[dict[str, Any]]:
    config = load_json_yaml(path)
    categories = config.get("categories")
    if not isinstance(categories, list):
        raise ValueError(f"Configuration has no categories list: {path}")
    return categories


def check_data_gaps(records: list[InventoryRecord], categories: list[dict[str, Any]]) -> list[GapRecord]:
    results: list[GapRecord] = []
    for item in categories:
        name, required = str(item["name"]), bool(item.get("required", False))
        matches = [record for record in records if record.likely_category == name]
        passing = [record for record in matches if record.file_status == "PASS"]
        if passing:
            status = "PASS"
            notes = "Readable file confidently matches a draft category rule; engineering validation is REVIEW REQUIRED."
        elif matches:
            status = "REVIEW"
            notes = "Candidate files exist but are uncertain or unreadable; REVIEW REQUIRED."
        elif required:
            status = "FAIL"
            notes = "Required critical category is missing under draft rules; REVIEW REQUIRED."
        else:
            status = "REVIEW"
            notes = "Optional category is missing; project is not failed."
        results.append(GapRecord(name, required, len(matches), status, notes))
    return results
