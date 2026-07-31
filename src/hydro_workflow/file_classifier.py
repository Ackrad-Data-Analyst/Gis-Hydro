"""Conservative, configuration-driven filename classification."""

from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
from typing import Any

from .models import Classification


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load JSON-compatible YAML without introducing a YAML dependency."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load configuration {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Configuration must contain an object: {path}")
    return value


def suffix_for_name(name: str) -> str:
    """Return a lowercase suffix for native or Windows-style path text."""
    return PureWindowsPath(name).suffix.lower()


class FileClassifier:
    def __init__(self, config: dict[str, Any]) -> None:
        self.rules = config.get("rules", [])
        self.supported = set(config.get("supported_extensions", []))
        self.threshold = float(config.get("confidence_threshold", 0.8))

    @classmethod
    def from_file(cls, path: Path) -> "FileClassifier":
        return cls(load_json_yaml(path))

    def classify(self, path: Path) -> Classification:
        name = path.stem.lower().replace("_", " ").replace("-", " ")
        extension = suffix_for_name(path.name)
        matches: list[tuple[int, str]] = []
        for rule in self.rules:
            keyword_hits = sum(str(word).lower() in name for word in rule.get("keywords", []))
            extension_match = extension in rule.get("extensions", [])
            if keyword_hits and extension_match:
                matches.append((keyword_hits, str(rule["category"])))
        if matches:
            matches.sort(reverse=True)
            top_hits, category = matches[0]
            tied = [item for item in matches if item[0] == top_hits]
            if len(tied) > 1:
                return Classification(category, 0.6, "REVIEW", "Multiple category rules matched; REVIEW REQUIRED.")
            return Classification(category, 0.95, "PASS", "Filename and extension match a draft rule; engineering suitability remains REVIEW REQUIRED.")
        if extension in self.supported:
            return Classification("Unclassified", 0.2, "REVIEW", "Known format but category is uncertain; REVIEW REQUIRED.")
        return Classification("Unknown", 0.0, "REVIEW", "Unknown file extension and purpose; REVIEW REQUIRED.")
