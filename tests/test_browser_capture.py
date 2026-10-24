import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ROOT=Path(__file__).resolve().parents[1]
server=load('capture_server',ROOT/'tools/import_browser_reference.py')
host=load('capture_host',ROOT/'tools/browser-capture/native_host.py')

class CaptureTests(unittest.TestCase):
 def test_wrong_year_and_wrong_document_are_rejected(self):
  for text in ['2024 Massachusetts Form 1','2025 Federal Form 1040','2025 Massachusetts Form 1 DRAFT AS OF May']:
   with self.subTest(text=text),patch.object(server.subprocess,'check_output',side_effect=['Pages: 4\nEncrypted: no\n',text]):
    with self.assertRaises(ValueError):server.validate_pdf(b'%PDF-fixture','ma-form1-2025')
 def test_matching_identity_and_year(self):
  with patch.object(server.subprocess,'check_output',side_effect=['Pages: 4\nEncrypted: no\n','2025 Massachusetts Form 1 Resident Income Tax Return']):
   self.assertEqual(server.validate_pdf(b'%PDF-fixture','ma-form1-2025'),4)
 def test_html_and_unknown_id_rejected_before_parser(self):
  with patch.object(server.subprocess,'check_output') as parse:
   for data,id in [(b'<html>Access denied</html>','ss5'),(b'%PDF-test','../../etc/passwd')]:
    with self.assertRaises(ValueError):server.validate_pdf(data,id)
   parse.assert_not_called()
 def test_encrypted_pdf_rejected(self):
  with patch.object(server.subprocess,'check_output',return_value='Pages: 4\nEncrypted: yes\n'):
   with self.assertRaises(ValueError):server.validate_pdf(b'%PDF-test','ss5')
 def test_native_file_boundary_and_fixed_command(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);downloads=root/'Downloads';downloads.mkdir();pdf=downloads/'form.pdf';pdf.write_bytes(b'%PDF-fixture');outside=root/'private.pdf';outside.write_bytes(b'%PDF-private')
   (root/'targets.json').write_text(json.dumps([{'id':'ma-form1-2025','url':'https://example.gov/form.pdf'}]))
   config={'download_directories':[str(downloads)],'ark_host':'192.168.40.123','ssh_key':'local-key','ssh_executable':'ssh'}
   message={'id':'ma-form1-2025','url':'https://example.gov/form.pdf','filename':str(pdf)}
   with patch.object(host,'ROOT',root),patch.object(host.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'{"ok":true,"message":"installed"}','')) as run:
    for bad in [{**message,'filename':str(outside)},{**message,'url':'https://evil.test/form.pdf'}]:
     with self.assertRaises(ValueError):host.import_file(bad,config)
    run.assert_not_called();self.assertTrue(host.import_file(message,config)['ok'])
    args=run.call_args.args[0];self.assertEqual(args[-1],'/usr/bin/python3 /opt/dataark/tools/import_browser_reference.py');self.assertNotIn(str(pdf),args)
    self.assertIn('StrictHostKeyChecking=yes',args)
    pdf.write_bytes(b'<html>403</html>')
    with self.assertRaises(ValueError):host.import_file(message,config)

if __name__=='__main__':unittest.main()
