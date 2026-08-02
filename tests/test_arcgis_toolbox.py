import importlib.machinery
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _Parameter:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.value = None
        self.filter = types.SimpleNamespace(list=[])


class ArcGISToolboxTests(unittest.TestCase):
    def test_preflight_dialog_uses_only_input_parameters(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)

        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        parameters = module.PreflightEnvironmentCheck().getParameterInfo()

        self.assertEqual([parameter.name for parameter in parameters], ["output_folder", "add_table_to_map"])
        self.assertTrue(all(parameter.direction == "Input" for parameter in parameters))

    def test_workspace_tool_has_site_agnostic_inputs(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_workspace_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)

        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        toolbox = module.Toolbox()
        parameters = module.CreateProjectWorkspace().getParameterInfo()

        self.assertIn(module.CreateProjectWorkspace, toolbox.tools)
        self.assertEqual([parameter.name for parameter in parameters], ["project_name", "output_root"])

    def test_boundary_tool_requires_boundary_and_workspace(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_boundary_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        parameters = module.ImportValidateBoundary().getParameterInfo()
        self.assertIn(module.ImportValidateBoundary, module.Toolbox().tools)
        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["boundary", "project_root", "target_crs", "add_to_map"],
        )

    def test_acquisition_tool_accepts_catalog_and_optional_source_list(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_acquisition_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        parameters = module.DownloadAuthoritativeData().getParameterInfo()
        self.assertIn(module.DownloadAuthoritativeData, module.Toolbox().tools)
        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["project_root", "source_catalog", "selected_sources"],
        )
        self.assertTrue(parameters[2].multiValue)

    def test_standardization_requires_explicit_target_crs(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_standardize_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}): loader.exec_module(module)
        parameters = module.ValidateStandardizeData().getParameterInfo()
        self.assertIn(module.ValidateStandardizeData, module.Toolbox().tools)
        self.assertEqual([parameter.name for parameter in parameters], ["project_root", "target_crs"])
        self.assertEqual(parameters[1].parameterType, "Required")

    def test_terrain_tool_requires_engineering_parameters(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_terrain_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}): loader.exec_module(module)
        parameters = module.PrepareTerrainDrainage().getParameterInfo()
        self.assertIn(module.PrepareTerrainDrainage, module.Toolbox().tools)
        self.assertEqual([parameter.name for parameter in parameters], [
            "project_root", "dem", "stream_threshold_cells", "fill_dem", "pour_points", "snap_distance"
        ])
        self.assertEqual(parameters[2].parameterType, "Required")
        self.assertEqual(parameters[3].parameterType, "Required")


if __name__ == "__main__":
    unittest.main()
