# Project scope

## Objective

Provide a reusable, boundary-driven workflow for any development site while preserving
traceability and engineering review. No site name is hard-coded. Cygnus is the first
pilot, and company files must remain read-only and must not be committed to this repository.

## Implemented workflow

- Inventory files without changing them.
- Infer likely categories from editable rules.
- Record source provenance when it can be inferred safely.
- Report required and optional data gaps with PASS/REVIEW/FAIL screening states.
- Inspect KMZ containers in memory and produce CSV/JSON plus optional Excel reports.
- Validate an editable authoritative-source catalog and create a site-specific acquisition plan.
- Create and validate a project workspace and polygon boundary.
- Acquire configured ArcGIS vector and image-service data, preserve originals, and record provenance.
- Standardize working GIS copies to an explicitly selected project coordinate system.
- Run Spatial Analyst-gated flow, stream, drainage, and optional watershed candidate processing.
- Screen road/drainage intersections and nearby supplied bridge or culvert records.
- Build a preliminary HEC-RAS review package and consolidated QA/QC index.
- Orchestrate the implemented stages through one complete-workflow ArcGIS tool.

## Explicitly excluded

HEC-RAS execution, automatic final geometry, imagery AI, dashboards, buildable-area
calculations, calibration, final design, and engineering approval are excluded. Live
service compatibility and engineering parameters require controlled workstation review.
