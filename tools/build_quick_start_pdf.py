"""Render channel-specific and private welcome sheets from one HTML template."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.welcome_guides import channels,render

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--channel',choices=channels(),default='microsd');p.add_argument('--all',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'docs/10-User/assets/data-ark-quick-start.pdf');p.add_argument('--output-dir',type=Path,default=ROOT/'output/first-start-guides');p.add_argument('--code-file',type=Path);p.add_argument('--title');p.add_argument('--note',default='');p.add_argument('--browser',type=Path);p.add_argument('--html-only',action='store_true');args=p.parse_args()
 code=args.code_file.read_text().strip() if args.code_file else None
 if code is not None:
  if args.all:p.error('Private code output must target one channel.')
  dest=args.output.resolve()
  if dest.is_relative_to(ROOT/'docs') or any(part.lower()=='website' for part in dest.parts):p.error('Keep a real setup code outside public documentation and website folders.')
 candidates=[str(args.browser)] if args.browser else ['C:/Program Files/Google/Chrome/Application/chrome.exe',shutil.which('chromium'),shutil.which('chromium-browser'),shutil.which('google-chrome')]
 browser=next((v for v in candidates if v and Path(v).is_file()),None)
 if not args.html_only and not browser:p.error('A local Chrome/Chromium installation is required to print PDFs; use --browser or --html-only.')
 results=[]
 for channel in (channels() if args.all else [args.channel]):
  output=(args.output_dir/('data-ark-first-start-'+channel+'.pdf')) if args.all else args.output
  output.parent.mkdir(parents=True,exist_ok=True);page=output.with_suffix('.html');page.write_text(render(channel,code=code,title=args.title,note=args.note),encoding='utf-8')
  if not args.html_only:
   with tempfile.TemporaryDirectory(prefix='ark-guide-chrome-') as profile:
    proc=subprocess.run([browser,'--headless','--disable-gpu','--no-pdf-header-footer','--no-header-footer','--user-data-dir='+profile,'--print-to-pdf='+str(output.resolve()),page.resolve().as_uri()],capture_output=True,text=True,timeout=90)
    if proc.returncode or not output.is_file():raise RuntimeError('Guide PDF could not be printed: '+proc.stderr[-600:])
   from pypdf import PdfReader
   reader=PdfReader(output);assert len(reader.pages)<=3,'Guide unexpectedly spans more than three pages'
   text='\n'.join(v.extract_text() or '' for v in reader.pages);assert 'DEJ Software' in text and channels()[channel]['title'] in text
   if code:assert code in text.replace(' ','')
   results.append({'channel':channel,'pdf':str(output),'pages':len(reader.pages),'bytes':output.stat().st_size})
  else:results.append({'channel':channel,'html':str(page)})
 print(json.dumps(results,indent=2))
if __name__=='__main__':main()
