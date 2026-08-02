import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from hydro_workflow.file_classifier import FileClassifier
from hydro_workflow.file_inventory import inventory_files
from helpers import make_kmz

CONFIG = Path(__file__).parents[1] / "config" / "file_classification.yaml"

class InventoryTests(unittest.TestCase):
    def setUp(self): self.classifier = FileClassifier.from_file(CONFIG)
    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(inventory_files(Path(folder), self.classifier)[0], [])
    def test_known_types_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'a').mkdir(); (root/'b').mkdir()
            (root/'a'/'site_dem.tif').write_bytes(b'dem'); (root/'b'/'site_dem.tif').write_bytes(b'dem2')
            (root/'soils.csv').write_text('synthetic')
            records,_=inventory_files(root,self.classifier)
            self.assertEqual(len(records),3)
            self.assertEqual(sum(r.file_name=='site_dem.tif' for r in records),2)
            self.assertEqual(sum(r.likely_category=='DEM' for r in records),2)
    def test_valid_and_invalid_kmz_are_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); make_kmz(root/'project_boundary.kmz'); (root/'bad.kmz').write_text('bad')
            records,_=inventory_files(root,self.classifier)
            self.assertEqual(len(records),2)
            self.assertIn('Invalid KMZ', next(r.review_notes for r in records if r.file_name=='bad.kmz'))
    def test_unreadable_file_fails_deterministically(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); target=root/'secret.pdf'; target.write_text('synthetic')
            from hydro_workflow import file_inventory
            original=file_inventory.hash_file
            with patch('hydro_workflow.file_inventory.hash_file', side_effect=lambda p: (_ for _ in ()).throw(PermissionError('denied')) if p==target else original(p)):
                records,_=inventory_files(root,self.classifier)
            self.assertEqual((records[0].is_readable, records[0].file_status),(False,'FAIL'))
