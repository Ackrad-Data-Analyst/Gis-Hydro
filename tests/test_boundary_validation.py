import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.boundary_validation import import_and_validate_boundary


class _Result:
    def __init__(self, value): self.value = value
    def __getitem__(self, index): return str(self.value)


class _Management:
    def __init__(self, owner): self.owner = owner
    def GetCount(self, value): return _Result(self.owner.counts.get(value, 0))
    def CheckGeometry(self, source, output): self.owner.counts[output] = self.owner.geometry_errors
    def CopyFeatures(self, source, output): self.owner.created.add(output)
    def Project(self, source, output, spatial_reference): self.owner.created.add(output)


class _ArcPy:
    def __init__(self, source, geometry="Polygon", count=1, geometry_errors=0):
        self.source = source
        self.created = set()
        self.counts = {source: count}
        self.geometry_errors = geometry_errors
        self.management = _Management(self)
    def Exists(self, value): return value == self.source or value in self.created
    def Describe(self, value):
        return types.SimpleNamespace(
            shapeType="Polygon" if value == self.source else "Table",
            spatialReference=types.SimpleNamespace(name="WGS 1984", type="Geographic", factoryCode=4326),
            extent=types.SimpleNamespace(XMin=-112, YMin=33, XMax=-111, YMax=34),
        )


def _workspace(root):
    gdb = root / "gis" / "site_hydrology.gdb"
    gdb.mkdir(parents=True)
    qa = root / "qa_qc"
    qa.mkdir()
    (qa / "workspace_manifest.json").write_text(json.dumps({"geodatabase": str(gdb)}))


class BoundaryValidationTests(unittest.TestCase):
    def test_polygon_is_copied_and_reported_without_source_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            source = Path(temp) / "boundary.geojson"
            source.write_text("synthetic boundary")
            before = source.read_bytes()
            adapter = _ArcPy(str(source))

            result = import_and_validate_boundary(str(source), root, adapter)

            self.assertEqual(result.status, "PASS")
            self.assertEqual(result.feature_count, 1)
            self.assertIsNotNone(result.source_sha256)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue((root / "qa_qc" / "boundary_validation.json").is_file())

    def test_geometry_errors_stop_import_without_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            source = str(Path(temp) / "boundary.shp")
            adapter = _ArcPy(source, geometry_errors=2)

            with self.assertRaisesRegex(ValueError, "2 geometry error"):
                import_and_validate_boundary(source, root, adapter)

            self.assertFalse(any(value.endswith("project_boundary") for value in adapter.created))

    def test_non_polygon_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            source = "synthetic_lines"
            adapter = _ArcPy(source)
            adapter.Describe = lambda value: types.SimpleNamespace(shapeType="Polyline")
            with self.assertRaisesRegex(ValueError, "must be polygon"):
                import_and_validate_boundary(source, root, adapter)


if __name__ == "__main__":
    unittest.main()
