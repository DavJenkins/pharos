import unittest,tempfile,tarfile
from pathlib import Path
from unittest.mock import patch
from tools import ready_card,ready_card_writer as writer
class PortableWelcomeTests(unittest.TestCase):
 def test_both_writers_receive_the_same_placeholder_template(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);archive=folder/'source.tar.gz'
   with tarfile.open(archive,'w:gz') as tar:
    for name in ['app/services/welcome_guides.py','config/distribution-channels.json','app/static/assets/pharos-data-ark-clean.png','app/static/assets/dej-software-footer.webp']:tar.add(root/name,arcname=name)
   text=ready_card.portable_welcome(archive,folder);self.assertTrue('{{SETUP_CODE}}' in text);self.assertTrue('DATAARK_HOSTNAME' in text);(folder/'welcome-template.html').write_text(text,encoding='utf-8')
   with patch.object(writer,'HERE',folder),patch.object(writer.secrets,'randbelow',return_value=7),patch.object(writer.secrets,'token_hex',return_value='abcdefabcdef'):
    seed,cloud,sheet=writer.make_seed({'library_gib':4,'country':'US','kit_sha256':'a'*64},b'driver')
   self.assertTrue('<div class="code">0007</div>' in sheet);self.assertFalse('{{SETUP_CODE}}' in sheet);self.assertTrue(seed['hostname'] in sheet);self.assertTrue('PHAROS DATA ARK' in sheet)
