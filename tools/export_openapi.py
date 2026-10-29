#!/usr/bin/env python3
"""Export the public API contract from the installed source, without runtime data."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def export(target=None):
 from app.main import app
 data=app.openapi();data['servers']=[{'url':'/api'}]
 target=Path(target) if target else ROOT/'docs/30-Developer/api/openapi.json'
 target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 print('Exported public API contract:',len(data['paths']),'paths')
if __name__=='__main__':export(sys.argv[1] if len(sys.argv)>1 else None)
