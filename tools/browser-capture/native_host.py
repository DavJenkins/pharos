"""Chrome native host. Reads only a selected completed download; fixed SSH import command."""
import base64, json, os, struct, subprocess, sys
from pathlib import Path
MAX = 30 * 1024 * 1024
ROOT = Path(__file__).resolve().parent

def import_file(message, config):
    if message.get('operation') == 'check_updates':
        return run_ark({'operation':'check_updates'},config)
    targets = json.loads((ROOT / 'targets.json').read_text(encoding='utf-8'))
    item = next((x for x in targets if x['id'] == message.get('id')), None)
    if not item or message.get('url') != item['url']:
        raise ValueError('Download does not match an approved publisher request.')
    file = Path(message['filename']).resolve(strict=True)
    allowed = [Path(x).resolve(strict=True) for x in config['download_directories']]
    if not any(file.is_relative_to(p) for p in allowed) or not file.is_file():
        raise ValueError('File is outside the configured Downloads folders.')
    with file.open('rb') as stream: data = stream.read(MAX+1)
    if len(data) > MAX or not data.startswith(b'%PDF-'):
        raise ValueError('Downloaded response is not a PDF, or exceeds 30 MiB. Nothing was installed.')
    payload = {'id':item['id'],'source_url':item['url'],'captured_url':message.get('final_url',item['url']), 'data':base64.b64encode(data).decode(), 'expected_sha256':message.get('expected_sha256')}
    return run_ark(payload,config)

def run_ark(payload,config):
    if config['ark_host'] not in ['192.168.40.123','192.168.4.1','dataark']:
        raise ValueError('Unapproved Ark destination.')
    command = [config['ssh_executable'],'-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8','-i',config['ssh_key'], 'root@'+config['ark_host'], '/usr/bin/python3 /opt/dataark/tools/import_browser_reference.py']
    result = subprocess.run(command,input=json.dumps(payload),capture_output=True,text=True,timeout=600,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try: answer=json.loads(result.stdout)
    except ValueError: raise ValueError((result.stderr or 'Ark connection/import failed')[-1500:]) from None
    if not isinstance(answer,dict) or 'ok' not in answer: raise ValueError('Invalid Ark response.')
    return answer

def main():
    header = sys.stdin.buffer.read(4)
    if len(header)!=4:return
    size=struct.unpack('<I',header)[0]
    if not 0<size<=16384: return
    try:
        message=json.loads(sys.stdin.buffer.read(size))
        config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
        answer=import_file(message,config)
    except Exception as e:answer={'ok':False,'error':str(e)}
    data=json.dumps(answer).encode();sys.stdout.buffer.write(struct.pack('<I',len(data))+data);sys.stdout.buffer.flush()
if __name__=='__main__':main()
