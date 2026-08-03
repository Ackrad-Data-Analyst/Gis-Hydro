# Test plan

Synthetic automated tests cover empty input, valid/invalid KMZ, known formats, missing required and optional categories, simulated unreadability, unknown extensions, duplicate names in separate directories, dry run, output creation, before/after integrity, configuration loading, report columns, and Windows-style path representation.

Run `PYTHONPATH=src python -m unittest discover -s tests -v`. Tests must pass before completion. No company data or network access is used.

ArcGIS capability tests cover Basic without extensions, Standard with Spatial Analyst,
Advanced with all configured extensions, and unknown-license fail-safe behavior. Native
`.pyt` execution must additionally be tested in ArcGIS Pro because ArcPy is unavailable
in the standard automated-test environment.
