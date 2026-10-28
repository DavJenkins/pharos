"""Check installed handler contracts; never runs restore/update/remove.

Importing Python executes module-level code. Run only against reviewed handlers.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.content_types import REGISTRY, ROOT, load_handler, read_registry


def check(path=REGISTRY, root=ROOT):
    registry = read_registry(path, root)
    checked = []
    for name, spec in registry['types'].items():
        load_handler(spec, root)
        checked.append(name)
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    args = parser.parse_args()
    names = check(args.registry)
    print('Handler API v1 contracts checked:', ', '.join(names))
    print('Structural checks only; run fixture and spare-media acceptance tests before relying on restoration.')
