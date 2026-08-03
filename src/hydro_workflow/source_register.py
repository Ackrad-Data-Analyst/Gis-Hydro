"""Build traceable source-register rows without inventing provenance."""

from __future__ import annotations

from typing import Any

from .models import InventoryRecord


SOURCE_COLUMNS = ["file_name", "relative_path", "likely_category", "source_type", "file_role", "sha256", "review_notes"]


def build_source_register(records: list[InventoryRecord]) -> list[dict[str, Any]]:
    return [{column: record.to_dict()[column] for column in SOURCE_COLUMNS} for record in records]
