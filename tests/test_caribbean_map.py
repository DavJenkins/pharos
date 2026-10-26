import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CaribbeanCoverageTests(unittest.TestCase):
 def test_requested_islands_are_inside_selected_coverage(self):
  cfg=json.loads((ROOT/'deploy/reference/osm-caribbean.json').read_text())
  west,south,east,north=cfg['bbox']
  islands={'Sint Maarten':(-63.05,18.04),'Saint-Martin':(-63.05,18.09),'St Croix':(-64.75,17.73),'St Thomas':(-64.94,18.34),'St John':(-64.75,18.34),'Tortola':(-64.62,18.43),'Puerto Rico':(-66.1,18.3),'Cuba':(-79.5,22),'Hispaniola':(-71,19),'Jamaica':(-77.3,18.1),'Bahamas':(-77.4,25),'Turks and Caicos':(-71.14,21.46),'Cayman':(-81.25,19.3),'Aruba':(-69.97,12.52),'Curacao':(-69,12.2),'Bonaire':(-68.25,12.2),'Guadeloupe':(-61.58,16.25),'Martinique':(-61,14.6),'Barbados':(-59.54,13.19),'Trinidad':(-61.22,10.69),'Tobago':(-60.67,11.25)}
  for name,(lon,lat) in islands.items():
   with self.subTest(island=name):self.assertTrue(west<lon<east and south<lat<north)
  self.assertEqual(cfg['maxzoom'],15)
  self.assertEqual(cfg['path'],'maps/osm/caribbean.pmtiles')
