import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from hydro_workflow.complete_workflow import run_complete_workflow


class CompleteWorkflowTests(unittest.TestCase):
    @patch("hydro_workflow.complete_workflow.generate_qa_package")
    @patch("hydro_workflow.complete_workflow.build_hec_ras_review_package")
    @patch("hydro_workflow.complete_workflow.combine_land_cover_soils")
    @patch("hydro_workflow.complete_workflow.prepare_terrain_hydrology")
    @patch("hydro_workflow.complete_workflow.validate_standardize_data")
    @patch("hydro_workflow.complete_workflow.acquire_catalog_sources")
    @patch("hydro_workflow.complete_workflow.import_and_validate_boundary")
    @patch("hydro_workflow.complete_workflow.create_project_workspace")
    def test_raster_response_units_are_not_exported_as_hec_vector_layers(
        self, create, boundary, acquire, standardize, terrain, combine, hec, qa
    ):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; (root / "qa_qc").mkdir(parents=True)
            create.return_value = types.SimpleNamespace(project_root=str(root))
            boundary.return_value = types.SimpleNamespace(imported_boundary="boundary")
            acquire.return_value = []
            standardize.return_value = [
                types.SimpleNamespace(source_name="DEM", standardized_dataset="dem", status="REVIEW"),
                types.SimpleNamespace(source_name="Land", standardized_dataset="land_raster", status="REVIEW"),
                types.SimpleNamespace(source_name="Soils", standardized_dataset="soil_raster", status="REVIEW"),
            ]
            terrain.return_value = types.SimpleNamespace(filled_dem="filled", drainage_paths="streams")
            combine.return_value = types.SimpleNamespace(combined_raster="response_units_raster")
            hec.return_value = types.SimpleNamespace(package_root="hec_package")
            qa.return_value = (root / "qa.json", root / "qa.csv")

            run_complete_workflow(
                "Site", Path(temp), "source_boundary", "crs", [], "DEM", "Roads", 500,
                True, object(), land_cover_source_name="Land", soil_group_source_name="Soils"
            )

            combine.assert_called_once()
            layers = hec.call_args.args[3]
            self.assertNotIn("land_cover", layers)
            self.assertNotIn("response_units_raster", layers.values())

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
            preferences = (root / "qa_qc" / "workflow_preferences.json").read_text()
            self.assertIn('"unit_system": "Imperial"', preferences)

    @patch("hydro_workflow.complete_workflow.generate_qa_package")
    @patch("hydro_workflow.complete_workflow.build_hec_ras_review_package")
    @patch("hydro_workflow.complete_workflow.screen_crossings")
    @patch("hydro_workflow.complete_workflow.prepare_terrain_hydrology")
    @patch("hydro_workflow.complete_workflow.validate_standardize_data")
    @patch("hydro_workflow.complete_workflow.acquire_catalog_sources")
    @patch("hydro_workflow.complete_workflow.import_and_validate_boundary")
    @patch("hydro_workflow.complete_workflow.create_project_workspace")
    def test_optional_land_cover_and_roads_failures_do_not_discard_terrain(
        self, create, boundary, acquire, standardize, terrain, crossings, hec, qa
    ):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; (root / "qa_qc").mkdir(parents=True)
            create.return_value = types.SimpleNamespace(project_root=str(root))
            boundary.return_value = types.SimpleNamespace(imported_boundary="boundary")
            acquire.return_value = [
                types.SimpleNamespace(source_name="DEM", status="REVIEW", message="ok"),
                types.SimpleNamespace(source_name="Roads", status="FAIL", message="service unavailable"),
                types.SimpleNamespace(source_name="Land", status="FAIL", message="service unavailable"),
            ]
            standardize.return_value = [
                types.SimpleNamespace(source_name="DEM", standardized_dataset="dem", status="REVIEW"),
                types.SimpleNamespace(source_name="Roads", standardized_dataset=None, status="FAIL"),
                types.SimpleNamespace(source_name="Land", standardized_dataset=None, status="FAIL"),
            ]
            terrain.return_value = types.SimpleNamespace(filled_dem="filled", drainage_paths="streams")
            hec.return_value = types.SimpleNamespace(package_root="hec_package")
            qa.return_value = (root / "qa.json", root / "qa.csv")

            result = run_complete_workflow(
                "Site", Path(temp), "source_boundary", "crs", [], "DEM", "Roads", 500,
                True, object(), land_cover_source_name="Land"
            )

            crossings.assert_not_called()
            self.assertIn("Land", result.review_notes)
            self.assertIn("Roads", result.review_notes)
            self.assertIn("service unavailable", result.review_notes)
            report = Path(result.crossings_report).read_text(encoding="utf-8")
            self.assertIn("crossing screening was skipped", report)
            hec.assert_called_once()

    @patch("hydro_workflow.complete_workflow.acquire_catalog_sources")
    @patch("hydro_workflow.complete_workflow.import_and_validate_boundary")
    @patch("hydro_workflow.complete_workflow.create_project_workspace")
    def test_required_dem_failure_has_actionable_error(self, create, boundary, acquire):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; (root / "qa_qc").mkdir(parents=True)
            create.return_value = types.SimpleNamespace(project_root=str(root))
            boundary.return_value = types.SimpleNamespace(imported_boundary="boundary")
            acquire.return_value = [
                types.SimpleNamespace(source_name="DEM", status="FAIL", message="HTTP 503")
            ]
            with self.assertRaisesRegex(RuntimeError, "Existing Map Layers"):
                run_complete_workflow(
                    "Site", Path(temp), "source_boundary", "crs", [], "DEM", "Roads",
                    500, True, object()
                )


if __name__ == "__main__": unittest.main()
