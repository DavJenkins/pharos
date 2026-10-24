import math,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from app.routers import callsigns
class CallsignTests(unittest.TestCase):
 def test_grid(self):
  self.assertEqual(callsigns.grid_center('FN42'),(42.5,-71.0))
  self.assertAlmostEqual(callsigns.grid_center('FN42ab')[0],42+1/24+1/48)
  self.assertEqual(callsigns.grid_center('AA'),(-85,-170))
  for g in ['ZZ99','FN4','FN42yy','FN42ab123']:
   with self.assertRaises(ValueError):callsigns.grid_center(g)
  self.assertAlmostEqual(callsigns.distance(0,179.9,0,-179.9),22.239,places=2)
  self.assertAlmostEqual(callsigns.bearing(0,0,1,0),0)
  self.assertAlmostEqual(callsigns.bearing(0,0,0,1),90)
  self.assertAlmostEqual(callsigns.bearing(0,0,-1,0),180)
  self.assertIsNone(callsigns.bearing(0,0,0,0))
 def test_search(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'test.sqlite';db=sqlite3.connect(path);db.executescript('CREATE TABLE licenses(id INTEGER,callsign TEXT,status TEXT,service TEXT,grant_date TEXT,expires TEXT,cancelled TEXT,name TEXT,city TEXT,state TEXT,zip TEXT); CREATE TABLE zcta(zip TEXT,lat REAL,lon REAL); CREATE VIRTUAL TABLE names USING fts5(name,content="licenses",content_rowid="rowid");')
   db.executemany('INSERT INTO licenses VALUES(?,?,?,?,?,?,?,?,?,?,?)',[(1,'W1TEST','A','HA','01/01/2020','01/01/2030','','Fictional Alpha','Testville','MA','00001'),(2,'W2TEST','E','HA','','','','Fictional Beta','Elsewhere','NY','00002')]);db.execute('INSERT INTO names(names) VALUES("rebuild")');db.executemany('INSERT INTO zcta VALUES(?,?,?)',[('00001',42.5,-71),('00002',41,-74)]);db.commit();db.close()
   with patch.object(callsigns,'DATABASE',path):
    def find(**kw):
     args=dict(q='',mode='callsign',state='',city='',grid='',radius_km=50,active=True);args.update(kw);return callsigns.search(**args)
    self.assertEqual(find(q='w1')['results'][0]['callsign'],'W1TEST')
    self.assertEqual(len(find(q='Fict Alp',mode='name')['results']),1)
    r=find(grid='FN42',radius_km=5);self.assertEqual(len(r['results']),1);self.assertEqual(r['results'][0]['distance_km'],0)
    self.assertEqual(len(find(q='W',active=False)['results']),2)
    for kw in [dict(grid='bad'),dict(q="' OR 1=1"),dict()]:
     with self.assertRaises(HTTPException) as caught:find(**kw)
     self.assertEqual(caught.exception.status_code,400)
if __name__=='__main__':unittest.main()
