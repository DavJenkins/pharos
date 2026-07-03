import subprocess


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.stdout.strip()
    except Exception:
        return ""
