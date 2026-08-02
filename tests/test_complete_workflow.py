import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hydro_workflow.complete_workflow import run_complete_workflow


class CompleteWorkflowTests(unittest.TestCase):
    @patch("hydro_workflow.complete_workflow.generate_qa_package")
    @patch("hydro_workflow.complete_workflow.build_hec_ras_review_package")
    @patch("hydro_workflow.complete_workflow.screen_crossings")
    @patch("hydro_workflow.complete_workflow.prepare_terrain_hydrology")
    @patch("hydro_workflow.complete_workflow.validate_standardize_data")
    @patch("hydro_workflow.complete_workflow.acquire_catalog_sources")
    @patch("hydro_workflow.complete_workflow.import_and_validate_boundary")
    @patch("hydro_workflow.complete_workflow.create_project_workspace")
    def test_runner_connects_every_stage(self, create, boundary, acquire, standardize, terrain, crossings, hec, qa):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; (root / "qa_qc").mkdir(parents=True)
            create.return_value = types.SimpleNamespace(project_root=str(root))
            boundary.return_value = types.SimpleNamespace(imported_boundary="boundary")
            acquire.return_value = [types.SimpleNamespace(source_name="DEM", status="REVIEW"), types.SimpleNamespace(source_name="Roads", status="REVIEW")]
            standardize.return_value = [types.SimpleNamespace(source_name="DEM", standardized_dataset="dem", status="REVIEW"), types.SimpleNamespace(source_name="Roads", standardized_dataset="roads", status="REVIEW")]
            terrain.return_value = types.SimpleNamespace(filled_dem="filled", drainage_paths="streams")
            crossings.return_value = types.SimpleNamespace(screened_crossings="crossings")
            hec.return_value = types.SimpleNamespace(package_root="hec_package")
            qa.return_value = (root / "qa.json", root / "qa.csv")
            result = run_complete_workflow("Site", Path(temp), "source_boundary", "crs", [], "DEM", "Roads", 500, True, object())
            self.assertEqual(result.status, "REVIEW")
            self.assertEqual(result.acquired_sources, 2)
            terrain.assert_called_once(); crossings.assert_called_once(); hec.assert_called_once(); qa.assert_called_once()


if __name__ == "__main__": unittest.main()
