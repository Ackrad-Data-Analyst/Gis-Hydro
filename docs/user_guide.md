# ArcGIS Pro operator guide

## Required workstation capabilities

- ArcGIS Pro Basic or higher: workspace, boundary, downloads, standardization, crossings,
  HEC-RAS review-package export, and QA reporting.
- Spatial Analyst: terrain filling, flow direction, flow accumulation, stream candidates,
  pour-point snapping, and watershed candidates.
- Internet and portal access required by the selected catalog rows.

An Advanced product license does not by itself prove that Spatial Analyst is assigned.
Run **00 - Environment and QA > Preflight Environment Check** and confirm
`terrain_hydrology=AVAILABLE` before terrain processing.

## Installation

1. Close ArcGIS Pro before replacing an existing toolbox version.
2. Extract the release ZIP to a permanent folder outside all project workspaces.
3. Double-click `tools\Open Site Hydrology Toolbox.cmd`, or connect the extracted folder
   from **View > Catalog Pane > Folders > Add Folder Connection**.
4. Expand `toolboxes\site_hydrology_workflow.pyt`.
5. Store site work under a separate root such as `C:\Site_Hydrology\Projects`.

On Windows, double-click `tools\Build Manager Package.cmd`. It uses the Python environment
included with ArcGIS Pro, stops if packaging fails, verifies the expected ZIP, and opens
the completed package folder. A separate Microsoft Store Python installation is not needed.

Release maintainers can alternatively build a personalized manager PDF and clean ZIP
without adding dependencies:

`python tools\build_manager_release.py --manager "Manager Name" --author "Author Name"`

## Complete preliminary workflow

For a normal new site, run **00 - START HERE > Automated Site Workflow - KMZ to Review
Package**. In one dialog, choose the project name, parent projects folder, KML/KMZ,
boundary polygon name, approved CRS, Imperial/Metric units, reviewed stream threshold,
fill choice, and data mode. **Existing Map Layers** is the preferred manager-demo mode:
it snapshots the DEM/roads and optional land-cover/soil layers from the current ArcGIS
map. If exactly one current-map layer name looks like DEM/3DEP/Elevation, Roads/Streets,
NLCD/LandCover, or Soils/HSG, the toolbox fills that layer automatically; ambiguous
matches stay blank for operator review. **Authoritative Catalog** remains available for
controlled service testing but should not be the only path for a manager demonstration.
The automated tool creates the project file geodatabase and all implemented downstream
review outputs.

Existing map image services are selected by layer name and clipped to the project boundary
before they are copied. If ArcGIS would exceed an image-service row/column limit such as
`001491`, the workflow temporarily increases only the snapshot cell size enough to keep
the service request under the limit and records that coarser preview resolution as
**REVIEW REQUIRED**. Do not treat this as final DEM or land-cover engineering accuracy.

If an optional catalog service such as land cover or roads is unavailable, the automated
run preserves completed terrain and QA outputs, records the skipped stage as **REVIEW
REQUIRED**, and tells the operator to rerun with an approved existing map layer. A DEM is
critical for terrain processing; a failed DEM stops safely with the service error and the
location of its acquisition record.

The individual tools below remain available for troubleshooting or controlled reruns.
Do not rerun a completed stage over existing outputs.

1. **00 - Preflight:** record product and extension availability.
2. **01 - Create Project Workspace:** provide a project name and projects root.
3. **01 - Import and Validate KML/KMZ Boundary:** select the source, workspace, and exact
   polygon candidate. Visually compare the imported polygon with the approved site exhibit.
4. **02 - Download Authoritative Data:** leave Source Names blank to run the catalog. The
   catalog includes federal DEM, roads, watershed, land-cover and flood sources plus USDA
   soil sources. Completed immutable downloads are reused; failures receive separate retry
   records.
5. **03 - Validate, Standardize, and Clip:** select the engineer/GIS-approved project CRS.
6. **04 - Prepare Terrain, Drainage, and Watershed Candidates:** select the standardized
   DEM and enter reviewed terrain parameters. A requested 1 m DEM must be confirmed from
   the acquisition and standardization reports; do not treat resampled coarse data as new
   1 m accuracy.
7. **05 - Screen Roads, Bridges, Culverts, and Drainage Crossings:** use standardized
   `USGS_TNM_Roads`, or replace it with a more authoritative state/local DOT layer when
   available. Bridge/culvert inputs and search distance are optional and REVIEW REQUIRED.
8. **06 - Prepare Preliminary HEC-RAS Review Package:** export terrain and available vector
   candidates. Missing banks, cross sections, structures, rainfall, infiltration, or
   boundary conditions remain explicitly listed; they are not invented.
   The package writes `qa_qc/hec_ras_readiness_report.json`; it must read
   `NOT_RUNNABLE_HEC_RAS_MODEL` until Civil Engineering supplies and approves the missing
   HEC-RAS geometry, roughness, hydrology, boundary-condition, structure, calibration, and
   reviewer-signoff inputs. Treat this report as a gate, not as a hidden failure.
9. **07 - Generate QA/QC Package:** retain the JSON and CSV index with the project.

## Engineer/GIS inputs that remain explicit

- approved projected CRS and any datum transformation;
- whether DEM depressions should be filled;
- stream threshold in contributing cells;
- pour points and snap distance when watersheds are requested;
- structure search distance when known bridges/culverts are supplied;
- final HEC-RAS geometry and hydraulic/hydrologic parameters.

## Acceptance and troubleshooting

- `REVIEW` is an expected preliminary status, not engineering approval.
- On a red acquisition result, do not delete successful source folders. Install the latest
  toolbox release and rerun; safe retry folders preserve earlier attempts.
- Confirm every required acquisition and standardized dataset in `qa_qc` before terrain.
- Confirm the DEM report shows actual source cell size and site coverage. A 1 m request is
  conditional on authoritative 1 m coverage at the site.
- Preserve the original boundary and downloaded agency files; work only from generated
  working copies.
