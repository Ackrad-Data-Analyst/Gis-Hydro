import csv
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from helpers import make_kmz
from hydro_workflow.cli import run_acquisition_plan
from hydro_workflow.source_catalog import build_acquisition_plan, load_source_catalog

CONFIG = Path(__file__).parents[1] / "config"


class SourceCatalogTests(unittest.TestCase):
    def test_manager_catalog_loads(self):
        sources = load_source_catalog(CONFIG / "authoritative_sources.yaml")
        self.assertEqual(len(sources), 9)
        roads = next(source for source in sources if source["name"] == "ESRI_Transportation_Roads_Railroads")
        self.assertEqual(roads["category"], "Roads and railroads")
        self.assertTrue(roads["rest_url"].endswith("/Transportation_v1/FeatureServer"))
        self.assertEqual(
            {source["source_agency"] for source in sources},
            {"USGS", "ESRI Federal Data", "FEMA", "USDA NRCS"},
        )

    def test_plan_is_site_agnostic_and_review_required(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = make_kmz(Path(folder) / "any_site_boundary.kmz")
            records = build_acquisition_plan("Any Site 101", boundary, load_source_catalog(CONFIG / "authoritative_sources.yaml"))
            self.assertEqual(len(records), 9)
            self.assertTrue(all(record.project_name == "Any Site 101" for record in records))
            self.assertTrue(all(record.plan_status == "REVIEW" for record in records))
            self.assertIsNotNone(records[0].boundary_west)

    def test_plan_reports_are_created_without_downloading(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"; source.mkdir()
            boundary = make_kmz(source / "boundary.kmz")
            output = root / "outputs"
            summary = run_acquisition_plan(Namespace(
                boundary=boundary, project_name="Generic Site", config=CONFIG,
                output_folder=output, dry_run=False,
            ))
            self.assertEqual(summary["source_count"], 9)
            self.assertTrue((output / "data_acquisition_plan.csv").is_file())
            self.assertTrue((output / "data_acquisition_plan.json").is_file())
            with (output / "data_acquisition_plan.csv").open(newline="", encoding="utf-8") as stream:
                self.assertIn("rest_url", csv.DictReader(stream).fieldnames)
            payload = json.loads((output / "data_acquisition_plan.json").read_text())
            self.assertEqual(len(payload["sources"]), 9)
            self.assertFalse(any(output.rglob("*.tif")))

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "source"; source.mkdir()
            boundary = make_kmz(source / "boundary.kmz"); output = root / "outputs"
            summary = run_acquisition_plan(Namespace(
                boundary=boundary, project_name="Generic Site", config=CONFIG,
                output_folder=output, dry_run=True,
            ))
            self.assertTrue(summary["dry_run"])
            self.assertFalse(output.exists())

    def test_plan_output_may_be_beside_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            boundary = make_kmz(root / "boundary.kmz")
            output = root / "acquisition_plan"
            summary = run_acquisition_plan(Namespace(
                boundary=boundary, project_name="Generic Site", config=CONFIG,
                output_folder=output, dry_run=False,
            ))
            self.assertEqual(summary["source_count"], 9)
            self.assertTrue((output / "data_acquisition_plan.json").is_file())
