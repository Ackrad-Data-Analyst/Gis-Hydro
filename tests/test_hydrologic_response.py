import json
import tempfile
import types
import unittest
from pathlib import Path

from hydro_workflow.hydrologic_response import combine_land_cover_soils


class _Raster:
    def __init__(self, adapter): self.adapter = adapter
    def save(self, output): self.adapter.existing.add(output)


class _ArcPy:
    def __init__(self, existing):
        self.existing = set(existing)
        self.sa = types.SimpleNamespace(Combine=lambda values: _Raster(self))
    def Exists(self, path): return path in self.existing
    def CheckExtension(self, name): return "Available"
    def CheckOutExtension(self, name): return
    def CheckInExtension(self, name): return


class HydrologicResponseTests(unittest.TestCase):
    def test_land_cover_and_soils_are_combined_and_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "qa_qc").mkdir()
            gdb = root / "gis.gdb"; gdb.mkdir()
            (root / "qa_qc" / "workspace_manifest.json").write_text(
                json.dumps({"geodatabase": str(gdb)}), encoding="utf-8"
            )
            adapter = _ArcPy({"land", "soil"})
            result = combine_land_cover_soils(root, "land", "soil", adapter)
            self.assertTrue(adapter.Exists(result.combined_raster))
            self.assertIn("REVIEW REQUIRED", result.review_notes)
            self.assertTrue((root / "qa_qc" / "hydrologic_response_report.json").is_file())


if __name__ == "__main__": unittest.main()
