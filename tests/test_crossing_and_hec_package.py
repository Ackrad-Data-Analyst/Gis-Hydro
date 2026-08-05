import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.crossing_screening import screen_crossings
from hydro_workflow.hec_ras_package import build_hec_ras_review_package
from hydro_workflow.qa_package import generate_qa_package


class _Management:
    def __init__(self, owner): self.owner = owner
    def GetCount(self, value): return ["3"]
    def CopyFeatures(self, source, output): self.owner.outputs.add(output)
    def Merge(self, sources, output): self.owner.outputs.add(output)
    def CopyRaster(self, source, output): Path(output).write_bytes(b"terrain")


class _Analysis:
    def __init__(self, owner): self.owner = owner
    def Intersect(self, inputs, output, *args): self.owner.outputs.add(output)
    def SpatialJoin(self, target, join, output, *args): self.owner.outputs.add(output)


class _Conversion:
    def FeaturesToJSON(self, source, output, *args):
        if source == "response_raster":
            raise RuntimeError("not a feature class")
        Path(output).write_text('{"type":"FeatureCollection"}')


class _ArcPy:
    def __init__(self):
        self.outputs = set(); self.management = _Management(self); self.analysis = _Analysis(self); self.conversion = _Conversion()
    def Exists(self, value): return value in {"roads", "drainage", "bridges", "culverts", "terrain", "streams", "response_raster"} or value in self.outputs
    def Describe(self, value):
        return types.SimpleNamespace(spatialReference=types.SimpleNamespace(exportToString=lambda: "SYNTHETIC_WKT"))


def _project(root):
    gdb = root / "gis" / "site_hydrology.gdb"; gdb.mkdir(parents=True)
    qa = root / "qa_qc"; qa.mkdir()
    (root / "hec_ras_inputs").mkdir()
    (qa / "workspace_manifest.json").write_text(json.dumps({"geodatabase": str(gdb), "status": "REVIEW"}))


class CrossingAndHecTests(unittest.TestCase):
    def test_crossings_keep_known_structure_review_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            result = screen_crossings(root, "roads", "drainage", _ArcPy(), "bridges", "culverts", "50 Meters")
            self.assertEqual(result.potential_crossing_count, 3)
            self.assertIn("not invented", result.review_notes)
            self.assertTrue((root / "qa_qc" / "crossing_screening_report.json").is_file())

    def test_structure_distance_is_never_invented(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            with self.assertRaisesRegex(ValueError, "search distance"):
                screen_crossings(root, "roads", "drainage", _ArcPy(), bridges="bridges")

    def test_hec_review_package_contains_terrain_projection_layers_and_qa(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            result = build_hec_ras_review_package(root, "terrain", _ArcPy(),
                {"stream_centerlines": "streams", "bank_lines": None, "cross_sections": None})
            self.assertTrue(Path(result.terrain).is_file())
            self.assertTrue(Path(result.projection_file).is_file())
            self.assertIn("bank_lines", result.missing_optional_inputs)
            self.assertIn("not invented", result.review_notes)
            json_path, csv_path = generate_qa_package(root)
            self.assertTrue(json_path.is_file()); self.assertTrue(csv_path.is_file())

    def test_hec_review_package_copies_raster_layers_without_failing_feature_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            result = build_hec_ras_review_package(
                root, "terrain", _ArcPy(), {"land_cover": "response_raster"}
            )
            self.assertTrue((Path(result.package_root) / "rasters" / "land_cover.tif").is_file())
            self.assertIn("land_cover", result.copied_layers)
            self.assertIn("land_cover_vector_export_review_required", result.missing_optional_inputs)

    def test_hec_review_package_uses_new_folder_when_previous_package_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            first = build_hec_ras_review_package(root, "terrain", _ArcPy(), {})
            second = build_hec_ras_review_package(root, "terrain", _ArcPy(), {})
            self.assertNotEqual(first.package_root, second.package_root)
            self.assertTrue(second.package_root.endswith("preliminary_review_package_2"))


if __name__ == "__main__": unittest.main()
