from pathlib import Path
from tools.inject_brand_links import application_brand
from tools.audit_web_surface import audit

def test_nav_only_tool_gets_one_shared_masthead():
    source='<html><head></head><body><nav><a href="/">Dashboard</a></nav><header><h1>Tool title</h1></header></body></html>'
    result=application_brand(source)
    assert result.count('class="ark-app-masthead"')==1
    assert 'dej-software-footer.webp' in result and '<h1>Tool title</h1>' in result
    assert application_brand(result)==result

def test_dashboard_retains_its_pharos_title():
    source='<header class="site-header"><h1 class="ark-wordmark">Pharos</h1><nav>Content</nav></header>'
    assert 'ark-app-masthead' not in application_brand(source)

def test_implicit_head_setup_and_fullscreen_map_are_branded():
    setup='<html><head><title>Setup</title><body><header><a href="/">Data Ark</a></header></body></html>'
    result=application_brand(setup)
    assert 'ark-brand.css' in result and '</head><body' in result
    map_page='<html><head></head><body><header><h1>Map</h1><p>Coverage</p></header><main id="map"></main></body></html>'
    result=application_brand(map_page)
    assert '<div class="ark-app-masthead">' in result and 'Coverage' in result
    assert application_brand(result)==result

def test_audit_distinguishes_missing_files_services_and_dynamic_anchors(tmp_path):
    (tmp_path/'index.html').write_text('<a href="missing.html">Bad</a><a href="http://ark:8080/content/book">Reader</a><a href="#dynamic">Panel</a><script src="page.js"></script>')
    (tmp_path/'page.js').write_text("section.id='dynamic'")
    result=audit(tmp_path,'http://ark')
    assert len(result['missing'])==1 and result['missing'][0]['target']=='/missing.html'
    assert len(result['service_urls'])==1 and not result['fragment_review']

def test_online_guide_does_not_import_native_masthead_or_its_asset_paths():
    from tools.public_handbook import guide_content
    value=guide_content('<main><header class="ark-app-masthead"><img src="/assets/dej-software-footer.webp"></header><h1>Access content</h1><script>privateControls()</script><p>Read locally.</p></main>')
    assert '<h1>Access content</h1>' in value and 'Read locally.' in value
    assert 'masthead' not in value and 'dej-software-footer' not in value and '<script' not in value
