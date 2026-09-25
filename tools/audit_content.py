#!/usr/bin/env python3
"""Read-only content portability audit; no document bodies or credentials."""
from collections import Counter
import json
import os
from pathlib import Path
import subprocess

def run(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def show(label, command):
    print("\n--- " + label + " ---")
    output = run(command)
    print(output.strip() if output else "(unavailable)")
    return output

def samba():
    print("\n--- Content share configuration ---")
    output = run(["testparm", "-s"])
    paths = []
    if not output:
        print("(unavailable)")
        return paths
    section = ""
    allowed = {"path", "read only", "browseable", "guest ok", "writeable", "writable", "force user", "create mask", "directory mask"}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            if section != "global":
                print(line)
        elif section and section != "global" and "=" in line:
            key, value = (part.strip() for part in line.split("=", 1))
            if key in allowed:
                print(f"  {key} = {value}")
                if key == "path" and value.startswith("/"):
                    paths.append(value)
    return paths

def summarize(root):
    print("\n--- Content metadata: " + str(root) + " ---")
    if not root.is_dir():
        print("(directory missing or inaccessible)")
        return
    try:
        top = sorted(root.iterdir(), key=lambda path: path.name.casefold())
        for path in top[:60]:
            kind = "link" if path.is_symlink() else "dir" if path.is_dir() else "file"
            print(f"{kind}: {path.name}")
        if len(top) > 60:
            print(f"... {len(top) - 60} additional top-level entries")
    except OSError:
        print("(cannot list)")
        return
    extensions = Counter()
    sizes = Counter()
    examples = {}
    errors = []
    count = 0
    total = 0
    truncated = False
    device = root.stat().st_dev
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: errors.append(type(error).__name__)):
        # Skip nested mounts, hidden operational directories, and symlinks.
        retained = []
        for name in dirs:
            path = Path(directory) / name
            try:
                if not name.startswith(".") and not path.is_symlink() and path.stat().st_dev == device:
                    retained.append(name)
            except OSError:
                errors.append("unreadable directory")
        dirs[:] = retained
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                errors.append("unreadable file")
                continue
            extension = path.suffix.lower() or "(no extension)"
            extensions[extension] += 1
            sizes[extension] += size
            if extension in (".zim", ".pdf", ".epub", ".html", ".txt"):
                samples = examples.setdefault(extension, [])
                if len(samples) < 3:
                    samples.append(str(path.relative_to(root)))
            total += size
            count += 1
            if count >= 100000:
                truncated = True
                break
        if truncated:
            break
    print(f"Files inspected: {count}; logical size: {total / 1024**3:.2f} GiB; capped: {truncated}")
    for extension, number in extensions.most_common(20):
        print(f"  {extension}: {number} files, {sizes[extension] / 1024**3:.2f} GiB")
    print("Example content paths: " + json.dumps(examples, ensure_ascii=False))
    print(f"Metadata errors: {len(errors)}")
    print("Root orientation files: " + ", ".join(path.name for path in top if path.is_file() and
          (path.name.lower().startswith(("readme", "start-here", "catalog", "index", "checksum", "sha256")))))

def main():
    show("Block devices and filesystem formats", ["lsblk", "-o", "NAME,TRAN,FSTYPE,FSVER,LABEL,SIZE,MOUNTPOINTS"])
    show("SSD mount and options", ["findmnt", "-T", "/mnt/storage", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"])
    shares = samba()
    mounts = show("Kiwix content mounts", ["docker", "inspect", "kiwix-serve", "--format", "{{json .Mounts}}"])
    roots = [Path("/mnt/storage")]
    if mounts:
        try:
            for mount in json.loads(mounts):
                source = mount.get("Source", "")
                if source.startswith("/"):
                    roots.append(Path(source))
        except (ValueError, TypeError):
            pass
    # Exclude the source-code share; audit only content directories.
    roots += [Path(path) for path in shares if path not in ("/opt/dataark", "/home/admin", "/")]
    selected = []
    for root in sorted(set(roots), key=lambda path: len(path.parts)):
        if root == Path("/") or any(root == parent or parent in root.parents for parent in selected):
            continue
        selected.append(root)
        summarize(root)
    print("\nAudit complete. No files, mounts, permissions, shares, or services were changed.")
    print("Review filenames before sharing this report; it contains no document bodies or passwords.")

if __name__ == "__main__":
    main()
