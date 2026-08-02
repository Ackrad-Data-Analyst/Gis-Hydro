# Site-Agnostic Preliminary Hydrology Workflow Automation

The application accepts a project name and boundary for **any site**; no site name is
hard-coded. Cygnus is the first pilot only. Module 1 provides **project intake, read-only file inventory, source
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
  --project-folder "C:\Site_Hydrology\Example_Site\data\original" \
  --project-name "Example Site" \
  --config config \
  --output-folder "C:\Site_Hydrology\Example_Site\outputs" \
  --verbose
```

Preview without creating an output folder or reports:

```bash
python -m hydro_workflow.cli inventory --project-folder sample_data/synthetic_only \
  --project-name Synthetic --config config --output-folder /tmp/site-hydro-preview --dry-run
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

## Authoritative data acquisition planning

The manager-provided authoritative source catalog is stored in
`config/authoritative_sources.yaml`. Build a site-specific, reviewable plan from any KMZ
boundary with:

```bash
python -m hydro_workflow.cli plan-acquisition \
  --boundary "C:\Projects\Example Site\boundary.kmz" \
  --project-name "Example Site" --config config \
  --output-folder "C:\Projects\Example Site\acquisition_plan"
```

This increment validates the catalog and writes CSV/JSON plus optional Excel plans. It
does not yet download or process remote GIS layers. Source-specific download adapters,
coverage checks, immutable download manifests, and GIS processing are the next module.

## ArcGIS Pro toolbox

`toolboxes/site_hydrology_workflow.pyt` is one toolbox for every ArcGIS Pro license
level. Its **Preflight Environment Check** detects Basic, Standard, or Advanced plus
Spatial Analyst, 3D Analyst, and Image Analyst availability. It writes an explicit
capability matrix; unsupported operations fail closed rather than being silently skipped.

In ArcGIS Pro, add a folder connection to the repository, expand `toolboxes`, open
`Site Hydrology Workflow`, and run **Preflight Environment Check** before processing.
The first toolbox increment only reports capabilities. Acquisition and processing tools
will use this matrix as their mandatory licensing gate.

For a colleague who does not use Git or PowerShell, start with
[`docs/manager_quick_start.md`](docs/manager_quick_start.md). The repository includes a
double-click Windows launcher at `tools/Open Site Hydrology Toolbox.cmd`; it opens the
correct toolbox folder and starts ArcGIS Pro without installing Python packages.

## Current scope

Module 1 inventory and the Module 2A acquisition-planning foundation are implemented.
Remote download and GIS processing adapters are not implemented yet. Filename-based
classification is intentionally conservative; CRS, units, datum, coverage, engineering
suitability, and the provenance of unknown sources remain **REVIEW REQUIRED**.
