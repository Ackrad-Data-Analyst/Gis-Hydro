# Module 1 requirements

The CLI accepts project folder/name, configuration folder, output folder, dry-run, and
verbose options. It inventories supported and unknown files, hashes every readable file,
classifies by external configuration, inspects KMZ safely, evaluates configured data
gaps, logs actions, and verifies hashes after processing.

Required reports are inventory, source register, gap report, summary, integrity report,
and run log. CSV and JSON are mandatory. XLSX is conditional on an already available
`openpyxl` installation. Dry-run performs analysis but writes nothing.

The implementation must be cross-platform Python, typed and understandable, use
synthetic tests, perform no network activity, and never write below the scanned source
folder. Full acceptance tests are documented in `docs/test_plan.md`.

The `plan-acquisition` command must accept any project name and KMZ boundary, validate
`config/authoritative_sources.yaml`, and write a reviewable source plan without contacting
remote services. The manager-provided catalog is configuration, not hard-coded Python.
Network acquisition uses the catalog-driven ArcGIS adapter and must retain coverage,
schema, CRS, licensing, metadata, and download-integrity records. Retry and pagination
controls require live-service validation before department deployment.

The ArcGIS workflow requires explicit target CRS and engineering parameters, preserves
original acquisitions, refuses overwrite, records provenance, gates terrain processing
on Spatial Analyst, and labels derived drainage, crossing, watershed, and HEC-RAS review
inputs REVIEW REQUIRED. Live endpoint, pagination, retry, and engineering acceptance
testing remain mandatory before department deployment.
