import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.authoritative_acquisition import acquire_catalog_sources


class _Management:
    def __init__(self, owner): self.owner = owner
    def MakeFeatureLayer(self, url, name, where): self.owner.layers.add(name)
    def SelectLayerByLocation(self, *args, **kwargs): return None
    def Clip(self, url, rectangle, output, *args): Path(output).write_bytes(b"synthetic raster")
    def CopyRaster(self, source, output): self.owner.outputs.add(output)


class _Conversion:
    def __init__(self, owner): self.owner = owner
    def FeaturesToJSON(self, layer, output, *args): Path(output).write_text('{"type":"FeatureCollection"}')
    def JSONToFeatures(self, source, output): self.owner.outputs.add(output)


class _Analysis:
    def __init__(self, owner): self.owner = owner
    def Clip(self, source, boundary, output): self.owner.outputs.add(output)


class _ArcPy:
    def __init__(self):
        self.layers, self.outputs = set(), set()
        self.management, self.conversion, self.analysis = _Management(self), _Conversion(self), _Analysis(self)
    def Exists(self, value): return value == "boundary" or value in self.layers or value in self.outputs
    def Describe(self, value):
        return types.SimpleNamespace(
            extent=types.SimpleNamespace(XMin=0, YMin=0, XMax=10, YMax=10),
            spatialReference=types.SimpleNamespace(name="Synthetic CRS"), meanCellWidth=1, meanCellHeight=1,
        )


def _project(root):
    gdb = root / "gis" / "site_hydrology.gdb"; gdb.mkdir(parents=True)
    qa = root / "qa_qc"; qa.mkdir()
    (root / "data" / "original").mkdir(parents=True)
    (qa / "workspace_manifest.json").write_text(json.dumps({"geodatabase": str(gdb)}))
    (qa / "boundary_validation.json").write_text(json.dumps({"imported_boundary": "boundary"}))


def _source(name, operation):
    return {"name": name, "category": "Synthetic", "source_agency": "Synthetic Agency",
            "rest_url": f"https://example.test/{name}", "operation": operation,
            "filter": "1=1", "resampling": "VECTOR" if operation != "extract" else "BILINEAR"}


class AuthoritativeAcquisitionTests(unittest.TestCase):
    def test_unlimited_catalog_names_use_generic_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            sources = [_source(f"Source_{index}", "spatial_query_clip") for index in range(12)]
            results = acquire_catalog_sources(root, sources, _ArcPy())
            self.assertEqual(len(results), 12)
            self.assertTrue(all(result.status == "REVIEW" for result in results))
            self.assertTrue(all(result.sha256 for result in results))

    def test_vector_and_raster_outputs_are_hashed_and_manifested(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            results = acquire_catalog_sources(
                root, [_source("FEMA_like", "spatial_query_clip"), _source("DEM_like", "extract")], _ArcPy()
            )
            self.assertEqual([result.status for result in results], ["REVIEW", "REVIEW"])
            self.assertEqual(len(list((root / "qa_qc").glob("acquisition_manifest_*.json"))), 1)
            self.assertTrue(Path(results[0].original_output).is_file())
            self.assertTrue(Path(results[1].original_output).is_file())

    def test_existing_original_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            source = _source("Existing", "extract")
            acquire_catalog_sources(root, [source], _ArcPy())
            with self.assertRaises(FileExistsError):
                acquire_catalog_sources(root, [source], _ArcPy())


if __name__ == "__main__":
    unittest.main()
