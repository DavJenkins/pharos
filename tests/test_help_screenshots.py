from pathlib import Path
import tempfile
import unittest
from tools.publish_docs import markdown_to_html,publish
from tools.public_handbook import rewrite

class HelpScreenshots(unittest.TestCase):
    def test_local_image_is_accessible_responsive_and_enlargeable(self):
        text=markdown_to_html('# Help\n![Choose the adapter](../assets/screenshots/ethernet.jpg)')
        for expected in ['<figure','<figcaption','alt="Choose the adapter"','href="../assets/screenshots/ethernet.jpg"','src="../assets/screenshots/ethernet.jpg"','max-width:100%','loading="lazy"']:
            self.assertIn(expected,text)
    def test_remote_or_executable_image_targets_refused(self):
        for target in ['https://example.com/a.jpg','//example.com/a.jpg','javascript:evil.jpg','../private.json']:
            with self.subTest(target=target),self.assertRaises(ValueError):markdown_to_html('![Image]('+target+')')
    def test_images_are_literal_inside_commands(self):
        text=markdown_to_html('```\n![not an image](a.jpg)\n```')
        self.assertNotIn('<figure',text)
    def test_native_and_public_editions_resolve_same_local_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);guide=root/'docs/10-User/Guide.md';guide.parent.mkdir(parents=True);guide.write_text('# Guide\n![Example](../assets/screenshots/example.jpg)')
            image=root/'docs/assets/screenshots/example.jpg';image.parent.mkdir(parents=True);image.write_bytes(b'fixture-image')
            target=root/'rendered';publish(root/'docs',target)
            self.assertEqual((target/'assets/screenshots/example.jpg').read_bytes(),b'fixture-image')
            page=markdown_to_html(guide.read_text())
            public=rewrite(root,guide,page,'/data-ark/editions/test/')
            self.assertIn('src="/data-ark/editions/test/docs/assets/screenshots/example.jpg"',public)
            self.assertIn('href="/data-ark/editions/test/docs/assets/screenshots/example.jpg"',public)

if __name__=='__main__':unittest.main()
