#!/usr/bin/env python3
"""Build original printable packs locally: /usr/bin/python3 tools/build_print_packs.py.
Requires Debian python3-reportlab. No network requests. Output is on the mounted SSD.
"""
import argparse, math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm

PATTERNS=[('square','Square grid'),('engineering','Engineering grid'),('dots','Dot grid'),('cross','Cross grid'),('isometric','Isometric triangular grid'),('iso-dots','Isometric dots'),('hex','Hexagonal grid'),('polar','Polar coordinates'),('log','Logarithmic grid - three decades'),('semi-log','Semi-logarithmic grid - three decades'),('lined','Ruled lines - 5 mm'),('wide','Wide ruled - 8.7 mm'),('narrow','Narrow ruled - 6.35 mm'),('handwriting','Handwriting guides'),('double','Double-line handwriting'),('cornell-lines','Cornell lined notes'),('cornell-grid','Cornell grid notes'),('cornell-dots','Cornell dot notes'),('music','Music staves'),('tablature','Guitar tablature'),('bass-tab','Bass tablature'),('calligraphy','Calligraphy guides'),('genkou','Character-writing squares'),('chess','Chess or checkers board'),('go','Go board - 19 by 19'),('calendar','Undated monthly calendar'),('story','Story and drawing page'),('blank','Blank page')]
WORKSHEETS=[
 ('Emergency contacts',['Name / relationship','Phone / alternative','Meeting place / notes']),
 ('Household inventory',['Item / location','Serial / quantity','Condition / notes']),
 ('Supplies and replenishment',['Supply','Have / need','Expiry / next check']),
 ('Medication record',['Person / medicine','Prescribed directions','Prescriber / refill / notes']),
 ('Evacuation planning',['People / pets / assistance','Destinations / transport','Contacts / items to take']),
 ('Pet care record',['Pet / identification','Food / care routine','Vet / medicine / contact']),
 ('Expenses and household budget',['Date / description','Category / amount','Paid / balance / notes']),
 ('Payment receipt record',['Date / payer / payee','Amount / purpose','Method / reference / acknowledgment']),
 ('Maintenance and repairs',['Equipment / location','Work / parts / date','Next due / person / notes']),
 ('Equipment loan / handover record',['Item / condition / accessories','From / to / date','Return date / return condition']),
 ('Project planning worksheet',['Task / desired result','Owner / resources','Due date / progress']),
 ('Community message log',['Date / time / from / to','Message / requested action','Delivered / follow-up']),
 ('Volunteer availability',['Name / contact','Skills / equipment','Availability / assignment']),
 ('Daily routine and care notes',['Time / person','Activity / support needed','Contact / notes']),
]
def span(a,b,step):
 while a<=b+.001:
  yield a;a+=step
