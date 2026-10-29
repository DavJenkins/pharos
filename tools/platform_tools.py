"""Obtain a profile's pinned tool without executing a foreign-architecture binary."""
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile
from urllib.request import urlopen,Request
from deploy.bootstrap_platform import elf_architecture


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def pmtiles(spec, cache, installed=Path('/usr/local/bin/pmtiles')):
    pin=spec['pmtiles'];arch=spec['baseline']['architecture']
    for path in (Path(installed),Path(cache)/('pmtiles-'+arch)):
        if path.is_file() and not path.is_symlink() and sha(path)==pin['binary_sha256'] and elf_architecture(path)==arch:return path
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    url=pin['url']
    if not url.startswith('https://github.com/protomaps/go-pmtiles/releases/download/'):
        raise ValueError('Tool source must be the pinned official release')
    with tempfile.TemporaryDirectory(prefix='pmtiles-',dir=cache) as tmp:
        archive=Path(tmp)/'release.tar.gz';total=0
        with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (Data Ark platform kit)'}),timeout=45) as response,archive.open('wb') as stream:
            if not response.url.startswith('https://'):raise ValueError('Tool redirected away from HTTPS')
            for block in iter(lambda:response.read(1024**2),b''):
                total+=len(block)
                if total>64*1024**2:raise ValueError('Tool archive exceeds size bound')
                stream.write(block)
        if sha(archive)!=pin['archive_sha256']:raise ValueError('Official tool archive checksum mismatch')
        binary=Path(tmp)/'pmtiles'
        with tarfile.open(archive) as bundle:
            members=[m for m in bundle.getmembers() if Path(m.name).name=='pmtiles' and m.isfile() and m.size<=128*1024**2]
            if len(members)!=1:raise ValueError('Expected one bounded PMTiles binary')
            with bundle.extractfile(members[0]) as source,binary.open('wb') as stream:shutil.copyfileobj(source,stream)
        if sha(binary)!=pin['binary_sha256'] or elf_architecture(binary)!=arch:raise ValueError('Tool hash or processor architecture mismatch')
        target=cache/('pmtiles-'+arch);binary.chmod(0o755);binary.replace(target)
    return target
