import tempfile, unittest
from pathlib import Path
from hydro_workflow.kmz_inspector import inspect_kmz, list_kml_polygon_names
from helpers import make_kmz

class KmzTests(unittest.TestCase):
    def test_valid_kmz(self):
        with tempfile.TemporaryDirectory() as folder:
            result = inspect_kmz(make_kmz(Path(folder) / "boundary.kmz"))
            self.assertTrue(result["valid_kmz"])
            self.assertEqual(result["placemark_count"], 1)
            self.assertEqual(result["approximate_bounds"]["west"], -112.0)
            self.assertEqual(list_kml_polygon_names(Path(folder) / "boundary.kmz"), ["Synthetic boundary"])
    def test_invalid_kmz(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.kmz"; path.write_text("not a zip")
            result = inspect_kmz(path)
            self.assertFalse(result["valid_kmz"])
            self.assertTrue(result["error"])