def paper(c,kind,w,h):
 x=y=12;W=w-24;H=h-24;s=5
 c.saveState();c.scale(mm,mm);c.translate(0,h);c.scale(1,-1);c.setStrokeColorRGB(.55,.60,.64);c.setFillColorRGB(.55,.60,.64);c.setLineWidth(.15)
 def line(a,b,d,e,bold=False,dash=False):
  c.setLineWidth(.3 if bold else .15);c.setDash([1,1] if dash else []);c.line(a,b,d,e)
 def grid(a,b,W,H,dots=False,gap=5):
  for xx in span(a,a+W,gap):
   if dots:
    for yy in span(b,b+H,gap):c.circle(xx,yy,.28,stroke=0,fill=1)
   else:line(xx,b,xx,b+H)
  if not dots:
   for yy in span(b,b+H,gap):line(a,yy,a+W,yy)
 if kind in ('square','engineering','dots','cross'):
  if kind!='cross':grid(x,y,W,H,kind=='dots',1 if kind=='engineering' else s)
  if kind=='engineering':
   for xx in span(x,x+W,s):line(xx,y,xx,y+H,True)
   for yy in span(y,y+H,s):line(x,yy,x+W,yy,True)
  if kind=='cross':
   for xx in span(x,x+W,s):
    for yy in span(y,y+H,s):line(xx-.5,yy,xx+.5,yy);line(xx,yy-.5,xx,yy+.5)
 elif kind in ('isometric','iso-dots'):
  dy=s*math.sqrt(3)/2
  for row,yy in enumerate(span(y,y+H,dy)):
   for xx in span(x+(row%2)*s/2,x+W,s):
    if kind=='iso-dots':c.circle(xx,yy,.28,stroke=0,fill=1)
    else:
     if xx+s<=x+W:line(xx,yy,xx+s,yy)
     if yy+dy<=y+H:
      for dx in [-s/2,s/2]:
       if x<=xx+dx<=x+W:line(xx,yy,xx+dx,yy+dy)
 elif kind=='hex':
  r=s/math.sqrt(3);dy=r*math.sqrt(3)
  for col,cx in enumerate(span(x+r,x+W-r,r*1.5)):
   for cy in span(y+dy/2+(col%2)*dy/2,y+H-dy/2,dy):
    pts=[(cx+r*math.cos(i*math.pi/3),cy+r*math.sin(i*math.pi/3)) for i in range(6)]
    for i,p in enumerate(pts):line(*p,*pts[(i+1)%6])
 elif kind=='polar':
  R=min(W,H)/2
  for r in span(s,R,s):c.circle(w/2,h/2,r)
  for a in range(0,360,15):line(w/2,h/2,w/2+R*math.cos(a*math.pi/180),h/2+R*math.sin(a*math.pi/180))
 elif kind in ('log','semi-log'):
  for decade in range(3):
   for v in range(1,10):
    xx=x+(decade+math.log10(v))*W/3;line(xx,y,xx,y+H,v==1)
    if kind=='log':yy=y+(decade+math.log10(v))*H/3;line(x,yy,x+W,yy,v==1)
  if kind=='semi-log':
   for yy in span(y,y+H,s):line(x,yy,x+W,yy)
  c.rect(x,y,W,H)
 elif kind in ('lined','wide','narrow'):
  for yy in span(y,y+H,8.7 if kind=='wide' else 6.35 if kind=='narrow' else s):line(x,yy,x+W,yy)
 elif kind in ('handwriting','double','calligraphy'):
  for yy in span(y,y+H-10,15):
   for i in range(3):line(x,yy+i*5,x+W,yy+i*5,dash=i==1 and kind!='double')
  if kind=='calligraphy':
   p=c.beginPath();p.rect(x,y,W,H);c.clipPath(p,stroke=0)
   for xx in span(x-100,x+W,10):line(xx,y,xx+H/math.tan(math.pi/3),y+H,dash=True)
 elif kind.startswith('cornell'):
  cue=x+W*.24;bottom=y+H-35;c.rect(x,y,W,H);line(cue,y,cue,bottom,True);line(x,bottom,x+W,bottom,True)
  if kind!='cornell-lines':grid(cue+3,y+8,W*.76-6,bottom-y-10,kind=='cornell-dots')
  else:
   for yy in span(y+12,bottom-1,s):line(cue+3,yy,x+W-3,yy)
 elif kind in ('music','tablature','bass-tab'):
  n=5 if kind=='music' else 4 if kind=='bass-tab' else 6
  for yy in span(y,y+H-(n-1)*2.5,(n+4)*2.5):
   for i in range(n):line(x,yy+i*2.5,x+W,yy+i*2.5)
 elif kind=='genkou':
  grid(x,y,W,H,gap=10)
  for xx in span(x+5,x+W,10):line(xx,y,xx,y+H,dash=True)
  for yy in span(y+5,y+H,10):line(x,yy,x+W,yy,dash=True)
 elif kind in ('chess','go'):
  side=min(W,H);left=(w-side)/2;top=(h-side)/2;n=8 if kind=='chess' else 18;d=side/n;grid(left,top,side,side,gap=d)
  if kind=='chess':
   c.setFillColorRGB(.88,.9,.91)
   for a in range(8):
    for b in range(8):
     if (a+b)%2:c.rect(left+a*d,top+b*d,d,d,stroke=0,fill=1)
  else:
   for a in [3,9,15]:
    for b in [3,9,15]:c.circle(left+a*d,top+b*d,1,stroke=0,fill=1)
 elif kind=='calendar':grid(x,y+15,W,H-15,gap=10000) # Individual cells below.
 elif kind=='story':
  c.rect(x,y,W,H*.55)
  for yy in span(y+H*.6,y+H,s*1.5):line(x,yy,x+W,yy)
 if kind=='calendar':
  for i in range(8):line(x+i*W/7,y+15,x+i*W/7,y+H)
  for i in range(7):line(x,y+15+i*(H-15)/6,x+W,y+15+i*(H-15)/6)
 c.restoreState()
 if kind.startswith('cornell'):
  c.setFont('Helvetica',9)
  for xx,yy,t in [(15,17,'Cues'),(12+W*.24+3,17,'Notes'),(15,h-42,'Summary')]:c.drawString(xx*mm,(h-yy)*mm,t)
 if kind=='calendar':
  c.setFont('Helvetica',10);c.drawString(12*mm,(h-19)*mm,'Month: ____________________     Year: __________')
  for i,t in enumerate(['Sun','Mon','Tue','Wed','Thu','Fri','Sat']):c.drawString((14+i*W/7)*mm,(h-25)*mm,t)

