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


class Toolbox:
    def __init__(self):
        self.label = "Site Hydrology Workflow"
        self.alias = "site_hydrology"
        self.tools = [PreflightEnvironmentCheck]


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
        report_json = arcpy.Parameter(
            displayName="Preflight Report JSON",
            name="preflight_report_json",
            datatype="DEFile",
            parameterType="Derived",
            direction="Output",
        )
        report_csv = arcpy.Parameter(
            displayName="Capability Matrix CSV",
            name="capability_matrix_csv",
            datatype="DEFile",
            parameterType="Derived",
            direction="Output",
        )
        return [output_folder, add_table, report_json, report_csv]

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

        parameters[2].value = str(json_path)
        parameters[3].value = str(csv_path)
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
