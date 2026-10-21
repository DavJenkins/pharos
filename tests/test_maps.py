import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile
from tools import map_worker as m

class Response(io.BytesIO):
    def __init__(self,data,headers=None):
        super().__init__(data);self.headers=headers or {'Content-Length':str(len(data))}

class MapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.item={'id':'x','title':'Example','group':'topographic','format':'PDF','url':'https://example.org/map.pdf','path':'topographic/map.pdf'}
        self.data={'system':{'base_mount':str(self.root)},'geography':{'country':'US','state':{'code':'MA','name':'Massachusetts'},'counties':[{'name':'Worcester'},{'name':'Middlesex'}]},'maps':{'enabled':True}}

    def test_settings(self):
        m.settings(self.data)
        for bad in ({'enabled':'yes'},{'reserve_gib':0},{'sources':['unknown']},{'max_run_gib':True}):
            with self.assertRaises(ValueError):m.settings(dict(self.data,maps=bad))

    def test_county_selection_and_missing_county(self):
        features=[{'attributes':{'TOWN':'Town','TOWN_ID':i,'COUNTY':county,'FIPS_STCO':fips}} for i,county,fips in [(1,'WORCESTER',25027),(2,'MIDDLESEX',25017),(3,'SUFFOLK',25025)]]
        with patch.object(m,'json_data',return_value={'features':features}):
            towns=m.county_towns(self.data);self.assertEqual(set(towns),{1,2})
        with patch.object(m,'json_data',return_value={'features':features[:1]}):
            with self.assertRaises(ValueError):m.county_towns(self.data)

    def test_latest_topos_only_and_download_host(self):
        base={'boundingBox':{'minX':1,'minY':2,'maxX':3,'maxY':4},'downloadURL':'https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/USTopo/PDF/MA/a.pdf'}
        old=dict(base,publicationDate='2020-01-01');new=dict(base,publicationDate='2024-01-01')
        self.assertEqual(m.latest_topos([old,new,new]),[new])
        with self.assertRaises(ValueError):m.latest_topos([dict(new,downloadURL='file:///etc/passwd')])
        self.assertTrue(m.parcel_url('http://download.massgis.digital.mass.gov/shapefiles/l3parcels/ACTON.zip').startswith(m.MASS))
        with self.assertRaises(ValueError):m.parcel_url('https://example.org/a.zip')

    def test_atomic_valid_pdf_and_conditional_request(self):
        target=self.root/'map.pdf';budget={'remaining':1000}
        with patch.object(m,'urlopen',return_value=Response(b'%PDF-test',{'ETag':'"abc"','Content-Length':'9'})):
            result,count=m.transfer(self.item,target,{},0,budget)
        self.assertEqual(target.read_bytes(),b'%PDF-test');self.assertEqual(budget['remaining'],991)
        with patch.object(m,'urlopen',side_effect=HTTPError(self.item['url'],304,'Unchanged',{},None)) as fetch:
            updated,count=m.transfer(self.item,target,result,0,budget)
        self.assertEqual(count,0);self.assertEqual(updated['sha256'],result['sha256'])
        self.assertEqual(fetch.call_args.args[0].get_header('If-none-match'),'"abc"')

    def test_invalid_replacement_preserves_good_copy_and_counts_bytes(self):
        target=self.root/'map.pdf';target.write_bytes(b'%PDF-good');budget={'remaining':100}
        with patch.object(m,'urlopen',return_value=Response(b'<html>error</html>')):
            with self.assertRaises(ValueError):m.transfer(self.item,target,{},0,budget)
        self.assertEqual(target.read_bytes(),b'%PDF-good');self.assertFalse((self.root/'.map.pdf.part').exists())
        self.assertLess(budget['remaining'],100)

    def test_budget_and_truncated_file(self):
        for budget,data,headers in [(3,b'%PDF-too-big',None),(100,b'%PDF-short',{'Content-Length':'50'})]:
            with patch.object(m,'urlopen',return_value=Response(data,headers)):
                with self.assertRaises(ValueError):m.transfer(self.item,self.root/'map.pdf',{},0,{'remaining':budget})
            self.assertFalse((self.root/'map.pdf').exists())

    def test_zip_validation_without_extraction(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('data.shp',b'map data')
        with patch.object(m,'urlopen',return_value=Response(buf.getvalue())):
            m.transfer(dict(self.item,format='GIS ZIP'),self.root/'maps.zip',{},0,{'remaining':1000})
        self.assertTrue((self.root/'maps.zip').exists());self.assertFalse((self.root/'data.shp').exists())

    def test_portable_index_escapes_source_text(self):
        (self.root/'topographic').mkdir();(self.root/'topographic/map.pdf').write_bytes(b'%PDF-data')
        m.publish(self.root,[dict(self.item,title='<script>')],{'files':{}},'MA')
        page=(self.root/'topographic/index.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',page);self.assertIn('href="map.pdf"',page)
        self.assertIn('not live flooding',page)

    def test_source_failure_does_not_block_other_collections(self):
        state=self.root/'state';state.mkdir()
        def discovery(data):
            if data['maps']['sources']==['parcels']:raise ValueError('Parcel service offline')
            return []
        with patch.object(m,'STATE',state),patch.object(Path,'is_mount',return_value=True),patch.object(m,'discover',side_effect=discovery):
            m.run(self.data)
        saved=json.loads((state/'state.json').read_text())
        self.assertIn('parcels',saved['group_errors']);self.assertIn('flood',saved['group_checked']);self.assertIn('topographic',saved['group_checked'])

if __name__=='__main__':unittest.main()
