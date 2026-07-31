# Cygnus Preliminary Hydrology Workflow Automation Prototype

Module 1 is a proof of concept for **project intake, read-only file inventory, source
registration, and data-gap screening**. It does not perform engineering analysis or
produce approved hydrology conclusions. Every configured rule is a draft requiring
Civil Engineering review.

## Safety first

- Use synthetic data for tests. Do not place company data in this repository.
- Source files are opened only for reading and are hashed before and after a run.
- Outputs must be outside the folder being inventoried.
- The application has no network, cloud, ArcPy, terrain, or HEC-RAS automation.

## Requirements and installation

Python 3.10 or newer is the only required dependency. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
```

No third-party package is required for CSV/JSON reports. If `openpyxl` is already
installed, matching `.xlsx` workbooks are also written; otherwise the log and summary
clearly record that Excel export was skipped. No package is installed automatically.

## Run

```bash
python -m hydro_workflow.cli inventory \
  --project-folder "C:\Cygnus_Hydrology_Prototype\data\original" \
  --project-name "Cygnus" \
  --config config \
  --output-folder "C:\Cygnus_Hydrology_Prototype\outputs" \
  --verbose
```

Preview without creating an output folder or reports:

```bash
python -m hydro_workflow.cli inventory --project-folder sample_data/synthetic_only \
  --project-name Synthetic --config config --output-folder /tmp/cygnus-preview --dry-run
```

For a source checkout without installation, prefix commands with `PYTHONPATH=src`
(on Windows PowerShell: `$env:PYTHONPATH = "src"`). Run tests with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Outputs

Normal runs produce `file_inventory.csv`, `source_register.csv`,
`data_gap_report.csv`, `project_summary.json`, `source_integrity_report.json`, and
`inventory_run.log`. Excel counterparts are optional as described above. See
[`docs/user_guide.md`](docs/user_guide.md) for interpretation and limitations.

## Current scope

Only Module 1 is implemented. Filename-based classification is intentionally
conservative; CRS, units, datum, coverage, engineering suitability, and the provenance
of unknown sources remain **REVIEW REQUIRED**.
