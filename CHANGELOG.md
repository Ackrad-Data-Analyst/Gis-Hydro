# Changelog

## 0.3.1 - 2026-08-03

- Added read-only KML/KMZ boundary-candidate conversion to the ArcGIS toolbox.
- Connected KML/KMZ conversion, name-based polygon selection, geometry validation,
  and boundary import into one ArcGIS tool so operators do not run a separate conversion.
- Kept project-boundary selection explicit when a source also contains rights-of-way,
  corridors, or other polygons, and added before/after source-hash protection.

## 0.2.1 - 2026-08-02

- Added a manager handoff guide with illustrated ArcGIS Pro setup steps.
- Added a double-click Windows launcher that opens the toolbox location and ArcGIS Pro
  without requiring Git, PowerShell, or Python package installation.
- Changed the manager handoff to an approved OneNote/Teams/SharePoint ZIP transfer; the
  receiving team member does not need a GitHub account.
- Simplified the ArcGIS Pro preflight dialog to input-only parameters to avoid a COM error when opening the Python toolbox in ArcGIS Pro 3.7.
- Added the first operational workflow tool: site-agnostic project workspace and file
  geodatabase creation with no-overwrite protection and a QA manifest.
- Added read-only boundary validation and import with polygon, geometry, feature-count,
  spatial-reference, source-hash, extent, and no-overwrite checks.
- Added catalog-driven vector and raster acquisition that accepts any number of valid
  source rows, preserves original extracts, creates working GIS outputs, hashes files,
  and writes per-source plus per-run provenance manifests.
- Added acquired-data validation and standardization with explicit target CRS, native
  raster metrics, feature counts, extent-overlap screening, and no-overwrite projection.
- Added Spatial Analyst-gated terrain hydrology with explicit fill, stream-threshold,
  pour-point, and snap-distance inputs plus flow, stream, drainage, watershed, and QA outputs.
- Added road/drainage crossing screening, optional known-structure proximity joins,
  a preliminary HEC-RAS review package, and consolidated QA/QC indexes.
- Added an end-to-end orchestration function that connects workspace, boundary,
  acquisition, standardization, terrain, crossings, HEC-RAS review package, and QA stages.
- Applied configured image-service filters to raster extraction layers and calculate
  extent overlap only after data and boundary share the selected project CRS.

## 0.2.0 - 2026-07-31

- Generalized product naming and CLI descriptions for any site.
- Added the manager-provided authoritative GIS source catalog.
- Added site-specific acquisition-plan generation and catalog validation.
- Added an ArcGIS Pro Python Toolbox preflight tool with capability-based licensing for
  Basic, Standard, Advanced, Spatial Analyst, 3D Analyst, and Image Analyst.

## 0.1.0 - 2026-07-29

- Established project documentation and safety constraints.
- Added configurable, read-only Module 1 inventory workflow and CLI.
- Added synthetic automated tests and reporting documentation.
