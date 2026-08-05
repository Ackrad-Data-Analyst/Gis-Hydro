# Changelog

## 0.3.5

- Replaced the misleading toolbox-not-found message with direct **Extract All** instructions
  when Windows launches the command file from inside a ZIP preview.
- Added a regression check and operator guidance for distinguishing a compressed ZIP view
  from the extracted release folder.
- Prevented optional NLCD or road-service outages from discarding an otherwise valid
  terrain run; unavailable crossing inputs are now recorded as REVIEW REQUIRED.
- Added actionable DEM failure messages and regression coverage for partial catalog outages.
- Avoided ArcGIS image-service error 001491 in Existing Map Layers mode by using map-layer
  name selectors and clipping remote rasters to the project boundary before CopyRaster.
- Added adaptive REVIEW REQUIRED raster snapshot cell-size control for broad boundaries
  that still exceed image-service row/column limits after clipping.
- Recorded existing-map optional layer snapshot failures as acquisition FAIL records instead
  of crashing the entire workflow before DEM results and QA can be reviewed.
- Made Existing Map Layers the default one-dialog data mode and added conservative current-map
  layer auto-detection for unique DEM, roads, land-cover, and soil/HSG layer names.
- Fixed HEC-RAS review packaging so raster review inputs, including combined hydrologic
  response units, are copied as raster snapshots instead of being forced through GeoJSON
  feature export. Raster/vector export fallbacks are recorded as REVIEW REQUIRED instead
  of crashing the manager demonstration.

## 0.3.4 - 2026-08-04

- Fixed the automated toolbox workflow failing with an unexpected
  `boundary_polygon_name` argument when ArcGIS Pro retained an older in-memory copy of the
  workflow module from a previously opened release.
- The toolbox now prioritizes its own extracted `src` directory, reloads the complete-workflow
  orchestrator immediately before execution, and reports a clear restart instruction if
  ArcGIS resolves the module from another extracted release.

## Manager UX consolidation

- Added a KMZ-first automated workflow as the first toolbox entry, reducing the normal run
  to one dialog while retaining advanced troubleshooting tools.
- Clarified parent-folder/geodatabase behavior and returned the created geodatabase.
- Replaced ambiguous boundary-name wording with a KMZ polygon dropdown and hid the redundant
  generic boundary importer.
- Added Imperial/Metric workflow preferences and transparent boundary-outline map display.
- Added conservative dual/mixed soil-group normalization and an approval-gated engineering
  lookup template rather than embedding unreviewed CN, roughness, or infiltration values.

## 0.3.3 - 2026-08-03

- Added a configurable federal USGS National Map road-centerline source for nationwide
  fallback crossing screening.
- Expanded the operator guide with installation, complete stage order, license checks,
  1 m DEM verification, safe retry behavior, acceptance checks, and explicit review inputs.
- Added a manager-ready handoff message that distinguishes tested Basic-license behavior,
  Advanced/Spatial Analyst expectations, traceability, and engineering limitations.
- Rewrote the handoff as a first-person submission message with current capabilities,
  installation steps, package contents, and a manager acceptance-test procedure.
- Added a six-screenshot Pegasus test narrative, Basic-versus-Advanced capability table,
  incorporated resolutions, and an explicit manager-submission checklist.
- Added a standard-library release builder that creates a personalized manager PDF, clean
  toolbox ZIP, and SHA-256 release manifest without packaging project data.

## 0.3.2 - 2026-08-03

- Corrected image-service filter placement and GeoJSON output naming for live ArcGIS
  authoritative-data acquisition.
- Corrected the SSURGO map-unit catalog URL to address a feature layer rather than its
  FeatureServer container.
- Preserve completed acquisitions on rerun and place failed retries in new timestamped
  folders so immutable downloaded sources are never overwritten.

## 0.3.1 - 2026-08-03

- Added read-only KML/KMZ boundary-candidate conversion to the ArcGIS toolbox.
- Connected KML/KMZ conversion, name-based polygon selection, geometry validation,
  and boundary import into one ArcGIS tool so operators do not run a separate conversion.
- Populate the boundary-name control from polygon placemarks in the selected KML/KMZ,
  report available names on a mismatch, and safely resume an identical prior conversion.
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
