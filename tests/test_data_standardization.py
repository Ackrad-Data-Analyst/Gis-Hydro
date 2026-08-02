import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.data_standardization import validate_standardize_data


class _Management:
    def __init__(self, owner): self.owner = owner
    def GetCount(self, value): return ["4"]
    def Project(self, source, output, crs): self.owner.outputs.add(output)
    def ProjectRaster(self, source, output, crs, resampling): self.owner.outputs.add(output)


class _ArcPy:
    def __init__(self):
        self.outputs = set()
        self.management = _Management(self)
    def Exists(self, value): return value in {"boundary", "vector", "raster"} or value in self.outputs
    def Describe(self, value):
        extent = types.SimpleNamespace(XMin=0, YMin=0, XMax=10, YMax=10)
        if value == "raster":
            return types.SimpleNamespace(dataType="RasterDataset", extent=extent,
                spatialReference=types.SimpleNamespace(name="Source CRS"), height=10, width=10,
                meanCellWidth=1, meanCellHeight=1)
        return types.SimpleNamespace(dataType="FeatureClass", extent=extent,
            spatialReference=types.SimpleNamespace(name="Source CRS"))


class _MixedCrsArcPy(_ArcPy):
    def Describe(self, value):
        if value in {"vector", "raster"}:
            extent = types.SimpleNamespace(XMin=-112, YMin=33, XMax=-111, YMax=34)
            if value == "raster":
                return types.SimpleNamespace(dataType="RasterDataset", extent=extent,
                    spatialReference=types.SimpleNamespace(name="Native Geographic CRS"), height=10,
                    width=10, meanCellWidth=0.1, meanCellHeight=0.1)
            return types.SimpleNamespace(dataType="FeatureClass", extent=extent,
                spatialReference=types.SimpleNamespace(name="Native Geographic CRS"))
        return super().Describe(value)


def _project(root):
    gdb = root / "gis" / "site_hydrology.gdb"; gdb.mkdir(parents=True)
    qa = root / "qa_qc"; qa.mkdir()
    (qa / "workspace_manifest.json").write_text(json.dumps({"geodatabase": str(gdb)}))
    (qa / "boundary_validation.json").write_text(json.dumps({"imported_boundary": "boundary"}))
    records = [
        {"source_name": "Roads", "working_output": "vector", "status": "REVIEW",
         "query_parameters": {"resampling": "VECTOR"}},
        {"source_name": "Elevation", "working_output": "raster", "status": "REVIEW",
         "query_parameters": {"resampling": "BILINEAR"}},
    ]
    (qa / "acquisition_manifest_test.json").write_text(json.dumps(records))


class DataStandardizationTests(unittest.TestCase):
    def test_vector_and_raster_are_projected_and_metrics_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            target = types.SimpleNamespace(name="Approved Project CRS")
            results = validate_standardize_data(root, target, _ArcPy())
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].feature_count, 4)
            self.assertEqual(results[1].rows, 10)
            self.assertEqual(results[1].native_cell_width, 1.0)
            self.assertEqual(results[0].extent_coverage_percent, 100.0)
            self.assertTrue(all(result.status == "REVIEW" for result in results))
            self.assertTrue((root / "qa_qc" / "data_standardization_report.json").is_file())

    def test_unknown_target_crs_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            with self.assertRaisesRegex(ValueError, "known target"):
                validate_standardize_data(root, types.SimpleNamespace(name="Unknown"), _ArcPy())

    def test_coverage_uses_projected_output_extent_not_native_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            results = validate_standardize_data(
                root, types.SimpleNamespace(name="Approved Project CRS"), _MixedCrsArcPy()
            )
            self.assertTrue(all(result.extent_coverage_percent == 100.0 for result in results))


if __name__ == "__main__":
    unittest.main()
