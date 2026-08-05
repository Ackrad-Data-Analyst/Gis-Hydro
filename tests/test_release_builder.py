import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_manager_release import build_release


class ReleaseBuilderTests(unittest.TestCase):
    def test_toolbox_launcher_explains_that_zip_must_be_extracted(self):
        launcher = Path("tools/Open Site Hydrology Toolbox.cmd").read_text(encoding="utf-8")
        self.assertIn('Click "Extract all"', launcher)
        self.assertIn("Open the extracted Gis-Hydro folder", launcher)
        self.assertIn("if not exist \"%TOOLBOX%\"", launcher)

    def test_windows_launcher_uses_arcgis_python_and_checks_the_zip(self):
        launcher = Path("tools/Build Manager Package.cmd").read_text(encoding="utf-8")
        self.assertIn("ArcGIS\\Pro\\bin\\Python\\Scripts\\propy.bat", launcher)
        self.assertIn("build_manager_release.py", launcher)
        self.assertIn("if errorlevel 1", launcher)
        self.assertIn("Gis-Hydro_Manager_Release_Adolfo_Espino.zip", launcher)

    def test_personalized_pdf_and_clean_zip_are_created(self):
        with tempfile.TemporaryDirectory() as folder:
            message, pdf, feedback_message, feedback_pdf, archive_path = build_release(
                "Manager Example", "Author Example", Path(folder)
            )
            self.assertIn("Hi Manager Example", message.read_text(encoding="utf-8"))
            self.assertIn("Author Example", message.read_text(encoding="utf-8"))
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF-1.4"))
            self.assertIn("Hi Manager Example", feedback_message.read_text(encoding="utf-8"))
            self.assertIn("Author Example", feedback_message.read_text(encoding="utf-8"))
            self.assertTrue(feedback_pdf.read_bytes().startswith(b"%PDF-1.4"))
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIn("Gis-Hydro/Manager_Submission.pdf", names)
                self.assertIn("Gis-Hydro/Feedback_Response.pdf", names)
                self.assertIn("Gis-Hydro/RELEASE_SHA256.txt", names)
                self.assertIn("Gis-Hydro/toolboxes/site_hydrology_workflow.pyt", names)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any(name.startswith("Gis-Hydro/outputs/") for name in names))


if __name__ == "__main__":
    unittest.main()
