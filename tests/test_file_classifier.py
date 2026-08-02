import unittest
from pathlib import Path, PureWindowsPath
from hydro_workflow.file_classifier import FileClassifier, load_json_yaml, suffix_for_name

CONFIG = Path(__file__).parents[1] / "config" / "file_classification.yaml"

class ClassifierTests(unittest.TestCase):
    def setUp(self): self.classifier = FileClassifier.from_file(CONFIG)
    def test_configuration_loads(self):
        self.assertGreater(len(load_json_yaml(CONFIG)["rules"]), 20)
    def test_known_file_classifies(self):
        result = self.classifier.classify(Path("cygnus_boundary.kmz"))
        self.assertEqual((result.category, result.status), ("Project boundary", "PASS"))
    def test_unknown_extension_is_review(self):
        result = self.classifier.classify(Path("mystery.xyz"))
        self.assertEqual((result.category, result.status), ("Unknown", "REVIEW"))
    def test_windows_style_path_suffix(self):
        value = r"C:\\Projects\\Cygnus\\site_DEM.TIFF"
        self.assertEqual(suffix_for_name(value), ".tiff")
        self.assertEqual(PureWindowsPath(value).name, "site_DEM.TIFF")
    def test_keyword_substring_does_not_pass(self):
        result = self.classifier.classify(Path("confirmation.pdf"))
        self.assertNotEqual((result.category, result.status), ("FEMA flood information", "PASS"))
    def test_configured_threshold_is_enforced(self):
        config = load_json_yaml(CONFIG)
        config["confidence_threshold"] = 0.99
        result = FileClassifier(config).classify(Path("site_boundary.kmz"))
        self.assertEqual((result.confidence, result.status), (0.95, "REVIEW"))
