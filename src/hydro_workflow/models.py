"""Typed records shared by Module 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    status: str
    notes: str


@dataclass(frozen=True)
class InventoryRecord:
    file_name: str
    full_path: str
    relative_path: str
    extension: str
    size_bytes: int
    modified_at: str
    likely_category: str
    classification_confidence: float
    source_type: str
    file_status: str
    review_notes: str
    is_readable: bool
    file_role: str
    sha256: str
    inventory_run_at: str
    kmz_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GapRecord:
    category: str
    required: bool
    matched_file_count: int
    status: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
