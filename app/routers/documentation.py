"""Locally hosted, themed Swagger UI; API operations retain their normal auth."""
from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.documentation_theme import masthead, footer

router = APIRouter()

@router.get('/docs', include_in_schema=False, response_class=HTMLResponse)
def documentation(request: Request):
    prefix = request.scope.get('root_path', '').rstrip('/')
    page = get_swagger_ui_html(
        openapi_url=prefix + '/openapi.json',
        title='Developer API — Data Ark',
        swagger_js_url='/assets/vendor/swagger-ui/swagger-ui-bundle.js',
        swagger_css_url='/assets/vendor/swagger-ui/swagger-ui.css',
        swagger_favicon_url='/assets/vendor/swagger-ui/favicon-32x32.png',
        swagger_ui_parameters={'filter': True, 'docExpansion': 'none', 'displayRequestDuration': True,
                               'validatorUrl': None, 'persistAuthorization': False},
    ).body.decode()
    page = page.replace('</head>', '<link rel="stylesheet" href="/assets/css/ark-documentation.css?v=1"></head>')
    page = page.replace('<body>', '<body class="ark-documentation api-documentation"><div class="documentation-shell">' + masthead('DEVELOPER REFERENCE', 'api') + '<main class="docs-paper api-paper"><p class="docs-eyebrow">EXPLORE THE ARK</p><h1>Developer API</h1><p class="docs-introduction">Inspect the available endpoints, read request and response formats, and try requests against this Ark.</p>')
    page = page.replace('</body>', '</main>' + footer() + '</div></body>')
    return HTMLResponse(page)

@router.get('/redoc', include_in_schema=False)
def legacy_documentation(request: Request):
    return RedirectResponse(request.scope.get('root_path', '').rstrip('/') + '/docs')