def build(out):
 out.mkdir(parents=True,exist_ok=True)
 for name,size in [('letter',letter),('a4',A4)]:
  w,h=(v/mm for v in size);c=canvas.Canvas(str(out/f'paper-{name}.pdf'),pagesize=size,pageCompression=1);c.setTitle('Data Ark paper patterns - '+name.upper());c.setAuthor('DEJ Software / Data Ark')
  for kind,title in PATTERNS:
   paper(c,kind,w,h);c.setFillColorRGB(.2,.3,.33);c.setFont('Helvetica',8);c.drawString(12*mm,size[1]-8*mm,title);c.setFont('Helvetica',7);c.drawString(12*mm,6*mm,'Data Ark | Print at actual size / 100% | Freely copy and adapt');c.showPage()
  c.save()
  c=canvas.Canvas(str(out/f'household-{name}.pdf'),pagesize=size,pageCompression=1);c.setTitle('Data Ark household worksheets - '+name.upper());c.setAuthor('DEJ Software / Data Ark')
  for title,columns in WORKSHEETS:
   c.setFillColorRGB(.08,.23,.26);c.setFont('Helvetica-Bold',19);c.drawString(15*mm,size[1]-22*mm,title)
   c.setFont('Helvetica',10);c.drawString(15*mm,size[1]-32*mm,'Household / group: ____________________   Updated: ______________')
   c.setFont('Helvetica',8);c.drawString(15*mm,size[1]-40*mm,'Blank record worksheet. Keep completed personal information private.')
   if title=='Medication record':c.drawString(15*mm,size[1]-46*mm,'Record existing prescribed directions; this sheet provides no treatment advice.')
   top=size[1]-54*mm;left=15*mm;width=size[0]-30*mm;bottom=20*mm;col=width/3;rows=12;row=(top-bottom)/rows
   c.setStrokeColorRGB(.6,.67,.67);c.setLineWidth(.5)
   for i in range(4):c.line(left+i*col,bottom,left+i*col,top)
   for i in range(rows+1):c.line(left,top-i*row,left+width,top-i*row)
   c.setFont('Helvetica-Bold',8)
   for i,text in enumerate(columns):
    words=text.split();lines=['']
    for word in words:
     candidate=(lines[-1]+' '+word).strip()
     if c.stringWidth(candidate,'Helvetica-Bold',8)>col-10:lines.append(word)
     else:lines[-1]=candidate
    for j,line in enumerate(lines):c.drawString(left+i*col+5,top-12-j*10,line)
   c.setFont('Helvetica',7);c.drawString(left,10*mm,'Data Ark original worksheet | Not an official form or a legal agreement | Freely copy and adapt');c.showPage()
  c.save()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('/mnt/storage/family-resources/generated'));args=p.parse_args()
 if args.output==Path('/mnt/storage/family-resources/generated') and not Path('/mnt/storage').is_mount():raise SystemExit('Content SSD must be mounted')
 build(args.output)
