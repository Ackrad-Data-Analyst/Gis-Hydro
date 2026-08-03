import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.boundary_validation import (
    import_and_validate_boundary,
    import_kml_boundary,
    prepare_kml_boundary_candidates,
)


class _Result:
    def __init__(self, value): self.value = value
    def __getitem__(self, index): return str(self.value)


class _Management:
    def __init__(self, owner): self.owner = owner
    def GetCount(self, value): return _Result(self.owner.counts.get(value, 0))
    def CheckGeometry(self, source, output): self.owner.counts[output] = self.owner.geometry_errors
    def CopyFeatures(self, source, output): self.owner.created.add(output)
    def Project(self, source, output, spatial_reference): self.owner.created.add(output)
    def MakeFeatureLayer(self, source, output, where_clause=None):
        self.owner.created.add(output)
        self.owner.counts[output] = self.owner.selected_count


class _ArcPy:
    def __init__(self, source, geometry="Polygon", count=1, geometry_errors=0, selected_count=1):
        self.source = source
        self.created = set()
        self.counts = {source: count}
        self.geometry_errors = geometry_errors
        self.selected_count = selected_count
        self.management = _Management(self)
        self.conversion = types.SimpleNamespace(KMLToLayer=self._kml_to_layer)
    def _kml_to_layer(self, source, output_folder, output_name, *args):
        output_gdb = str(Path(output_folder) / f"{output_name}.gdb")
        self.created.add(output_gdb)
        self.created.add(str(Path(output_gdb) / "Placemarks" / "Polygons"))
    def Exists(self, value): return value == self.source or value in self.created
    def Describe(self, value):
        return types.SimpleNamespace(
            shapeType="Polygon" if value == self.source or value in self.created else "Table",
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
    def test_kmz_named_boundary_is_converted_selected_and_imported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            (root / "intake").mkdir()
            source = Path(temp) / "project_and_row.kmz"
            source.write_bytes(b"synthetic kmz fixture")
            adapter = _ArcPy(str(source))

            candidates, validation = import_kml_boundary(
                source, root, adapter, "Project Boundary"
            )

            self.assertEqual(candidates.status, "REVIEW")
            self.assertEqual(validation.status, "PASS")
            self.assertTrue(validation.imported_boundary.endswith("project_boundary"))

    def test_kmz_import_requires_name_and_rejects_no_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            (root / "intake").mkdir()
            source = Path(temp) / "project_and_row.kmz"
            source.write_bytes(b"synthetic kmz fixture")
            with self.assertRaisesRegex(ValueError, "Boundary Name Contains is required"):
                import_kml_boundary(source, root, _ArcPy(str(source)), "")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            (root / "intake").mkdir()
            source = Path(temp) / "project_and_row.kmz"
            source.write_bytes(b"synthetic kmz fixture")
            with self.assertRaisesRegex(ValueError, "No KML/KMZ polygon"):
                import_kml_boundary(source, root, _ArcPy(str(source), selected_count=0), "Missing")

    def test_kmz_is_converted_read_only_and_requires_candidate_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            (root / "intake").mkdir()
            source = Path(temp) / "synthetic_project_and_row.kmz"
            source.write_bytes(b"synthetic kmz fixture")
            before = source.read_bytes()
            adapter = _ArcPy(str(source))

            result = prepare_kml_boundary_candidates(source, root, adapter)

            self.assertEqual(result.status, "REVIEW")
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(result.polygon_candidates), 1)
            self.assertIn("rights-of-way", result.review_notes)
            self.assertTrue((root / "qa_qc" / "boundary_candidate_conversion.json").is_file())

    def test_kmz_candidates_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            candidates = root / "intake" / "boundary_candidates"
            candidates.mkdir(parents=True)
            marker = candidates / "keep.txt"
            marker.write_text("do not overwrite")
            source = Path(temp) / "boundary.kmz"
            source.write_bytes(b"synthetic kmz fixture")

            with self.assertRaises(FileExistsError):
                prepare_kml_boundary_candidates(source, root, _ArcPy(str(source)))
            self.assertEqual(marker.read_text(), "do not overwrite")

    def test_matching_kmz_conversion_is_resumed_after_selection_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"
            _workspace(root)
            (root / "intake").mkdir()
            source = Path(temp) / "boundary.kmz"
            source.write_bytes(b"synthetic kmz fixture")
            adapter = _ArcPy(str(source))
            first = prepare_kml_boundary_candidates(source, root, adapter)

            resumed = prepare_kml_boundary_candidates(source, root, adapter)

            self.assertEqual(resumed.source_sha256, first.source_sha256)
            self.assertEqual(resumed.polygon_candidates, first.polygon_candidates)

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
