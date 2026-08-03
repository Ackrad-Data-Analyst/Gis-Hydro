import json
import tempfile
import unittest
from pathlib import Path

from hydro_workflow.project_workspace import PROJECT_FOLDERS, create_project_workspace, safe_project_id


class _Management:
    @staticmethod
    def CreateFileGDB(out_folder_path, out_name):
        (Path(out_folder_path) / out_name).mkdir()


class _ArcPy:
    management = _Management()


class ProjectWorkspaceTests(unittest.TestCase):
    def test_safe_project_id(self):
        self.assertEqual(safe_project_id("Arizona Site 04"), "Arizona_Site_04")
        with self.assertRaises(ValueError):
            safe_project_id("---")

    def test_workspace_is_complete_and_manifested(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp) / "projects"
            manifest = create_project_workspace("Arizona Site 04", output_root, _ArcPy())
            project_root = output_root / "Arizona_Site_04"

            for relative in PROJECT_FOLDERS:
                self.assertTrue((project_root / relative).is_dir())
            self.assertTrue(Path(manifest.geodatabase).is_dir())
            saved = json.loads((project_root / "qa_qc" / "workspace_manifest.json").read_text())
            self.assertEqual(saved["project_name"], "Arizona Site 04")
            self.assertFalse(saved["overwrite_allowed"])
            self.assertIn("REVIEW REQUIRED", saved["engineering_notice"])

    def test_existing_project_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp)
            existing = output_root / "Existing_Site"
            existing.mkdir()
            sentinel = existing / "do_not_change.txt"
            sentinel.write_text("original")

            with self.assertRaises(FileExistsError):
                create_project_workspace("Existing Site", output_root, _ArcPy())

            self.assertEqual(sentinel.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
