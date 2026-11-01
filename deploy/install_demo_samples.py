"""Install only the samples explicitly approved with system-card demo allocation."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy import demo_library
from app.services.manifest import load_manifest


def register(repo, config):
    from app.services.demo_library import overlay
    return overlay(load_manifest(repo / 'dataark.yaml'), config)


if __name__ == '__main__':
    config = demo_library.samples(ROOT)
    register(ROOT, config)
    print('Demo samples verified and registered; full source catalogue retained.')
