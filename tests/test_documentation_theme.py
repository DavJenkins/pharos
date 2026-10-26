import unittest
from starlette.requests import Request
from app.main import app
from app.routers.documentation import documentation, legacy_documentation
from tools.publish_docs import markdown_to_html

class DocumentationThemeTests(unittest.TestCase):
    def test_handbook_has_shared_dej_frame_and_safe_markdown(self):
        page = markdown_to_html('# Guide\n## Commands\nUse **care** and `<file>`.\n---\n[Next](next.md)')
        for expected in ['DEJ SOFTWARE', 'ark-documentation.css', 'docs-masthead', 'docs-footer', '<strong>care</strong>', '<code>&lt;file&gt;</code>', '<hr>', 'href="next.html"']:
            self.assertIn(expected, page)
        self.assertNotIn('<file>', page)

    def test_interactive_docs_use_local_assets_and_api_prefix(self):
        response = documentation(Request({'type': 'http', 'root_path': '/api'}))
        self.assertEqual(response.status_code, 200)
        page = response.body.decode()
        for expected in ['/assets/vendor/swagger-ui/swagger-ui-bundle.js', '/assets/vendor/swagger-ui/swagger-ui.css', '/api/openapi.json', 'DEJ SOFTWARE', 'Developer API', 'SwaggerUIBundle', 'ark-documentation.css']:
            self.assertIn(expected, page)
        self.assertNotIn('cdn.jsdelivr.net', page)
        self.assertNotIn('fastapi.tiangolo.com/img', page)

    def test_schema_and_legacy_docs_remain_accessible(self):
        self.assertIn('/status', app.openapi()['paths'])
        response = legacy_documentation(Request({'type': 'http', 'root_path': '/api'}))
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/api/docs')

if __name__ == '__main__': unittest.main()
