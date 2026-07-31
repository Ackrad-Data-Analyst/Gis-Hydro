"""Logging setup for console, and file output on non-dry runs."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(output: Path, verbose: bool, dry_run: bool) -> logging.Logger:
    logger = logging.getLogger("hydro_workflow")
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(output / "inventory_run.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def close_logging(logger: logging.Logger) -> None:
    """Flush and close run handlers so Windows releases the log file."""
    for handler in logger.handlers[:]:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
