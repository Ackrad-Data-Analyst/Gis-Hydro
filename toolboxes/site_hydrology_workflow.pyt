# -*- coding: utf-8 -*-
"""ArcGIS Pro Python Toolbox for the site-agnostic hydrology workflow."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import arcpy

TOOLBOX_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = TOOLBOX_DIR.parent
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from hydro_workflow.arcgis_capabilities import evaluate_capabilities, load_capability_config
from hydro_workflow.authoritative_acquisition import acquire_catalog_sources
from hydro_workflow.boundary_validation import import_and_validate_boundary, import_kml_boundary
from hydro_workflow.data_standardization import validate_standardize_data
from hydro_workflow.crossing_screening import screen_crossings
from hydro_workflow.complete_workflow import run_complete_workflow
from hydro_workflow.hec_ras_package import build_hec_ras_review_package
from hydro_workflow.kmz_inspector import list_kml_polygon_names
from hydro_workflow.project_workspace import create_project_workspace
from hydro_workflow.qa_package import generate_qa_package
from hydro_workflow.source_catalog import load_source_catalog
from hydro_workflow.terrain_hydrology import prepare_terrain_hydrology


class Toolbox:
    def __init__(self):
        self.label = "Site Hydrology Workflow"
        self.alias = "site_hydrology"
        self.tools = [
            PreflightEnvironmentCheck,
            CreateProjectWorkspace,
            PrepareKmlBoundaryCandidates,
            ImportValidateBoundary,
            DownloadAuthoritativeData,
            ValidateStandardizeData,
            PrepareTerrainDrainage,
            ScreenRoadsCrossings,
            PrepareHecRasPackage,
            GenerateQaPackage,
            RunCompleteSiteWorkflow,
        ]


class RunCompleteSiteWorkflow:
    def __init__(self):
        self.label = "Run Complete Preliminary Site Workflow"; self.category = "08 - Complete Workflow"; self.canRunInBackground = False
    def getParameterInfo(self):
        specs = [
            ("Project Name", "project_name", "GPString", "Required"),
            ("Projects Root Folder", "projects_root", "DEFolder", "Required"),
            ("Project Boundary", "boundary", "GPFeatureLayer", "Required"),
            ("Approved Project Coordinate System", "target_crs", "GPCoordinateSystem", "Required"),
            ("Authoritative Source Catalog", "source_catalog", "DEFile", "Required"),
            ("DEM Source Name", "dem_source_name", "GPString", "Required"),
            ("Road Source Name", "roads_source_name", "GPString", "Required"),
            ("Stream Threshold (Contributing Cells)", "stream_threshold_cells", "GPLong", "Required"),
            ("Fill Depressions", "fill_dem", "GPBoolean", "Required"),
            ("Bridge Source Name (Optional)", "bridges_source_name", "GPString", "Optional"),
            ("Culvert Source Name (Optional)", "culverts_source_name", "GPString", "Optional"),
            ("Known Structure Search Distance", "structure_search_distance", "GPLinearUnit", "Optional"),
            ("Pour Points (Optional)", "pour_points", "GPFeatureLayer", "Optional"),
            ("Pour Point Snap Distance", "snap_distance", "GPDouble", "Optional"),
            ("Land Cover Source Name (Optional)", "land_cover_source_name", "GPString", "Optional"),
        ]
        parameters = [arcpy.Parameter(displayName=d, name=n, datatype=t, parameterType=r, direction="Input") for d,n,t,r in specs]
        parameters[4].value = str(REPOSITORY_ROOT / "config" / "authoritative_sources.yaml")
        return parameters
    def isLicensed(self): return arcpy.CheckExtension("Spatial") in {"Available", "CheckedOut"}
    def updateParameters(self, parameters):
        catalog_text = parameters[4].valueAsText
        if catalog_text and Path(catalog_text).is_file():
            try:
                names = [row["name"] for row in load_source_catalog(Path(catalog_text))]
                for index in (5, 6, 9, 10, 14): parameters[index].filter.list = names
            except (ValueError, OSError): pass
    def updateMessages(self, parameters):
        if (parameters[9].valueAsText or parameters[10].valueAsText) and not parameters[11].valueAsText:
            parameters[11].setErrorMessage("Search distance is required with known structures.")
        if parameters[12].valueAsText and parameters[13].value is None:
            parameters[13].setErrorMessage("Snap distance is required with pour points.")
    def execute(self, parameters, messages):
        sources = load_source_catalog(Path(parameters[4].valueAsText))
        result = run_complete_workflow(
            parameters[0].valueAsText, Path(parameters[1].valueAsText), parameters[2].valueAsText,
            parameters[3].value, sources, parameters[5].valueAsText, parameters[6].valueAsText,
            int(parameters[7].value), bool(parameters[8].value), arcpy,
            parameters[9].valueAsText or None, parameters[10].valueAsText or None,
            parameters[11].valueAsText or None, parameters[12].valueAsText or None,
            float(parameters[13].value) if parameters[13].value is not None else None,
            parameters[14].valueAsText or None,
        )
        arcpy.AddMessage(f"Complete workflow outputs: {result.project_root}")
        arcpy.AddWarning(result.review_notes)


class ScreenRoadsCrossings:
    def __init__(self):
        self.label = "Screen Roads, Bridges, Culverts, and Drainage Crossings"
        self.category = "05 - Infrastructure and Crossings"; self.canRunInBackground = False
    def getParameterInfo(self):
        specs = [
            ("Existing Project Workspace", "project_root", "DEFolder", "Required"),
            ("Road Centerlines", "roads", "GPFeatureLayer", "Required"),
            ("Drainage Path Candidates", "drainage_paths", "GPFeatureLayer", "Required"),
            ("Known Bridges (Optional)", "bridges", "GPFeatureLayer", "Optional"),
            ("Known Culverts (Optional)", "culverts", "GPFeatureLayer", "Optional"),
            ("Known Structure Search Distance (REVIEW REQUIRED)", "search_distance", "GPLinearUnit", "Optional"),
        ]
        return [arcpy.Parameter(displayName=d, name=n, datatype=t, parameterType=r, direction="Input") for d,n,t,r in specs]
    def isLicensed(self): return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}
    def updateParameters(self, parameters): return
    def updateMessages(self, parameters):
        if (parameters[3].valueAsText or parameters[4].valueAsText) and not parameters[5].valueAsText:
            parameters[5].setErrorMessage("Search distance is required with known structures.")
    def execute(self, parameters, messages):
        result = screen_crossings(Path(parameters[0].valueAsText), parameters[1].valueAsText,
            parameters[2].valueAsText, arcpy, parameters[3].valueAsText or None,
            parameters[4].valueAsText or None, parameters[5].valueAsText or None)
        arcpy.AddMessage(f"Potential crossings: {result.potential_crossing_count}")
        arcpy.AddWarning(result.review_notes)


class PrepareHecRasPackage:
    def __init__(self):
        self.label = "Prepare Preliminary HEC-RAS Review Package"; self.category = "06 - HEC-RAS Preparation"; self.canRunInBackground = False
    def getParameterInfo(self):
        specs = [
            ("Existing Project Workspace", "project_root", "DEFolder", "Required"),
            ("Preliminary Terrain", "terrain", "GPRasterLayer", "Required"),
            ("Stream Centerline Candidates", "stream_centerlines", "GPFeatureLayer", "Optional"),
            ("Bank Line Candidates", "bank_lines", "GPFeatureLayer", "Optional"),
            ("Flow Path Candidates", "flow_paths", "GPFeatureLayer", "Optional"),
            ("Cross Section Candidates", "cross_sections", "GPFeatureLayer", "Optional"),
            ("Road and Crossing Locations", "crossings", "GPFeatureLayer", "Optional"),
            ("Land Cover / Roughness Source", "land_cover", "GPFeatureLayer", "Optional"),
        ]
        return [arcpy.Parameter(displayName=d, name=n, datatype=t, parameterType=r, direction="Input") for d,n,t,r in specs]
    def isLicensed(self): return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}
    def updateParameters(self, parameters): return
    def updateMessages(self, parameters): return
    def execute(self, parameters, messages):
        names = ["stream_centerlines", "bank_lines", "flow_paths", "cross_sections", "crossings", "land_cover"]
        layers = {name: parameters[index + 2].valueAsText or None for index, name in enumerate(names)}
        result = build_hec_ras_review_package(Path(parameters[0].valueAsText), parameters[1].valueAsText, arcpy, layers)
        arcpy.AddMessage(f"Review package: {result.package_root}"); arcpy.AddWarning(result.review_notes)


class GenerateQaPackage:
    def __init__(self):
        self.label = "Generate QA/QC Package"; self.category = "07 - QA and Reporting"; self.canRunInBackground = False
    def getParameterInfo(self):
        return [arcpy.Parameter(displayName="Existing Project Workspace", name="project_root", datatype="DEFolder", parameterType="Required", direction="Input")]
    def isLicensed(self): return True
    def updateParameters(self, parameters): return
    def updateMessages(self, parameters): return
    def execute(self, parameters, messages):
        json_path, csv_path = generate_qa_package(Path(parameters[0].valueAsText))
        arcpy.AddMessage(f"QA/QC JSON: {json_path}"); arcpy.AddMessage(f"QA/QC CSV: {csv_path}")


class PrepareTerrainDrainage:
    def __init__(self):
        self.label = "Prepare Terrain, Drainage, and Watershed Candidates"
        self.description = "Run license-gated flow processing with explicit engineer-reviewed parameters."
        self.category = "04 - Terrain and Drainage"
        self.canRunInBackground = False

    def getParameterInfo(self):
        project_root = arcpy.Parameter(displayName="Existing Project Workspace", name="project_root",
            datatype="DEFolder", parameterType="Required", direction="Input")
        dem = arcpy.Parameter(displayName="Validated Standardized DEM", name="dem",
            datatype="GPRasterLayer", parameterType="Required", direction="Input")
        threshold = arcpy.Parameter(displayName="Stream Threshold (Contributing Cells; REVIEW REQUIRED)",
            name="stream_threshold_cells", datatype="GPLong", parameterType="Required", direction="Input")
        fill_dem = arcpy.Parameter(displayName="Fill Depressions (REVIEW REQUIRED)", name="fill_dem",
            datatype="GPBoolean", parameterType="Required", direction="Input")
        pour_points = arcpy.Parameter(displayName="Pour Points (Optional; REVIEW REQUIRED)", name="pour_points",
            datatype="GPFeatureLayer", parameterType="Optional", direction="Input")
        snap_distance = arcpy.Parameter(displayName="Pour Point Snap Distance (Optional; dataset units)",
            name="snap_distance", datatype="GPDouble", parameterType="Optional", direction="Input")
        return [project_root, dem, threshold, fill_dem, pour_points, snap_distance]

    def isLicensed(self):
        return arcpy.CheckExtension("Spatial") in {"Available", "CheckedOut"}

    def updateParameters(self, parameters): return

    def updateMessages(self, parameters):
        if parameters[4].valueAsText and not parameters[5].value:
            parameters[5].setErrorMessage("Snap distance is required when pour points are supplied.")

    def execute(self, parameters, messages):
        result = prepare_terrain_hydrology(
            Path(parameters[0].valueAsText), parameters[1].valueAsText,
            int(parameters[2].value), bool(parameters[3].value), arcpy,
            parameters[4].valueAsText or None,
            float(parameters[5].value) if parameters[5].value is not None else None,
        )
        arcpy.AddMessage(f"Flow direction: {result.flow_direction}")
        arcpy.AddMessage(f"Flow accumulation: {result.flow_accumulation}")
        arcpy.AddMessage(f"Drainage candidates: {result.drainage_paths}")
        if result.watersheds: arcpy.AddMessage(f"Watershed candidates: {result.watersheds}")
        arcpy.AddWarning(result.review_notes)


class ValidateStandardizeData:
    def __init__(self):
        self.label = "Validate, Standardize, and Clip Acquired Data"
        self.description = "Inspect acquired GIS data and project working copies to an explicitly selected CRS."
        self.category = "03 - Data Preparation"
        self.canRunInBackground = False

    def getParameterInfo(self):
        project_root = arcpy.Parameter(
            displayName="Existing Project Workspace", name="project_root",
            datatype="DEFolder", parameterType="Required", direction="Input",
        )
        target_crs = arcpy.Parameter(
            displayName="Approved Project Coordinate System (REVIEW REQUIRED)", name="target_crs",
            datatype="GPCoordinateSystem", parameterType="Required", direction="Input",
        )
        return [project_root, target_crs]

    def isLicensed(self):
        return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        results = validate_standardize_data(
            Path(parameters[0].valueAsText), parameters[1].value, arcpy
        )
        for result in results:
            message = f"{result.status}: {result.source_name} - extent overlap {result.extent_coverage_percent}%"
            if result.status == "FAIL": arcpy.AddWarning(message)
            else: arcpy.AddMessage(message)
        if any(result.status == "FAIL" for result in results):
            raise arcpy.ExecuteError("One or more datasets failed standardization; review QA report")


class DownloadAuthoritativeData:
    """Download all or selected rows from the editable authoritative-source catalog."""

    def __init__(self):
        self.label = "Download Authoritative Data"
        self.description = "Acquire configured vector and image services for the validated site boundary."
        self.category = "02 - Data Acquisition"
        self.canRunInBackground = False

    def getParameterInfo(self):
        project_root = arcpy.Parameter(
            displayName="Existing Project Workspace", name="project_root",
            datatype="DEFolder", parameterType="Required", direction="Input",
        )
        catalog = arcpy.Parameter(
            displayName="Authoritative Source Catalog", name="source_catalog",
            datatype="DEFile", parameterType="Required", direction="Input",
        )
        catalog.value = str(REPOSITORY_ROOT / "config" / "authoritative_sources.yaml")
        selected = arcpy.Parameter(
            displayName="Source Names (Optional; blank downloads every catalog row)",
            name="selected_sources", datatype="GPString", parameterType="Optional", direction="Input",
            multiValue=True,
        )
        return [project_root, catalog, selected]

    def isLicensed(self):
        return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}

    def updateParameters(self, parameters):
        catalog_text = parameters[1].valueAsText
        if catalog_text and Path(catalog_text).is_file():
            try:
                parameters[2].filter.list = [row["name"] for row in load_source_catalog(Path(catalog_text))]
            except (ValueError, OSError):
                pass

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        sources = load_source_catalog(Path(parameters[1].valueAsText))
        selected_text = parameters[2].valueAsText or ""
        selected = {value.strip(" '\"") for value in selected_text.split(";") if value.strip(" '\"")} or None
        results = acquire_catalog_sources(Path(parameters[0].valueAsText), sources, arcpy, selected)
        failures = [result for result in results if result.status == "FAIL"]
        for result in results:
            message = f"{result.status}: {result.source_name} - {result.message}"
            if result.status == "FAIL":
                arcpy.AddWarning(message)
            else:
                arcpy.AddMessage(message)
        if failures:
            raise arcpy.ExecuteError(f"{len(failures)} source acquisition(s) failed; review the QA manifest")
        arcpy.AddMessage(f"Completed {len(results)} catalog-driven acquisition(s).")


class ImportValidateBoundary:
    """Validate a boundary and copy it into an existing project workspace."""

    def __init__(self):
        self.label = "Import and Validate Boundary"
        self.description = "Validate polygon geometry and CRS, then copy it without changing the source."
        self.category = "01 - Project Setup"
        self.canRunInBackground = False

    def getParameterInfo(self):
        boundary = arcpy.Parameter(
            displayName="Project Boundary",
            name="boundary",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )
        project_root = arcpy.Parameter(
            displayName="Existing Project Workspace",
            name="project_root",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )
        target_crs = arcpy.Parameter(
            displayName="Target Coordinate System (Optional; REVIEW REQUIRED)",
            name="target_crs",
            datatype="GPCoordinateSystem",
            parameterType="Optional",
            direction="Input",
        )
        add_to_map = arcpy.Parameter(
            displayName="Add Imported Boundary to Current Map",
            name="add_to_map",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        add_to_map.value = True
        return [boundary, project_root, target_crs, add_to_map]

    def isLicensed(self):
        return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        target_crs = parameters[2].value if parameters[2].value else None
        result = import_and_validate_boundary(
            parameters[0].valueAsText,
            Path(parameters[1].valueAsText),
            arcpy,
            target_crs,
        )
        arcpy.AddMessage(f"Imported boundary: {result.imported_boundary}")
        arcpy.AddMessage(f"Features: {result.feature_count}; CRS: {result.output_spatial_reference}")
        arcpy.AddWarning(result.review_notes)
        if bool(parameters[3].value):
            project = arcpy.mp.ArcGISProject("CURRENT")
            if project.activeMap is not None:
                project.activeMap.addDataFromPath(result.imported_boundary)


class PrepareKmlBoundaryCandidates:
    """Convert and import a named project boundary from KML/KMZ."""

    def __init__(self):
        self.label = "Import and Validate KML/KMZ Boundary"
        self.description = (
            "Convert a KML/KMZ read-only, select polygons by name, validate them, "
            "and import the project boundary without changing the source."
        )
        self.category = "01 - Project Setup"
        self.canRunInBackground = False

    def getParameterInfo(self):
        source = arcpy.Parameter(
            displayName="Project Boundary KML or KMZ",
            name="boundary_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        source.filter.list = ["kml", "kmz"]
        project_root = arcpy.Parameter(
            displayName="Existing Project Workspace",
            name="project_root",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )
        boundary_name = arcpy.Parameter(
            displayName="Boundary Name Contains (for example: Project Boundary)",
            name="boundary_name_contains",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        target_crs = arcpy.Parameter(
            displayName="Target Coordinate System (Optional; REVIEW REQUIRED)",
            name="target_crs",
            datatype="GPCoordinateSystem",
            parameterType="Optional",
            direction="Input",
        )
        add_to_map = arcpy.Parameter(
            displayName="Add Imported Boundary to Current Map",
            name="add_to_map",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        add_to_map.value = True
        return [source, project_root, boundary_name, target_crs, add_to_map]

    def isLicensed(self):
        return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}

    def updateParameters(self, parameters):
        source_text = parameters[0].valueAsText
        if not source_text or not Path(source_text).is_file():
            return
        try:
            names = list_kml_polygon_names(Path(source_text))
        except ValueError:
            return
        parameters[2].filter.list = names
        if parameters[2].valueAsText:
            return
        preferred = [
            name for name in names
            if "boundary" in name.lower()
            and not any(token in name.lower() for token in ("row", "right of way", "corridor"))
        ]
        if len(preferred) == 1:
            parameters[2].value = preferred[0]

    def updateMessages(self, parameters):
        source_text = parameters[0].valueAsText
        if source_text and Path(source_text).is_file():
            try:
                names = list_kml_polygon_names(Path(source_text))
            except ValueError as exc:
                parameters[0].setErrorMessage(str(exc))
                return
            if not names:
                parameters[0].setErrorMessage("The KML/KMZ contains no named polygon placemarks.")

    def execute(self, parameters, messages):
        polygon_names = list_kml_polygon_names(Path(parameters[0].valueAsText))
        candidates, result = import_kml_boundary(
            Path(parameters[0].valueAsText),
            Path(parameters[1].valueAsText),
            arcpy,
            parameters[2].valueAsText,
            parameters[3].value if parameters[3].value else None,
            polygon_names,
        )
        arcpy.AddMessage(f"Converted source: {candidates.output_geodatabase}")
        arcpy.AddMessage(f"Imported boundary: {result.imported_boundary}")
        if bool(parameters[4].value):
            project = arcpy.mp.ArcGISProject("CURRENT")
            if project.activeMap is not None:
                project.activeMap.addDataFromPath(result.imported_boundary)
        arcpy.AddWarning(result.review_notes)


class CreateProjectWorkspace:
    """Create the standard project folder tree and file geodatabase without overwrite."""

    def __init__(self):
        self.label = "Create Project Workspace"
        self.description = "Create an immutable site workspace, geodatabase, and QA manifest."
        self.category = "01 - Project Setup"
        self.canRunInBackground = False

    def getParameterInfo(self):
        project_name = arcpy.Parameter(
            displayName="Project Name",
            name="project_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        output_root = arcpy.Parameter(
            displayName="Projects Root Folder",
            name="output_root",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )
        return [project_name, output_root]

    def isLicensed(self):
        return arcpy.ProductInfo() not in {"NotInitialized", "Unavailable"}

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        manifest = create_project_workspace(
            parameters[0].valueAsText,
            Path(parameters[1].valueAsText),
            arcpy,
        )
        arcpy.AddMessage(f"Created project workspace: {manifest.project_root}")
        arcpy.AddMessage(f"Created project geodatabase: {manifest.geodatabase}")
        arcpy.AddWarning(manifest.engineering_notice)


class PreflightEnvironmentCheck:
    """Record license-dependent workflow availability before processing any site."""

    def __init__(self):
        self.label = "Preflight Environment Check"
        self.description = "Inspect ArcGIS Pro, license, extensions, portal, and configured workflow capabilities."
        self.category = "00 - Environment and QA"
        self.canRunInBackground = False

    def getParameterInfo(self):
        output_folder = arcpy.Parameter(
            displayName="Output Folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )
        add_table = arcpy.Parameter(
            displayName="Add Capability Table to Current Map",
            name="add_table_to_map",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        add_table.value = True
        return [output_folder, add_table]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    @staticmethod
    def _normalize_license(product_info):
        aliases = {
            "ArcView": "Basic", "Basic": "Basic",
            "ArcEditor": "Standard", "Standard": "Standard",
            "ArcInfo": "Advanced", "Advanced": "Advanced",
        }
        return aliases.get(product_info, product_info)

    def execute(self, parameters, messages):
        output_folder = Path(parameters[0].valueAsText).expanduser().resolve()
        output_folder.mkdir(parents=True, exist_ok=True)
        config_path = REPOSITORY_ROOT / "config" / "arcgis_capabilities.yaml"
        config = load_capability_config(config_path)

        install_info = arcpy.GetInstallInfo()
        product_info = arcpy.ProductInfo()
        license_level = self._normalize_license(product_info)
        extension_statuses = {
            "Spatial": arcpy.CheckExtension("Spatial"),
            "3D": arcpy.CheckExtension("3D"),
            "ImageAnalyst": arcpy.CheckExtension("ImageAnalyst"),
        }
        portal_url = arcpy.GetActivePortalURL() or ""
        try:
            signed_in = bool(arcpy.GetSigninToken())
        except RuntimeError:
            signed_in = False

        capabilities = evaluate_capabilities(license_level, extension_statuses, config)
        report = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "arcgis_pro_version": install_info.get("Version", "Unknown"),
            "python_version": sys.version,
            "product_info_raw": product_info,
            "license_level": license_level,
            "extensions": extension_statuses,
            "active_portal_url": portal_url,
            "portal_signed_in": signed_in,
            "repository_root": str(REPOSITORY_ROOT),
            "configuration": str(config_path),
            "review_notice": config["review_notice"],
            "capabilities": [result.to_dict() for result in capabilities],
        }
        json_path = output_folder / "arcgis_preflight_report.json"
        csv_path = output_folder / "arcgis_capability_matrix.csv"
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        columns = ["name", "available", "status", "reason", "minimum_license", "required_extensions", "description"]
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(result.to_dict() for result in capabilities)

        arcpy.AddMessage(f"ArcGIS Pro version: {report['arcgis_pro_version']}")
        arcpy.AddMessage(f"License level: {license_level}")
        arcpy.AddMessage(f"Portal signed in: {signed_in}")
        for result in capabilities:
            message = f"{result.status}: {result.name} - {result.reason}"
            if result.available:
                arcpy.AddMessage(message)
            else:
                arcpy.AddWarning(message)

        if bool(parameters[1].value):
            project = arcpy.mp.ArcGISProject("CURRENT")
            if project.activeMap is not None:
                project.activeMap.addDataFromPath(str(csv_path))
                arcpy.AddMessage("Added capability matrix to the current map.")
            else:
                arcpy.AddWarning("No active map; capability CSV was created but not added.")
