"""Command-line entry point for the Module 1 inventory workflow."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .data_gap_checker import check_data_gaps, load_required_inputs
from .file_classifier import FileClassifier
from .file_inventory import inventory_files, verify_integrity
from .logging_config import configure_logging
from .models import GapRecord, InventoryRecord
from .project_setup import validate_paths
from .reporting import write_csv, write_json, write_xlsx_if_available
from .source_register import SOURCE_COLUMNS, build_source_register


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cygnus read-only project intake prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory", help="inventory a project folder")
    inventory.add_argument("--project-folder", required=True, type=Path)
    inventory.add_argument("--project-name", required=True)
    inventory.add_argument("--config", type=Path, default=Path("config"))
    inventory.add_argument("--output-folder", type=Path)
    inventory.add_argument("--dry-run", action="store_true")
    inventory.add_argument("--verbose", action="store_true")
    return parser


def run_inventory(args: argparse.Namespace) -> dict[str, object]:
    requested_output = args.output_folder or args.project_folder.parent / f"{args.project_name}_inventory_outputs"
    source, output = validate_paths(args.project_folder, requested_output)
    config = args.config.expanduser().resolve()
    classifier = FileClassifier.from_file(config / "file_classification.yaml")
    categories = load_required_inputs(config / "required_inputs.yaml")
    logger = configure_logging(output, args.verbose, args.dry_run)
    logger.info("Starting read-only inventory for %s at %s", args.project_name, source)
    records, initial_hashes = inventory_files(source, classifier)
    gaps = check_data_gaps(records, categories)
    sources = build_source_register(records)
    integrity = verify_integrity(source, initial_hashes)
    summary: dict[str, object] = {
        "project_name": args.project_name, "project_folder": str(source),
        "inventory_run_at": datetime.now(timezone.utc).isoformat(), "dry_run": args.dry_run,
        "file_count": len(records), "pass_file_count": sum(r.file_status == "PASS" for r in records),
        "review_file_count": sum(r.file_status == "REVIEW" for r in records),
        "fail_file_count": sum(r.file_status == "FAIL" for r in records),
        "missing_required_count": sum(g.status == "FAIL" for g in gaps),
        "integrity_confirmed": integrity["integrity_confirmed"],
        "engineering_notice": "REVIEW REQUIRED: draft intake screening only; not final engineering approval.",
    }
    if args.dry_run:
        logger.info("Dry run complete: %d files; no output files or folders written", len(records))
        return summary
    inventory_rows = [record.to_dict() for record in records]
    gap_rows = [gap.to_dict() for gap in gaps]
    inventory_columns = list(InventoryRecord.__dataclass_fields__)
    gap_columns = list(GapRecord.__dataclass_fields__)
    write_csv(output / "file_inventory.csv", inventory_rows, inventory_columns)
    write_csv(output / "source_register.csv", sources, SOURCE_COLUMNS)
    write_csv(output / "data_gap_report.csv", gap_rows, gap_columns)
    excel_created = [
        write_xlsx_if_available(output / "file_inventory.xlsx", inventory_rows, inventory_columns),
        write_xlsx_if_available(output / "source_register.xlsx", sources, SOURCE_COLUMNS),
        write_xlsx_if_available(output / "data_gap_report.xlsx", gap_rows, gap_columns),
    ]
    summary["excel_support_available"] = all(excel_created)
    summary["excel_note"] = "Excel reports created." if all(excel_created) else "Excel reports skipped because openpyxl is not installed; CSV reports are complete."
    write_json(output / "project_summary.json", summary)
    write_json(output / "source_integrity_report.json", integrity)
    logger.info("Completed inventory: %d files; source integrity confirmed=%s", len(records), integrity["integrity_confirmed"])
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_inventory(args)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"Inventory complete: {summary['file_count']} files; integrity confirmed: {summary['integrity_confirmed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
