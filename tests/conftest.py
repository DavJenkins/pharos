"""Keep network unit fixtures independent of the host's private role assignment."""
import pytest
import sys


@pytest.fixture(autouse=True)
def isolated_network_roles(request, tmp_path, monkeypatch):
    if request.module.__name__.split('.')[-1] not in {
        'test_network_admin', 'test_wifi_roles', 'test_wired_interfaces'
    }:
        return
    from tools import network_helper, wifi_interfaces
    monkeypatch.setattr(network_helper, 'ROLE_PENDING', tmp_path / 'pending.json')
    monkeypatch.setattr(wifi_interfaces, 'PLATFORM', tmp_path / 'platform.json')
    monkeypatch.setattr(wifi_interfaces, 'RUNTIME', tmp_path / 'runtime.json')
    helper_roles = sys.modules[network_helper.interfaces.__module__]
    monkeypatch.setattr(helper_roles, 'PLATFORM', tmp_path / 'platform.json')
    monkeypatch.setattr(helper_roles, 'RUNTIME', tmp_path / 'runtime.json')
