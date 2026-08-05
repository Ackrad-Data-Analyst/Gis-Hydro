import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.authoritative_acquisition import acquire_catalog_sources, stage_existing_map_sources


class _Management:
    def __init__(self, owner): self.owner = owner
    def MakeFeatureLayer(self, url, name, where): self.owner.layers.add(name)
    def MakeImageServerLayer(self, url, name, where_clause=None):
        self.owner.layers.add(name); self.owner.image_filters[name] = where_clause
    def SelectLayerByLocation(self, *args, **kwargs): return None
    def Clip(self, url, rectangle, output, *args):
        Path(output).write_bytes(b"synthetic raster")
        self.owner.clip_cell_sizes.append(getattr(self.owner.env, "cellSize", None))
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
        self.layers, self.outputs, self.image_filters = set(), set(), {}
        self.env = types.SimpleNamespace(cellSize=None)
        self.clip_cell_sizes = []
        self.management, self.conversion, self.analysis = _Management(self), _Conversion(self), _Analysis(self)
    def Exists(self, value): return value == "boundary" or value in self.layers or value in self.outputs
    def Describe(self, value):
        return types.SimpleNamespace(
            extent=types.SimpleNamespace(XMin=0, YMin=0, XMax=10, YMax=10),
            spatialReference=types.SimpleNamespace(name="Synthetic CRS"), meanCellWidth=1, meanCellHeight=1,
            dataType="RasterDataset" if "dem" in str(value).lower() else "FeatureClass",
        )



class _SizeLimitedManagement(_Management):
    def Clip(self, url, rectangle, output, *args):
        if getattr(self.owner.env, "cellSize", None) is None:
            raise RuntimeError("Cannot process above the size limits of the image service")
        super().Clip(url, rectangle, output, *args)


class _SizeLimitedArcPy(_ArcPy):
    def __init__(self):
        super().__init__()
        self.management = _SizeLimitedManagement(self)

    def Describe(self, value):
        if value == "boundary":
            return types.SimpleNamespace(
                extent=types.SimpleNamespace(XMin=0, YMin=0, XMax=100000, YMax=100000),
                spatialReference=types.SimpleNamespace(name="Synthetic CRS"),
                meanCellWidth=1, meanCellHeight=1, dataType="FeatureClass",
            )
        return types.SimpleNamespace(
            extent=types.SimpleNamespace(XMin=0, YMin=0, XMax=100000, YMax=100000),
            spatialReference=types.SimpleNamespace(name="Synthetic CRS"),
            meanCellWidth=1, meanCellHeight=1, dataType="RasterDataset",
        )


class _SelectiveFailureManagement(_Management):
    def Clip(self, url, rectangle, output, *args):
        if "bad_land_cover" in str(url):
            raise RuntimeError("Synthetic land-cover service outage")
        super().Clip(url, rectangle, output, *args)


class _SelectiveFailureArcPy(_ArcPy):
    def __init__(self):
        super().__init__()
        self.management = _SelectiveFailureManagement(self)

    def Describe(self, value):
        return types.SimpleNamespace(
            extent=types.SimpleNamespace(XMin=0, YMin=0, XMax=10, YMax=10),
            spatialReference=types.SimpleNamespace(name="Synthetic CRS"),
            meanCellWidth=1, meanCellHeight=1,
            dataType="RasterDataset" if "dem" in str(value).lower() or "land_cover" in str(value).lower() else "FeatureClass",
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

    def test_raster_filter_is_applied_to_image_service_layer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root); adapter = _ArcPy()
            source = _source("Annual_Land_Cover", "extract")
            source["filter"] = "Year=2024"
            acquire_catalog_sources(root, [source], adapter)
            self.assertEqual(adapter.image_filters["Annual_Land_Cover_filtered_image"], "Year=2024")

    def test_existing_success_is_reused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            source = _source("Existing", "extract")
            adapter = _ArcPy()
            first = acquire_catalog_sources(root, [source], adapter)[0]
            original_bytes = Path(first.original_output).read_bytes()
            second = acquire_catalog_sources(root, [source], adapter)[0]
            self.assertEqual(first, second)
            self.assertEqual(Path(first.original_output).read_bytes(), original_bytes)
            self.assertFalse(list((root / "data" / "original" / "authoritative").glob("Existing_retry_*")))

    def test_failed_attempt_gets_new_retry_folder_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            source = _source("Retry_Me", "unsupported")
            first = acquire_catalog_sources(root, [source], _ArcPy())[0]
            self.assertEqual(first.status, "FAIL")
            first_record = Path(root / "data" / "original" / "authoritative" / "Retry_Me" / "acquisition_record.json")
            first_bytes = first_record.read_bytes()
            second = acquire_catalog_sources(root, [source], _ArcPy())[0]
            self.assertEqual(second.status, "FAIL")
            self.assertEqual(first_record.read_bytes(), first_bytes)
            self.assertEqual(len(list(first_record.parent.parent.glob("Retry_Me_retry_*"))), 1)

    def test_vector_original_uses_geojson_extension(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            result = acquire_catalog_sources(root, [_source("Vector", "spatial_query_clip")], _ArcPy())[0]
            self.assertEqual(Path(result.original_output).suffix, ".geojson")

    def test_existing_map_layers_replace_network_acquisition_with_snapshots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            adapter = _ArcPy()
            results = stage_existing_map_sources(
                root, {"USGS_3DEP_DEM": "approved_dem", "ESRI_Transportation_Roads_Railroads": "approved_roads"}, adapter
            )
            self.assertEqual(len(results), 2)
            self.assertTrue(all(item.operation == "snapshot_from_map" for item in results))
            self.assertTrue(all(item.status == "REVIEW" for item in results))
            self.assertTrue(Path(results[0].original_output).is_file())
            self.assertTrue(results[0].sha256)
            self.assertEqual(len(list((root / "qa_qc").glob("acquisition_manifest_*.json"))), 1)

    def test_existing_map_raster_uses_adaptive_cell_size_for_large_image_services(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            adapter = _SizeLimitedArcPy()
            result = stage_existing_map_sources(root, {"USGS_3DEP_DEM": "approved_dem"}, adapter)[0]
            self.assertEqual(result.status, "REVIEW")
            self.assertTrue(Path(result.original_output).is_file())
            self.assertTrue(adapter.clip_cell_sizes[0])
            self.assertIn("service row/column limits", result.message)

    def test_catalog_raster_uses_adaptive_cell_size_for_large_image_services(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            adapter = _SizeLimitedArcPy()
            result = acquire_catalog_sources(root, [_source("USGS_3DEP_DEM", "extract")], adapter)[0]
            self.assertEqual(result.status, "REVIEW")
            self.assertTrue(Path(result.original_output).is_file())
            self.assertTrue(adapter.clip_cell_sizes[0])
            self.assertIn("service row/column limits", result.message)

    def test_existing_map_optional_layer_failure_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "site"; _project(root)
            adapter = _SelectiveFailureArcPy()
            results = stage_existing_map_sources(
                root, {"USGS_3DEP_DEM": "approved_dem", "NLCD_Land_Cover": "bad_land_cover"}, adapter
            )
            by_name = {item.source_name: item for item in results}
            self.assertEqual(by_name["USGS_3DEP_DEM"].status, "REVIEW")
            self.assertEqual(by_name["NLCD_Land_Cover"].status, "FAIL")
            self.assertIn("Existing map layer snapshot failed", by_name["NLCD_Land_Cover"].message)


if __name__ == "__main__":
    unittest.main()
