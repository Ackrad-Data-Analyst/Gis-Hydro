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


if __name__ == "__main__":
    unittest.main()
