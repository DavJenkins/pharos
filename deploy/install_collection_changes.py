"""Initialize shared root/admin collection journal storage; no service restart."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    if os.geteuid() != 0 or ROOT != Path('/opt/dataark'):
        raise SystemExit('Run as root from /opt/dataark on the Ark.')
    from app.services.collection_changes import database
    with database():
        pass
    print('Collection change journal initialized; no services restarted.')


if __name__ == '__main__':
    main()
