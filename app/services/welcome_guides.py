"""One self-contained welcome-sheet template for public guides and private handoff."""
from pathlib import Path
import base64,html,json,re
ROOT=Path(__file__).resolve().parents[2]
def channels():return json.loads((ROOT/'config/distribution-channels.json').read_text(encoding='utf-8'))['channels']
def asset(name,root=ROOT):
 path=root/'app/static/assets'/name
 if not path.is_file():path=ROOT/'app/static/assets'/name
 mime='image/webp' if path.suffix=='.webp' else 'image/png'
 return 'data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
def render(channel='microsd',*,code=None,hostname='',ssid='DataArk',network_mode='hotspot',title=None,note='',root=ROOT):
 model=channels()[channel];private=code is not None
 if private and (not model['pairing'] or not re.fullmatch(r'[0-9]{4}',code)):raise ValueError('Use a four-digit private code only for a prepared card or appliance.')
 e=lambda text:html.escape(str(text),quote=True)
 logo=asset('pharos-data-ark-clean.png',root);maker=asset('dej-software-footer.webp',root)
 brand='<svg class="wordmark" viewBox="0 0 4420 350" role="img" aria-label="PHAROS DATA ARK"><defs><image id="ark-lettering" width="1967" height="799" href="'+logo+'"/><clipPath id="pharos-crop"><rect width="1800" height="350"/></clipPath><clipPath id="data-crop"><rect x="1900" width="2520" height="350"/></clipPath></defs><g clip-path="url(#pharos-crop)"><use href="#ark-lettering" transform="translate(-80 -115)"/></g><g clip-path="url(#data-crop)"><use href="#ark-lettering" transform="translate(1760 -672) scale(1.4)"/></g></svg>'
 def header(label):return '<header><div class="maker"><a href="https://www.dejsoftware.com/"><img src="'+maker+'" alt="DEJ Software™"></a></div>'+brand+'<p class="edition">'+e(label)+'</p></header>'
 # Label-side outline: exact 11 x 15 mm envelope, contacts against the paper.
 target='<svg class="card-target" width="70mm" height="70mm" viewBox="0 0 70 70" aria-label="Actual-size microSD outline"><circle cx="35" cy="35" r="33" fill="none" stroke="#ac8835" stroke-width=".35"/><use href="#ark-lettering" transform="translate(10 10) scale(.025419)"/><g transform="translate(29.5 36) scale(1 -1) translate(0 -15)"><path d="M .7 15 H 9 C 9.4 15 9.7 14.7 9.7 14.3 V 10.3 C 9.7 10.15 9.75 9.95 9.9 9.8 L 10.8 8.9 C 10.95 8.75 11 8.6 11 8.45 V 6.9 H 10.5 C 10.35 6.9 10.3 6.8 10.3 6.65 V 5.95 C 10.3 5.8 10.35 5.7 10.45 5.6 L 11 5.05 V .7 C 11 .3 10.7 0 10.3 0 H .7 C .3 0 0 .3 0 .7 V 14.3 C 0 14.7 .3 15 .7 15 Z" fill="none" stroke="#203e54" stroke-width=".2"/></g></svg>'
 out=['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title or model['title'])+' - PHAROS DATA ARK</title><style>@page{size:Letter;margin:12mm 14mm}*{box-sizing:border-box}body{margin:0;color:#203e54;background:white;font:10.5pt/1.4 Arial,sans-serif}.page{max-width:720px;margin:auto}header{background:#f0eee5;border-radius:9px;border-bottom:2px solid #ac8835;padding:12px 18px;margin-bottom:16px}.maker{height:22px;width:125px;overflow:hidden;margin-bottom:8px}.maker img{width:278px;max-width:none;position:relative;left:-78px;top:-6px}.wordmark{display:block;width:300px;max-width:100%;height:auto}.edition{font-size:11pt;font-weight:bold;margin:10px 0 0}h1{font-size:16pt;margin:12px 0 9px}h2{font-size:12pt;margin:14px 0 6px}p{margin:7px 0}li{margin:7px 0}ol,ul{padding-left:22px;margin:8px 0}.code-area{display:flex;align-items:center;justify-content:space-between;gap:12px;break-inside:avoid}.code-copy{flex:1}.code{font:700 27pt monospace;letter-spacing:7px;border:1px solid #ac8835;padding:12px 8px;display:inline-block;margin:8px 0}.card-target{flex:none}.roles{background:#f5f3ec;border-left:3px solid #ac8835;padding:9px 12px;margin:12px 0;break-inside:avoid}code{font:10pt monospace}.footer{border-top:1px solid #ac8835;font-size:8pt;margin-top:16px;padding-top:7px;display:flex;justify-content:space-between;gap:10px}a{color:#1b5c87}.hardware{break-before:page}.hardware header .wordmark{width:260px}.hardware header .maker{display:none}.screen-actions{margin:16px 0;text-align:right}button{padding:10px 18px}@media print{.screen-actions{display:none}.page{max-width:none}a{color:inherit;text-decoration:none}}@media screen{body{background:#e7eced;padding:20px}.page{background:white;padding:24px}.hardware{margin-top:28px}}@media(max-width:540px){body{padding:8px}.page{padding:16px}.code-area{flex-wrap:wrap}.card-target{margin:auto}.wordmark{width:260px}}</style></head><body><section class="page">',header(title or model['title']),'<p>'+e(model['intro'])+'</p>']
 if note:out.append('<p><strong>'+e(note)+'</strong></p>')
 if private and network_mode=='lan':out.append('<p>Connect the device and your browser to the same local network. For headless first setup, use Ethernet.</p>')
 if private and network_mode!='lan':out.append('<p>Join the '+e(ssid)+' Wi-Fi hotspot.</p>')
 if model['pairing']:
  out+=['<div class="code-area"><div class="code-copy"><h2>Your one-time setup code</h2><div class="code">'+e(code if private else '____')+'</div><p>'+( 'Keep this code private until setup is complete.' if private else 'Use the private code supplied with this card or appliance.')+'</p><p>(Prevents nearby setup-time hijacking.)</p></div>'+(target if model['card_target'] else '')+'</div>']
 else:out+=['<p class="roles"><strong>Setup authorization:</strong> '+('set the caretaker password in the Docker host terminal. The container does not use pairing codes and does not create Linux accounts.' if channel=='docker' else 'use the trusted local installer or host terminal. No separate activation code is needed after owner credentials are set. If browser setup is deferred on a shared network, prepare a fresh private pairing code first.')+'</p>']
 out+=['<h2>What you need</h2><ul>'+''.join('<li>'+e(t)+'</li>' for t in model['needs'])+'</ul><h2>First start</h2><ol>']
 for text in model['steps']:
  if private and model['pairing'] and network_mode=='lan' and '192.168.4.1' in text:text='Connect to the same local network and open http://'+hostname+'.local/setup.html. Enter your supplied private setup code.'
  if private and ssid!='DataArk':text=text.replace('DataArk hotspot',ssid+' hotspot')
  out.append('<li>'+e(text)+'</li>')
 out.append('</ol>')
 if model['pairing']:out.append('<div class="roles"><p><strong>Caretaker password:</strong> authorizes web changes when prompted.</p><p><strong>Linux admin password:</strong> protects SSH and terminal access as <code>admin</code>. Use a different, particularly strong password. Both passwords require at least 12 characters; root login stays disabled.</p><p>Five wrong codes trigger a one-minute pause. Successful setup retires the code. Complete initial HTTP setup privately before inviting others.</p></div>')
 out.append('<p>Browsing installed content needs no password. No online activation, registration or DEJ Software account is required.</p>')
 if hostname:out.append('<p>Device: <code>'+e(hostname)+'</code></p>')
 if channel in ('microsd','appliance'):out.append('<footer class="footer"><a href="https://www.dejsoftware.com/">DEJ Software™ · dejsoftware.com</a><span>'+('Private card-specific sheet' if private else 'Public first-start guide')+'</span></footer>')
 if model['hardware']:
  out+=(['</section><section class="page hardware">',header('Hardware & operating notes')] if channel in ('microsd','appliance') else ['<h2>Operating notes</h2>'])
  out+=['<ul>'+''.join('<li>'+e(t)+'</li>' for t in model['hardware'])+'</ul><h2>Further help</h2><p>The complete handbook is included with the Ark. Online: <a href="https://www.dejsoftware.com/data-ark/docs/">dejsoftware.com/data-ark/docs/</a>.</p><p>On an installed appliance, use System / System / Power before disconnecting power or removing storage. Containers use their host controls.</p><footer class="footer"><a href="https://www.dejsoftware.com/">DEJ Software™ · dejsoftware.com</a><span>'+e(model['title'])+'</span></footer>']
 out+=['<div class="screen-actions"><button onclick="window.print()">Print / Save as PDF</button></div></section></body></html>']
 return ''.join(out)
