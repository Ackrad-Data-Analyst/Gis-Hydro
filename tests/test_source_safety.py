import csv, json, tempfile, unittest
from pathlib import Path
from hydro_workflow.cli import build_parser, run_inventory
from hydro_workflow.file_inventory import hash_file
from hydro_workflow.project_setup import validate_paths
from helpers import make_kmz

CONFIG = Path(__file__).parents[1] / 'config'

class SourceSafetyTests(unittest.TestCase):
    def args(self, source, output, dry=False):
        values=['inventory','--project-folder',str(source),'--project-name','Synthetic','--config',str(CONFIG),'--output-folder',str(output)]
        if dry: values.append('--dry-run')
        return build_parser().parse_args(values)
    def test_output_inside_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError): validate_paths(root,root/'outputs')
    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source'; source.mkdir(); (source/'mystery.xyz').write_text('x'); output=root/'out'
            summary=run_inventory(self.args(source,output,True))
            self.assertTrue(summary['dry_run']); self.assertFalse(output.exists())
    def test_reports_columns_output_creation_and_hash_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source'; source.mkdir(); output=root/'reports'
            target=make_kmz(source/'synthetic_project_boundary.kmz'); before=hash_file(target)
            summary=run_inventory(self.args(source,output))
            self.assertEqual(before,hash_file(target)); self.assertTrue(summary['integrity_confirmed'])
            expected={'file_inventory.csv','source_register.csv','data_gap_report.csv','project_summary.json','source_integrity_report.json','inventory_run.log'}
            self.assertTrue(expected.issubset({p.name for p in output.iterdir()}))
            with (output/'file_inventory.csv').open(newline='') as stream:
                self.assertTrue({'file_name','sha256','file_status','kmz_details'}.issubset(csv.DictReader(stream).fieldnames))
            integrity=json.loads((output/'source_integrity_report.json').read_text())
            self.assertEqual(integrity['source_changes_expected'],0); self.assertTrue(integrity['integrity_confirmed'])
