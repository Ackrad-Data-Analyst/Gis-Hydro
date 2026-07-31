"""Read-only file discovery, metadata collection, and integrity hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .file_classifier import FileClassifier
from .kmz_inspector import inspect_kmz
from .models import InventoryRecord


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_files(source: Path) -> list[Path]:
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Project folder is not an existing directory: {source}")
    return sorted((item for item in source.rglob("*") if item.is_file()), key=lambda item: str(item).lower())


def inventory_files(source: Path, classifier: FileClassifier, run_at: str | None = None) -> tuple[list[InventoryRecord], dict[str, str]]:
    timestamp = run_at or datetime.now(timezone.utc).isoformat()
    records: list[InventoryRecord] = []
    initial_hashes: dict[str, str] = {}
    for path in discover_files(source):
        relative = path.relative_to(source)
        role = "original" if "original" in (part.lower() for part in path.parts) else "working/unknown"
        try:
            digest = hash_file(path)
            initial_hashes[str(relative)] = digest
            readable = True
            stat = path.stat()
            classification = classifier.classify(path)
            kmz = inspect_kmz(path) if path.suffix.lower() == ".kmz" else None
            status = classification.status
            notes = classification.notes
            if kmz is not None and not kmz["valid_kmz"]:
                status = "REVIEW"
                notes += f" Invalid KMZ: {kmz['error']}"
        except (OSError, PermissionError) as exc:
            digest, readable, stat, kmz = "", False, None, None
            classification = classifier.classify(path)
            status, notes = "FAIL", f"File is unreadable: {exc}"
        records.append(InventoryRecord(
            path.name, str(path.resolve()), relative.as_posix(), path.suffix.lower(),
            stat.st_size if stat else 0,
            datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if stat else "",
            classification.category, classification.confidence, "Unknown - REVIEW REQUIRED",
            status, notes, readable, role, digest, timestamp,
            json.dumps(kmz, sort_keys=True) if kmz is not None else "",
        ))
    return records, initial_hashes


def verify_integrity(source: Path, initial: dict[str, str]) -> dict[str, object]:
    current_paths = {str(path.relative_to(source)): path for path in discover_files(source)}
    changed, missing, unreadable = [], [], []
    for relative, before_hash in initial.items():
        path = current_paths.get(relative)
        if path is None:
            missing.append(relative)
            continue
        try:
            if hash_file(path) != before_hash:
                changed.append(relative)
        except OSError:
            unreadable.append(relative)
    added = sorted(set(current_paths) - set(initial))
    return {"source_changes_expected": 0, "changed_files": changed, "missing_files": missing,
            "added_files": added, "unreadable_files": unreadable,
            "integrity_confirmed": not any((changed, missing, added, unreadable))}
