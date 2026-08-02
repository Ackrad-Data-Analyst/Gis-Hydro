import unittest
from pathlib import Path


class ManagerHandoffTests(unittest.TestCase):
    def test_quick_start_assets_and_launcher_are_present(self):
        root = Path(__file__).parents[1]
        guide = (root / "docs" / "manager_quick_start.md").read_text(encoding="utf-8")
        launcher = (root / "tools" / "Open Site Hydrology Toolbox.cmd").read_text(encoding="utf-8")

        for image_number in range(1, 5):
            image_name = next((root / "docs" / "images").glob(f"0{image_number}_*.svg"), None)
            self.assertIsNotNone(image_name)
            self.assertIn(f"images/{image_name.name}", guide)

        self.assertIn("site_hydrology_workflow.pyt", launcher)
        self.assertIn("ArcGISPro.exe", launcher)
        self.assertIn("does not need GitHub", guide)
        self.assertIn("notebook > section > page", guide)
        self.assertNotIn("github.com/Ackrad-Data-Analyst", guide)
        self.assertNotIn("pip install", guide)
        self.assertNotIn("```powershell", guide.lower())


if __name__ == "__main__":
    unittest.main()
