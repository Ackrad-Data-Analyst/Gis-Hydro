# Site-Agnostic Preliminary Hydrology Workflow Automation

The application accepts a project name and boundary for **any site**; no site name is
hard-coded. Cygnus is the first pilot only. Module 1 provides **project intake, read-only file inventory, source
registration, and data-gap screening**. It does not perform engineering analysis or
produce approved hydrology conclusions. Every configured rule is a draft requiring
Civil Engineering review.

## Download and run the ArcGIS tool

There is no installer and no Python package setup is required for the ArcGIS toolbox.
Download the complete repository ZIP rather than saving the `.pyt` file by itself:

1. On the GitHub repository page, select **Code > Download ZIP**. If you are reviewing a
   pull request, select the PR's **Code** tab first so the ZIP contains that version.
2. In Windows File Explorer, right-click the downloaded ZIP, select **Extract All**, and
   move the extracted `Gis-Hydro` folder to a permanent location such as
   `C:\Users\<you>\Documents\Gis-Hydro`.
3. Do **not** run anything while browsing inside the ZIP. Open the extracted folder and
   double-click `tools\Open Site Hydrology Toolbox.cmd`.
4. In ArcGIS Pro, open or create a **Map** project. If the toolbox is not already visible,
   use **View > Catalog Pane**, right-click **Folders**, select **Add Folder Connection**,
   and choose the extracted `Gis-Hydro` folder.
5. Expand `toolboxes\site_hydrology_workflow.pyt` and run **Preflight Environment Check**.
   Choose an output folder outside the downloaded code folder.
6. Confirm the preflight report shows `terrain_hydrology=AVAILABLE`. ArcGIS Pro Advanced
   does not by itself include Spatial Analyst; that extension must also be assigned.
7. Open **00 - START HERE > Automated Site Workflow - KMZ to Review Package**. Select a
   project name, a parent projects folder, the KML/KMZ boundary and polygon, an approved
   CRS, units, data-source mode, and reviewed terrain parameters. Then run it once.
8. Review the new project's `qa_qc` reports and `hec_ras_inputs` review package. The output
   is preliminary and is not final engineering approval or a runnable HEC-RAS model.

If the launcher cannot find ArcGIS Pro, start ArcGIS Pro normally and follow step 4. If
the toolbox shows a red exclamation mark, right-click it, select **Refresh Python Toolbox
Access Permission**, and then **Refresh**. For screenshots and field-by-field guidance,
see [`docs/manager_quick_start.md`](docs/manager_quick_start.md) and
[`docs/user_guide.md`](docs/user_guide.md).

## Safety first

- Use synthetic data for tests. Do not place company data in this repository.
- Source files are opened only for reading and are hashed before and after a run.
- Outputs must be outside the folder being inventoried.
- The command-line inventory is read-only and performs no network activity. The ArcGIS
  toolbox can acquire configured authoritative services and create preliminary terrain
  and HEC-RAS review inputs; it does not run HEC-RAS or approve engineering results.

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

For a colleague who does not use GitHub, Git, or PowerShell, send a clean ZIP through the
team's approved OneNote/Teams/SharePoint location and start with
[`docs/manager_quick_start.md`](docs/manager_quick_start.md). The repository includes a
double-click Windows launcher at `tools/Open Site Hydrology Toolbox.cmd`; it opens the
correct toolbox folder and starts ArcGIS Pro without installing Python packages.

## Current scope

The ArcGIS toolbox now connects workspace creation, boundary validation, catalog-driven
acquisition, data standardization, Spatial Analyst terrain/drainage processing, crossing
screening, preliminary HEC-RAS review-package export, and QA/QC reporting. It also exposes
**Run Complete Preliminary Site Workflow**. Live services and native ArcGIS behavior must
still be validated on the approved workstation. The package does not run HEC-RAS or make
final engineering decisions. CRS, datum transformations, thresholds, structure data,
model geometry, and engineering suitability remain **REVIEW REQUIRED**.
