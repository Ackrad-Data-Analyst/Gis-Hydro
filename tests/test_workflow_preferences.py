import json
import tempfile
import unittest
from pathlib import Path

from hydro_workflow.workflow_preferences import (
    conservative_soil_group,
    load_engineering_lookup,
    unit_preferences,
)


class WorkflowPreferenceTests(unittest.TestCase):
    def test_metric_and_imperial_preferences_are_explicit(self):
        self.assertEqual(unit_preferences("Imperial").area, "acres")
        self.assertEqual(unit_preferences("Metric").area, "hectares")
        with self.assertRaises(ValueError):
            unit_preferences("automatic")

    def test_dual_and_mixed_soil_groups_use_conservative_d(self):
        for value in ("A/D", "B/D", "C/D", "A-B", "A, C"):
            self.assertEqual(conservative_soil_group(value), "D")
        self.assertEqual(conservative_soil_group("C"), "C")
        self.assertEqual(conservative_soil_group(None), "UNKNOWN")

    def test_unapproved_engineering_constants_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lookup.json"
            path.write_text(json.dumps({"approval_status": "DRAFT"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "APPROVED"):
                load_engineering_lookup(path)


if __name__ == "__main__":
    unittest.main()
