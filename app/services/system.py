from pathlib import Path
import subprocess


def _model() -> str:
    try:
        return Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
    except Exception:
        try:
            vendor=Path('/sys/class/dmi/id/sys_vendor').read_text().strip()
            model=Path('/sys/class/dmi/id/product_name').read_text().strip()
            return vendor+' '+model
        except OSError:
            import platform
            return platform.machine()


def installed_ram(revision_path=Path('/proc/device-tree/system/linux,revision')):
    """Decode installed capacity, rather than OS-usable RAM, from Pi revision bits.

    Raspberry Pi documentation: new-style flag bit 23; memory bits 20-22.
    """
    try:
        raw=Path(revision_path).read_bytes()
        if len(raw)!=4:return None
        revision=int.from_bytes(raw,'big')
        if not revision & (1<<23):return None
        return {0:'256 MB',1:'512 MB',2:'1 GB',3:'2 GB',4:'4 GB',5:'8 GB',6:'16 GB'}.get((revision>>20)&7)
    except OSError:
        return None


def _uptime() -> str:
    try:
        return subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        ).stdout.strip().removeprefix("up ")
    except Exception:
        return ""


def collect() -> dict:
    return {
        "hostname": Path("/etc/hostname").read_text().strip(),
        "platform": _model(),
        "uptime": _uptime(),
    }
