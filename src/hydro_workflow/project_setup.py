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


def validate_file_output(source_file: Path, output: Path) -> tuple[Path, Path]:
    """Validate an output directory for an operation that reads one source file."""
    source_file = source_file.expanduser().resolve()
    output = output.expanduser().resolve()
    if not source_file.is_file():
        raise ValueError(f"Source is not an existing file: {source_file}")
    if output == source_file:
        raise ValueError("Output folder cannot overwrite the source file.")
    return source_file, output
