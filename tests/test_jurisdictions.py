import json
import unittest
from tools.install_jurisdictions import university_body, validate_text

class JurisdictionTests(unittest.TestCase):
    def payload(self, count=10):
        values=[None, {'data':2}, {'useConstitutionEntriesAll2026-10-24':3}, []]
        for i in range(count):
            entry=len(values); values[3].append(entry)
            values.extend([{'title':entry+1,'clause':entry+2,'notes':entry+3},
                'Section '+str(i+1), 'The Alabama legislature and governor shall respect <rights>.',
                'Research annotation that must not be copied'])
        return '<script id="__NUXT_DATA__" type="application/json">'+json.dumps(values)+'</script>'

    def test_extracts_provisions_escapes_text_and_excludes_annotations(self):
        body,text,count,snapshot=university_body(self.payload())
        self.assertEqual(count,10)
        self.assertEqual(snapshot,'2026-10-24')
        self.assertIn('&lt;rights&gt;',body)
        self.assertNotIn('Research annotation',body)
        self.assertIn('Section 10',body)

    def test_index_only_payload_is_rejected(self):
        with self.assertRaises(ValueError):university_body(self.payload(0))
        with self.assertRaises(ValueError):university_body('<html>Table of contents</html>')

    def test_validation_rejects_short_or_wrong_jurisdiction(self):
        with self.assertRaises(ValueError):validate_text('Alabama constitution contents','Alabama')
        with self.assertRaises(ValueError):validate_text(('Virginia constitution governor legislature '*400),'Alabama')
        self.assertGreater(len(validate_text(('Alabama constitution governor legislature '*400),'Alabama')),12000)

if __name__=='__main__':unittest.main()
