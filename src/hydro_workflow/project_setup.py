"""Validate that output writes cannot affect the scanned source tree."""

from __future__ import annotations

from pathlib import Path


def validate_paths(source: Path, output: Path) -> tuple[Path, Path]:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Project folder is not an existing directory: {source}")
    if output == source or source in output.parents:
        raise ValueError("Output folder must be outside the project source folder to protect original data.")
    return source, output
