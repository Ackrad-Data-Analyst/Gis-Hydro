# Manager feedback resolution

## Implemented user-experience changes

- **One primary run:** `00 - START HERE > Automated Site Workflow - KMZ to Review Package`
  now accepts the KMZ, creates the named project folder and file geodatabase, imports the
  selected polygon, acquires/standardizes configured sources, runs Spatial Analyst terrain
  and crossing screening, and creates the review package and QA index.
- **Geodatabase clarity:** workspace creation has always created
  `gis/site_hydrology.gdb`; the parameter now says **Parent Folder for Projects** and the
  created geodatabase is returned as a derived output. This prevents the impression that
  only a folder was created and explains why selecting a folder already named after the
  project produces a repeated name.
- **KMZ clarity:** the automated tool accepts only `.kml`/`.kmz`. The ambiguous generic
  boundary-import tool is removed from the visible toolbox. **Boundary Name Contains** is
  renamed **Project Boundary Polygon Name** and populated as a dropdown from the KMZ.
- **Map display:** the completed workflow adds elevation first and the boundary as a
  transparent fill with a red outline, rather than masking terrain with a random polygon
  fill. Symbology remains editable in ArcGIS Pro.
- **Units:** the one-run tool requires Imperial or Metric and writes explicit distance,
  elevation, area, and rainfall units to `qa_qc/workflow_preferences.json`.
- **Soil groups:** A, B, C, and D remain distinct. Dual/mixed groups such as A/D, B/D,
  and C/D use conservative group D for preliminary screening, with REVIEW REQUIRED.

## Existing-map reuse

An ArcGIS map can contain authoritative service layers, symbology, joins, and local data,
but a map is not itself a reproducible data snapshot. **Existing Map Layers** mode now lets
the operator explicitly assign the approved DEM, roads, land cover, and soil-group layers.
The workflow snapshots those layers into the project geodatabase and writes the same
acquisition manifest used by standardization. **Authoritative Catalog** mode remains
available for boundary-clipped services with agency/endpoint/query provenance. The tool
does not silently substitute whichever similarly named layer happens to be open.

## Curve numbers, Manning's n, and infiltration rates

These are not universally constant merely because they are stored in a lookup table.
Curve number depends on land cover/use, treatment, hydrologic condition, soil group and
antecedent runoff condition; roughness and infiltration also depend on method and approved
assumptions. The workflow now includes `config/engineering_lookup.template.json` and a
validator. Automated assignment is deliberately blocked until the profile is marked
`APPROVED`, identifies the approver/date/technical basis, and contains non-empty tables.
This makes approved company constants reusable without silently inventing engineering
values.

## Still REVIEW REQUIRED

Target CRS, source fitness/currency, true 1 m DEM availability, stream threshold, depression
filling, pour points, drainage interpretation, soil/land-cover classifications, lookup-table
approval, crossing interpretation, and final engineering use remain REVIEW REQUIRED.
