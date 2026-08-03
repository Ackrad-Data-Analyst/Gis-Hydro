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

    @property
    def valueAsText(self):
        return str(self.value) if self.value is not None else None


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
        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["project_name", "output_root", "created_geodatabase"],
        )
        self.assertEqual(parameters[2].direction, "Output")

    def test_boundary_tool_requires_boundary_and_workspace(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_boundary_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        parameters = module.ImportValidateBoundary().getParameterInfo()
        self.assertNotIn(module.ImportValidateBoundary, module.Toolbox().tools)
        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["boundary", "project_root", "target_crs", "add_to_map"],
        )

    def test_kml_boundary_candidate_tool_accepts_file_and_workspace(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_kml_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        parameters = module.PrepareKmlBoundaryCandidates().getParameterInfo()
        self.assertIn(module.PrepareKmlBoundaryCandidates, module.Toolbox().tools)
        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["boundary_file", "project_root", "boundary_name_contains", "target_crs", "add_to_map"],
        )
        self.assertEqual(parameters[0].filter.list, ["kml", "kmz"])

    def test_kml_boundary_names_populate_from_selected_kmz(self):
        from tempfile import TemporaryDirectory
        from helpers import make_kmz

        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_kml_names_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        with TemporaryDirectory() as temp:
            kmz = make_kmz(Path(temp) / "boundary.kmz")
            tool = module.PrepareKmlBoundaryCandidates()
            parameters = tool.getParameterInfo()
            parameters[0].value = str(kmz)
            tool.updateParameters(parameters)

        self.assertEqual(parameters[2].filter.list, ["Synthetic boundary"])
        self.assertEqual(parameters[2].value, "Synthetic boundary")

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

    def test_automated_workflow_is_first_and_accepts_kmz_units_and_one_run_inputs(self):
        fake_arcpy = types.SimpleNamespace(Parameter=_Parameter)
        toolbox_path = Path(__file__).parents[1] / "toolboxes" / "site_hydrology_workflow.pyt"
        loader = importlib.machinery.SourceFileLoader("site_hydrology_toolbox_automated_test", str(toolbox_path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"arcpy": fake_arcpy}):
            loader.exec_module(module)

        toolbox = module.Toolbox()
        parameters = module.RunCompleteSiteWorkflow().getParameterInfo()
        self.assertIs(toolbox.tools[0], module.RunCompleteSiteWorkflow)
        self.assertEqual([parameter.name for parameter in parameters], [
            "project_name", "projects_root", "boundary", "boundary_polygon_name",
            "target_crs", "unit_system", "data_source_mode", "map_dem", "map_roads",
            "map_land_cover", "map_soils", "stream_threshold_cells", "fill_dem",
            "source_catalog", "add_to_map",
        ])
        self.assertEqual(parameters[2].filter.list, ["kml", "kmz"])
        self.assertEqual(parameters[5].filter.list, ["Imperial", "Metric"])
        self.assertEqual(parameters[6].filter.list, ["Authoritative Catalog", "Existing Map Layers"])


if __name__ == "__main__":
    unittest.main()
