import json
import tempfile
import unittest
from pathlib import Path

from hydro_workflow.terrain_hydrology import prepare_terrain_hydrology


class _Raster:
    def __init__(self, owner): self.owner = owner
    def save(self, output): self.owner.outputs.add(output)
    def __ge__(self, other): return self


class _SA:
    def __init__(self, owner): self.owner = owner
    def Fill(self, value): return _Raster(self.owner)
    def FlowDirection(self, *args): return _Raster(self.owner)
    def FlowAccumulation(self, *args): return _Raster(self.owner)
    def Con(self, *args): return _Raster(self.owner)
    def StreamToFeature(self, stream, flow, output, simplify): self.owner.outputs.add(output)
    def SnapPourPoint(self, *args): return _Raster(self.owner)
    def Watershed(self, *args): return _Raster(self.owner)


class _Management:
    def GetRasterProperties(self, raster, name): return ["1" if name == "ANYNODATA" else "0"]


class _ArcPy:
    def __init__(self, extension="Available"):
        self.extension, self.outputs, self.checked_in = extension, set(), False
        self.sa, self.management = _SA(self), _Management()
    def Exists(self, value): return value == "dem" or value in self.outputs
    def CheckExtension(self, name): return self.extension
    def CheckOutExtension(self, name): return None
    def CheckInExtension(self, name): self.checked_in = True


def _project(root):
    gdb = root / "gis" / "site_hydrology.gdb"; gdb.mkdir(parents=True)
    qa = root / "qa_qc"; qa.mkdir()
    (qa / "workspace_manifest.json").write_text(json.dumps({"geodatabase": str(gdb)}))


class TerrainHydrologyTests(unittest.TestCase):
    def test_full_spatial_workflow_uses_explicit_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root); adapter = _ArcPy()
            result = prepare_terrain_hydrology(root, "dem", 5000, True, adapter, "pour_points", 30.0)
            self.assertEqual(result.stream_threshold_cells, 5000)
            self.assertEqual(result.snap_distance, 30.0)
            self.assertIsNotNone(result.watersheds)
            self.assertTrue(adapter.checked_in)
            self.assertTrue((root / "qa_qc" / "terrain_hydrology_report.json").is_file())

    def test_missing_spatial_analyst_stops_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            with self.assertRaisesRegex(RuntimeError, "Spatial Analyst"):
                prepare_terrain_hydrology(root, "dem", 100, False, _ArcPy("NotLicensed"))

    def test_engineering_parameters_are_not_invented(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            with self.assertRaisesRegex(ValueError, "positive"):
                prepare_terrain_hydrology(root, "dem", 0, False, _ArcPy())
            with self.assertRaisesRegex(ValueError, "snap distance"):
                prepare_terrain_hydrology(root, "dem", 100, False, _ArcPy(), "pour_points", None)


if __name__ == "__main__":
    unittest.main()
