import unittest
from hydro_workflow.data_gap_checker import check_data_gaps
from hydro_workflow.models import InventoryRecord

def record(category="Project boundary", status="PASS"):
    return InventoryRecord("a.kmz","/a.kmz","a.kmz",".kmz",1,"",category,.95,"Unknown",status,"",True,"original","abc","")

class GapTests(unittest.TestCase):
    def test_missing_required_fails(self):
        gap = check_data_gaps([], [{"name":"DEM","required":True}])[0]
        self.assertEqual(gap.status, "FAIL")
    def test_missing_optional_does_not_fail(self):
        gap = check_data_gaps([], [{"name":"LiDAR","required":False}])[0]
        self.assertEqual(gap.status, "REVIEW")
    def test_present_category_passes(self):
        self.assertEqual(check_data_gaps([record()], [{"name":"Project boundary","required":True}])[0].status, "PASS")
