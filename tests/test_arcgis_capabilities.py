import unittest
from pathlib import Path

from hydro_workflow.arcgis_capabilities import evaluate_capabilities, load_capability_config

CONFIG = Path(__file__).parents[1] / "config" / "arcgis_capabilities.yaml"


class ArcGisCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.config = load_capability_config(CONFIG)

    def test_basic_without_extensions_gets_supported_subset(self):
        results = evaluate_capabilities(
            "Basic", {"Spatial": "Unavailable", "3D": "Unavailable", "ImageAnalyst": "Unavailable"}, self.config
        )
        availability = {result.name: result.available for result in results}
        self.assertTrue(availability["project_workspace"])
        self.assertTrue(availability["vector_acquisition"])
        self.assertFalse(availability["terrain_hydrology"])
        self.assertFalse(availability["lidar_terrain_processing"])

    def test_advanced_with_extensions_gets_full_matrix(self):
        results = evaluate_capabilities(
            "Advanced", {"Spatial": "Available", "3D": "Available", "ImageAnalyst": "Available"}, self.config
        )
        self.assertTrue(all(result.available for result in results))

    def test_standard_with_spatial_enables_hydrology(self):
        results = evaluate_capabilities(
            "Standard", {"Spatial": "Available", "3D": "Unavailable", "ImageAnalyst": "Unavailable"}, self.config
        )
        availability = {result.name: result.available for result in results}
        self.assertTrue(availability["terrain_hydrology"])
        self.assertFalse(availability["lidar_terrain_processing"])

    def test_unknown_license_fails_closed(self):
        results = evaluate_capabilities("NotInitialized", {}, self.config)
        self.assertTrue(all(not result.available and result.status == "FAIL" for result in results))
