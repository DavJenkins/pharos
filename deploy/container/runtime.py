"""Nonprivileged container initialization and foreground process supervision."""
import argparse,getpass,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
import shutil
from app.services import configuration_project as project
from app.services.manifest import load_manifest,build

ROOT=Path('/opt/dataark')
CONFIG=Path('/config')
WEB=Path('/var/www/html')
STATE=Path('/var/lib/dataark/container')

def write_image_metadata():
    from tools.write_build_info import build_info
    info=build_info();info.update(revision=os.environ.get('DATAARK_REVISION','development'),branch='container-image')
    (ROOT/'app/static/assets/build-info.json').write_text(json.dumps(info,indent=2)+'\n')

def initialize(config=CONFIG,defaults=Path('/usr/share/dataark')):
    """Fill only missing public defaults; never replace a supplied collection."""
    config.mkdir(parents=True,exist_ok=True)
    if not (config/'library').exists() and (config/'content/public-manifest.yaml').is_file():
        project.write(config/'library',project.public(load_manifest(config/'content/public-manifest.yaml')))
    for name in ('library','content'):
        path=config/name
        if path.is_symlink():raise ValueError('Public configuration folders cannot be symlinks')
        if not path.exists():shutil.copytree(defaults/name,path)
    source=config/'library/ark.yaml'
    # Existing modular configuration is authoritative; a portable flat manifest
    # is accepted when the drive predates modular authoring.
    manifest=project.load(source) if source.is_file() else load_manifest(config/'content/public-manifest.yaml')
    data=project.public(manifest)
    data['system']['base_mount']='/mnt/storage'
    data['system'].pop('demo_library',None)
    data['system'].setdefault('services',{})['content_url_prefix']='/library-files/'
    project.atomic_write(config/'manifest.yaml',project.dump(data).encode())
    return data

def render():
    STATE.mkdir(parents=True,exist_ok=True)
    previous=(CONFIG/'manifest.yaml').read_bytes() if (CONFIG/'manifest.yaml').is_file() else None
    try:
        initialize()
        project.atomic_write(ROOT/'dataark.yaml',(CONFIG/'manifest.yaml').read_bytes())
        build(ROOT/'dataark.yaml',ROOT/'app/templates/index.html',WEB/'index.html',content_root=Path('/mnt/storage'))
    except Exception as error:
        if previous is None:raise
        project.atomic_write(CONFIG/'manifest.yaml',previous)
        project.atomic_write(ROOT/'dataark.yaml',previous)
        (STATE/'rendered.json').write_text(json.dumps({'error':str(error),'at':time.time()}))
        print('Configuration reload rejected; retaining last working library:',error,flush=True)
        return
    for path in WEB.rglob('*.html'):
        if path.is_symlink():continue
        text=path.read_text(encoding='utf-8')
        if '/assets/js/container.js' not in text:
            text=text.replace('</body>','<script src="/assets/js/container.js"></script></body>')
            path.write_text(text,encoding='utf-8')
    (STATE/'rendered.json').write_text(json.dumps({'at':time.time(),'revision':os.environ.get('DATAARK_REVISION','development')}))

def archives(data,root=Path('/mnt/storage')):
    """Only configured current archives; never scan arbitrary private folders."""
    rows=[]
    for asset in data.get('assets',[]):
        if asset.get('removed') or not asset.get('relative_path','').endswith('.zim'):continue
        relative=Path(asset['relative_path']);path=root/relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe archive path')
        if path.is_file():rows.append((str(path),path.stat().st_size,path.stat().st_mtime_ns))
    return sorted(set(rows))

def password():
    from tools.prepare_recipient import password_record,write
    if not sys.stdin.isatty():raise ValueError('Use docker compose run --rm ark caretaker-password from an interactive terminal')
    secret=getpass.getpass('Caretaker password (12+ characters): ')
    if secret!=getpass.getpass('Repeat password: '):raise ValueError('Passwords did not match')
    write('/etc/dataark/network-admin.json',json.dumps(password_record(secret))+'\n')
    print('Caretaker password saved privately. Browsing remains open. No Linux/root password is created.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',nargs='?',choices=['serve','caretaker-password','render'],default='serve');a=parser.parse_args()
    if a.command=='caretaker-password':password();return
    if a.command=='render':render();return
    for folder in ['community','configuration','collection-changes','container','ark','logs']:(Path('/var/lib/dataark')/folder).mkdir(parents=True,exist_ok=True)
    from app.services.community import initialize as initialize_board
    initialize_board()
    shutil.copytree(ROOT/'app/static',WEB,dirs_exist_ok=True)
    docs=WEB/'docs'
    if not docs.exists():
        from tools.publish_docs import publish
        publish(ROOT/'docs',docs)
    render()
    processes=[];reader=None;signature=None;stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    api=subprocess.Popen([sys.executable,'-m','uvicorn','deploy.container.server:app','--host','0.0.0.0','--port','8088','--no-proxy-headers'])
    processes.append(api)
    try:
        while not stopping:
            if api.poll() is not None:raise RuntimeError('Web/API process exited')
            selected=archives(load_manifest(ROOT/'dataark.yaml'))
            if selected!=signature:
                if reader is not None:
                    reader.terminate()
                    try:reader.wait(timeout=15)
                    except subprocess.TimeoutExpired:reader.kill();reader.wait()
                reader=None
                if selected:
                    reader=subprocess.Popen(['kiwix-serve','--address=127.0.0.1','--port=8089','--urlRootLocation=/kiwix',*[r[0] for r in selected]])
                    processes.append(reader)
                signature=selected
                (STATE/'reader.json').write_text(json.dumps({'archives':len(selected),'updated':time.time()}))
                render()
            if reader is not None and reader.poll() is not None:raise RuntimeError('Archive reader exited')
            # Re-render on host edits or newly copied archives without downloading.
            marker=STATE/'reload'
            stamp=[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in sorted((CONFIG/'library').rglob('*.yaml')) if p.is_file()]
            if marker.exists() or stamp!=getattr(main,'stamp',stamp):
                render();marker.unlink(missing_ok=True)
            main.stamp=stamp
            time.sleep(2)
    finally:
        for child in processes:
            if child.poll() is None:child.terminate()
        deadline=time.monotonic()+20
        for child in processes:
            try:child.wait(timeout=max(.1,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:child.kill();child.wait()

if __name__=='__main__':main()
