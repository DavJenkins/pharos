"""AP welcome detection and per-device internet forwarding control."""
import http.client
import ipaddress
import threading
import time
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from app.services.pass_through import control

router = APIRouter(prefix="/portal", include_in_schema=False)
ONLINE_LOCK = threading.Lock()
ONLINE_CACHE = (0.0, False)
PROBES = {
    "generate_204": ("http://connectivitycheck.gstatic.com/generate_204", 204, b""),
    "gen_204": ("http://connectivitycheck.gstatic.com/generate_204", 204, b""),
    "hotspot-detect.html": ("http://captive.apple.com/hotspot-detect.html", 200, b"Success"),
    "library/test/success.html": ("http://captive.apple.com/hotspot-detect.html", 200, b"Success"),
    "connecttest.txt": ("http://www.msftconnecttest.com/connecttest.txt", 200, b"Microsoft Connect Test"),
    "ncsi.txt": ("http://www.msftncsi.com/ncsi.txt", 200, b"Microsoft NCSI"),
}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def peer(request):
    # Apache overwrites the peer header. The API must remain loopback-only.
    try:
        address = ipaddress.ip_address(request.headers.get("x-dataark-peer", ""))
    except ValueError:
        raise HTTPException(404)
    if address not in ipaddress.ip_network("192.168.4.0/24"):
        raise HTTPException(404)
    return str(address)


def remembered(address):
    try:
        return control(address)
    except RuntimeError:
        return False


def upstream_available():
    global ONLINE_CACHE
    with ONLINE_LOCK:
        now = time.monotonic()
        if now < ONLINE_CACHE[0]:
            return ONLINE_CACHE[1]
        try:
            upstream_probe('generate_204')
            online = True
        except (OSError, ValueError, http.client.HTTPException):
            online = False
        ONLINE_CACHE = (time.monotonic() + 15, online)
        return online


def switch(request, enabled):
    address = peer(request)
    if request.headers.get("origin") != "http://192.168.4.1":
        raise HTTPException(403)
    if enabled and not upstream_available():
        raise HTTPException(409, "Upstream internet is unavailable")
    try:
        control(address, enabled)
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/continue")
def continue_online(request: Request):
    # Compatibility with already-cached copies of the former welcome button.
    return switch(request, True)


@router.post("/pass-through/{setting}")
def pass_through(setting: str, request: Request):
    if setting not in ('on', 'off'):
        raise HTTPException(404)
    return switch(request, setting == 'on')


@router.get("/upstream")
def upstream_state():
    # Public, read-only status of the Ark, independent of the caller's network.
    import json
    return Response(json.dumps({'online':upstream_available()}), media_type="application/json",
                    headers={"Cache-Control":"no-store"})


@router.get("/state")
def state(request: Request):
    address = peer(request)
    try:
        enabled = control(address)
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    import json
    return Response(json.dumps({'enabled':enabled,'upstream_online':upstream_available()}),
                    media_type="application/json", headers={"Cache-Control": "no-store"})


def upstream_probe(name):
    url, expected_status, expected_body = PROBES[name]
    # Fixed URLs only; no arbitrary proxy, environment proxy, redirects or cookies.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=3) as result:
        body = result.read(4097)
        if result.status != expected_status or len(body) > 4096:
            raise ValueError("Unexpected upstream probe response")
        if expected_body and expected_body not in body:
            raise ValueError("Upstream is not providing internet access")
        return result.status, body, ("text/html" if name.endswith(".html") else "text/plain")


@router.api_route("/probe/{name:path}", methods=["GET", "HEAD"])
def probe(name: str, request: Request):
    address = peer(request)
    if name not in PROBES:
        raise HTTPException(404)
    if remembered(address):
        try:
            status, body, media = upstream_probe(name)
            return Response(body if request.method != "HEAD" else b"", status_code=status,
                            media_type=media, headers={"Cache-Control": "no-store"})
        except (OSError, ValueError, http.client.HTTPException):
            pass
    return RedirectResponse("http://192.168.4.1/?portal=1", status_code=302,
                            headers={"Cache-Control": "no-store"})
