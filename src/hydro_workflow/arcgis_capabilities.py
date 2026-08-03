"""Evaluate ArcGIS license capabilities without importing ArcPy.

ArcPy entry points collect runtime facts and pass them into this pure-Python module so
capability decisions are testable outside ArcGIS Pro.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .file_classifier import load_json_yaml


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    available: bool
    status: str
    reason: str
    minimum_license: str
    required_extensions: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_capability_config(path: Path) -> dict[str, Any]:
    config = load_json_yaml(path)
    order = config.get("license_order")
    capabilities = config.get("capabilities")
    if order != ["Basic", "Standard", "Advanced"]:
        raise ValueError("ArcGIS license order must be Basic, Standard, Advanced")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("ArcGIS capability configuration must contain capabilities")
    names: set[str] = set()
    for row in capabilities:
        name = str(row.get("name", ""))
        if not name or name in names:
            raise ValueError(f"Empty or duplicate ArcGIS capability: {name!r}")
        names.add(name)
        if row.get("minimum_license") not in order:
            raise ValueError(f"Invalid minimum license for {name}")
        if not isinstance(row.get("extensions"), list):
            raise ValueError(f"Extensions must be a list for {name}")
    return config


def evaluate_capabilities(
    license_level: str,
    extension_statuses: dict[str, str],
    config: dict[str, Any],
) -> list[CapabilityResult]:
    """Return explicit availability and reasons for every configured operation."""
    order = list(config["license_order"])
    if license_level not in order:
        return [CapabilityResult(
            name=str(row["name"]), available=False, status="FAIL",
            reason=f"Unrecognized or unavailable ArcGIS Pro license: {license_level}",
            minimum_license=str(row["minimum_license"]),
            required_extensions=", ".join(row["extensions"]),
            description=str(row["description"]),
        ) for row in config["capabilities"]]
    current_rank = order.index(license_level)
    results: list[CapabilityResult] = []
    for row in config["capabilities"]:
        minimum = str(row["minimum_license"])
        extensions = [str(value) for value in row["extensions"]]
        missing = [name for name in extensions if extension_statuses.get(name) not in {"Available", "CheckedOut"}]
        if current_rank < order.index(minimum):
            available, status = False, "UNAVAILABLE"
            reason = f"Requires {minimum} or higher; current license is {license_level}."
        elif missing:
            available, status = False, "UNAVAILABLE"
            details = ", ".join(f"{name}={extension_statuses.get(name, 'Unknown')}" for name in missing)
            reason = f"Required extension unavailable: {details}."
        else:
            available, status = True, "AVAILABLE"
            reason = "Current license and extension availability satisfy configured requirements."
        results.append(CapabilityResult(
            name=str(row["name"]), available=available, status=status, reason=reason,
            minimum_license=minimum, required_extensions=", ".join(extensions),
            description=str(row["description"]),
        ))
    return results
