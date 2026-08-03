"""Create a single QA/QC index for a site workflow run."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def generate_qa_package(project_root: Path) -> tuple[Path, Path]:
    root = project_root.expanduser().resolve()
    qa_root = root / "qa_qc"
    if not qa_root.is_dir(): raise ValueError(f"QA/QC folder is missing: {qa_root}")
    records = []
    for path in sorted(qa_root.glob("*.json")):
        if path.name == "qa_qc_package.json": continue
        raw = path.read_bytes()
        status = "RECORDED"
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict): status = str(payload.get("status", status))
            elif isinstance(payload, list) and any(item.get("status") == "FAIL" for item in payload if isinstance(item, dict)):
                status = "FAIL"
        except json.JSONDecodeError: status = "FAIL"
        records.append({"report": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "status": status})
    overall = "FAIL" if any(record["status"] == "FAIL" for record in records) else "REVIEW"
    json_path, csv_path = qa_root / "qa_qc_package.json", qa_root / "qa_qc_index.csv"
    json_path.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall, "engineering_notice": "REVIEW REQUIRED: preliminary screening only.",
        "reports": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["report", "sha256", "status"]); writer.writeheader(); writer.writerows(records)
    return json_path, csv_path
