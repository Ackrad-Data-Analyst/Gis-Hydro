# Changelog

## 0.2.1 - 2026-08-02

- Added a manager handoff guide with illustrated ArcGIS Pro setup steps.
- Added a double-click Windows launcher that opens the toolbox location and ArcGIS Pro
  without requiring Git, PowerShell, or Python package installation.
- Changed the manager handoff to an approved OneNote/Teams/SharePoint ZIP transfer; the
  receiving team member does not need a GitHub account.
- Simplified the ArcGIS Pro preflight dialog to input-only parameters to avoid a COM error when opening the Python toolbox in ArcGIS Pro 3.7.
- Added the first operational workflow tool: site-agnostic project workspace and file
  geodatabase creation with no-overwrite protection and a QA manifest.

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
