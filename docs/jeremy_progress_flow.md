# Automated Hydro Workflow Progress for Jeremy Masell

This page maps the current prototype to Adolfo's seven-step communication flowchart. It is
written for Civil & Engineering progress reporting: Jeremy Masell is Director, Adolfo is
manager, Jessica is civil engineer, and Ackrad Seth Shimwense is the civil engineering intern.

| Step | Flowchart deliverable | Current prototype status | Current output / handoff |
|---|---|---|---|
| 01 | Process user input project boundary | TESTING | Imports a selected KML/KMZ polygon by name, preserves the original source, hashes it, and writes boundary QA. |
| 02 | Process boundary and acquire project data | TESTING | Uses Existing Map Layers first or Catalog Services. Catalog rows are editable and include HUC12, roads/railroads, NHDPlus HR streams, FEMA flood zones, HSG, NLCD, soil map units, 3DEP elevation, and NOAA Atlas 14 reference records. |
| 03 | Acquire rainfall and storm temporal distribution | NOT STARTED / REFERENCE RECORDED | NOAA Atlas 14 PFDS is recorded as a reference-only source. The current tool does not invent design storms; a later rainfall tool must prompt the engineer for project-approved precipitation inputs. |
| 04 | Acquire project terrain data | TESTING | Existing project DEM/map DEM or catalog 3DEP elevation can be staged, clipped, and recorded with provenance. |
| 05 | Process terrain data for HEC-RAS | IN PROGRESS | Creates terrain/drainage review outputs when Spatial Analyst is available; stream threshold, fill choice, and derived drainage remain REVIEW REQUIRED. |
| 06 | Process land data for HEC-RAS | IN PROGRESS | Stages land cover/HSG/soil layers and can combine hydrologic-response candidates. Manning's n/CN/infiltration values come from an approved engineering lookup file, not invented from the boundary. |
| 07 | Run HEC-RAS model | NOT STARTED | The package prepares review inputs for HEC-RAS. Automated HEC-RAS model execution is not implemented in this increment. |

Quality control is required at every handoff: spatial reference, units, datum, extent,
resolution, completeness, source provenance, and engineering suitability remain REVIEW REQUIRED.
