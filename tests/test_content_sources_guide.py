import unittest
from pathlib import Path
from tools.document_content_sources import generate
from app.services.manifest import load_manifest
from tools.publish_docs import markdown_to_html

class ContentGuideTests(unittest.TestCase):
    def test_every_active_asset_once_in_matching_cards(self):
        data = load_manifest('/opt/dataark/dataark.yaml')
        text, identifiers, cards = generate(data, Path('/mnt/storage'))
        expected = {a['id'] for a in data['assets'] if not a.get('removed')}
        self.assertEqual(set(identifiers), expected)
        self.assertEqual(len(identifiers), len(expected))
        self.assertEqual(len(cards), 24)
        self.assertEqual(len([line for line in text.splitlines() if line.startswith('## ') and line[3:4].isdigit()]), 24)
        self.assertIn('Caribbean island groups and destinations', text)
        self.assertIn('not a complete collection of every state statute', text)
        self.assertIn('http://dataark:8080/content/wikipedia_', text)
        self.assertNotIn('/library-files/wikipedia_en_all_maxi', text)
    def test_collapsible_groups_are_safe_and_lists_close(self):
        result = markdown_to_html('# Guide\n## 1. Maps & Navigation\n::: details All states <script>\n\n- One\n- Two\n\n:::\n')
        self.assertIn('<details class="content-details">', result)
        self.assertIn('<summary>All states &lt;script&gt;</summary>', result)
        self.assertIn('</ul>\n</details>', result)
        self.assertIn('id="1-maps-navigation"', result)
        self.assertNotIn('<script>', result)
