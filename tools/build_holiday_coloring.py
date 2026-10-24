#!/usr/bin/env python3
"""Build original holiday coloring PDFs from a readable theme catalogue."""
import hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/mnt/storage/family-resources/holidays')

def poly(c,points,close=True):
 p=c.beginPath();p.moveTo(*points[0])
 for x,y in points[1:]:p.lineTo(x,y)
 if close:p.close()
 c.drawPath(p)
def star(c,x,y,r,n=5):
 poly(c,[(x+(r if i%2==0 else r*.43)*math.cos(math.pi/2+i*math.pi/n),y+(r if i%2==0 else r*.43)*math.sin(math.pi/2+i*math.pi/n)) for i in range(n*2)])
def heart(c,x=0,y=0,s=1):
 c.saveState();c.translate(x,y);c.scale(s,s);p=c.beginPath();p.moveTo(0,-30);p.curveTo(-60,0,-42,55,0,24);p.curveTo(42,55,60,0,0,-30);p.close();c.drawPath(p);c.restoreState()
def candle(c,x,y,h=35):
 c.rect(x-4,y,8,h);p=c.beginPath();p.moveTo(x,y+h+3);p.curveTo(x-9,y+h+10,x-2,y+h+13,x,y+h+21);p.curveTo(x+9,y+h+11,x+8,y+h+6,x,y+h+3);p.close();c.drawPath(p)
def motif(c,name):
 # Motifs occupy roughly a 100 x 100 square around the origin.
 c.setLineWidth(1.4)
 if name=='heart':heart(c,0,-2)
 elif name=='star':
  star(c,0,0,42);star(c,0,0,24)
 elif name=='fireworks':
  for angle in range(0,360,45):
   c.saveState();c.rotate(angle);c.line(0,12,0,37);c.circle(0,43,3);c.restoreState()
  star(c,0,0,12)
 elif name=='lantern':
  c.roundRect(-30,-28,60,60,16);c.rect(-19,32,38,6);c.rect(-19,-34,38,6);c.arc(-23,-28,23,32,90,180);c.arc(-10,-28,10,32,90,180)
  c.line(0,-34,0,-46);c.line(-6,-46,6,-46);c.arc(-12,38,12,53,0,180)
 elif name=='shamrock':
  for angle in [0,120,240]:c.saveState();c.rotate(angle);heart(c,0,21,.55);c.restoreState()
  p=c.beginPath();p.moveTo(0,-8);p.curveTo(2,-23,10,-36,19,-40);p.lineTo(12,-44);p.curveTo(1,-30,-5,-19,-5,-8);c.drawPath(p)
 elif name=='egg':
  p=c.beginPath();p.moveTo(0,46);p.curveTo(-45,35,-55,-46,0,-46);p.curveTo(55,-46,45,35,0,46);p.close();c.drawPath(p)
  for y,w in [(-22,34),(0,38),(22,28)]:poly(c,[(-w,y),( -w/2,y+6),(0,y),(w/2,y+6),(w,y)],False)
  for x in [-16,0,16]:c.circle(x,-34,3)
 elif name=='earth':
  c.circle(0,0,43);c.ellipse(-18,-43,18,43);c.ellipse(-34,-43,34,43)
  c.line(-43,0,43,0);c.line(-35,24,35,24);c.line(-35,-24,35,-24)
 elif name=='pumpkin':
  c.ellipse(-42,-34,42,31);c.ellipse(-25,-34,25,31);c.ellipse(-10,-34,10,31)
  poly(c,[(-4,31),(-7,44),(6,47),(5,31)]);poly(c,[(-24,6),(-15,18),(-7,6)]);poly(c,[(7,6),(15,18),(24,6)])
  poly(c,[(-24,-10),(-15,-22),(0,-27),(15,-22),(24,-10),(12,-16),(0,-19),(-12,-16)])
 elif name=='turkey':
  for angle in [-65,-32,0,32,65]:
   c.saveState();c.rotate(angle);c.ellipse(-10,-5,10,46);c.restoreState()
  c.setFillColorRGB(1,1,1);c.ellipse(-24,-32,24,15,fill=1);c.circle(0,16,13,fill=1);c.setFillColorRGB(0,0,0);c.circle(-4,19,1.5);c.circle(4,19,1.5);poly(c,[(-4,13),(4,13),(0,7)])
  for x in [-10,10]:c.line(x,-32,x,-44);c.line(x-6,-44,x+6,-44)
 elif name=='tree':
  poly(c,[(-10,-40),(10,-40),(10,-29),(-10,-29)])
  poly(c,[(0,39),(-21,17),(-12,17),(-34,-7),(-22,-7),(-45,-29),(45,-29),(22,-7),(34,-7),(12,17),(21,17)])
  star(c,0,45,8)
  for x,y in [(-8,10),(11,-8),(-16,-20),(22,-22)]:c.circle(x,y,3)
 elif name in ['menorah','kinara']:
  if name=='menorah':
   # Eight lights plus a raised central shamash.
   for i in range(-4,5):
    x=i*10;bottom=-22;top=8 if i else 23;candle(c,x,bottom,top-bottom)
   c.line(-44,-22,44,-22);c.rect(-5,-36,10,14);c.rect(-25,-41,50,5)
  else:
   # Seven lights, three on either side of the central candle.
   for i in range(-3,4):candle(c,i*12,-24,35 if i else 45)
   c.rect(-43,-31,86,7);c.rect(-32,-38,64,7)
 elif name=='diya':
  p=c.beginPath();p.moveTo(-43,-5);p.curveTo(-28,-45,28,-45,43,-5);p.close();c.drawPath(p);c.ellipse(-43,-12,43,2)
  p=c.beginPath();p.moveTo(0,2);p.curveTo(-24,17,-8,28,0,48);p.curveTo(17,28,26,13,0,2);p.close();c.drawPath(p)
  poly(c,[(-24,-18),(-12,-26),(0,-18),(12,-26),(24,-18)],False)
 elif name=='crescent':
  p=c.beginPath();p.moveTo(15,42);p.curveTo(-48,43,-55,-45,15,-42);p.curveTo(-19,-18,-15,23,15,42);p.close();c.drawPath(p);star(c,25,11,13)

def border(c,detailed):
 c.roundRect(37,64,538,632,18)
 if detailed:
  c.roundRect(44,71,524,618,14)
  for y in range(95,680,34):
   for x in [53,559]:c.circle(x,y,3)

def page(c,theme,detailed,number,total):
 c.setStrokeColorRGB(0,0,0);c.setFillColorRGB(0,0,0);c.setLineWidth(1)
 c.setFont('Helvetica-Bold',22);c.drawCentredString(306,746,theme['title'])
 c.setFont('Helvetica',10);c.drawCentredString(306,725,'DETAILED DESIGNS' if detailed else 'HOLIDAY COLORING - FAMILY PAGES')
 border(c,detailed)
 if detailed:
  c.saveState();c.translate(306,382)
  for radius in [109,117,217,226]:c.circle(0,0,radius)
  for k in range(12):
   a=math.radians(k*30);x,y=167*math.cos(a),167*math.sin(a)
   c.saveState();c.translate(x,y);c.rotate(k*30-90);c.scale(.77,.77);motif(c,theme['motif']);c.restoreState()
  c.saveState();c.scale(1.65,1.65);motif(c,theme['motif']);c.restoreState()
  for k in range(24):
   a=math.radians(k*15);star(c,245*math.cos(a),245*math.sin(a),6)
  c.restoreState()
 else:
  c.saveState();c.translate(306,404);c.scale(3.3,3.3);motif(c,theme['motif']);c.restoreState()
  for x,y in [(107,607),(505,607),(107,204),(505,204)]:
   c.saveState();c.translate(x,y);c.scale(.62,.62);motif(c,theme['motif']);c.restoreState()
  c.setFont('Helvetica',11);c.drawCentredString(306,115,'Choose your colors. Add a pattern. Make it yours.')
 c.setFont('Helvetica',8);c.drawCentredString(306,45,'Original Data Ark artwork - CC0 1.0 - freely copy, color and share.')
 c.setFont('Helvetica',7);c.drawString(39,30,'creativecommons.org/publicdomain/zero/1.0/');c.drawRightString(573,30,str(number)+' / '+str(total));c.showPage()

def main():
 if not OUT.parent.parent.is_mount():raise SystemExit('Content SSD must be mounted')
 OUT.mkdir(parents=True,exist_ok=True);themes=json.loads((ROOT/'deploy/reference/holiday-themes.json').read_text())['themes'];records=[]
 for detailed,name in [(False,'family'),(True,'detailed')]:
  dest=OUT/('holiday-'+name+'.pdf');temp=dest.with_suffix('.pdf.part');c=canvas.Canvas(str(temp),pagesize=letter,invariant=1)
  title='Holiday Coloring - '+('Detailed Designs' if detailed else 'Family Pages');c.setTitle(title);c.setAuthor('DEJ Software / Data Ark')
  for i,theme in enumerate(themes,1):page(c,theme,detailed,i,len(themes))
  c.save();temp.chmod(0o644);temp.replace(dest);data=dest.read_bytes()
  records.append({'id':'holiday-'+name,'title':title,'collection':'holiday-coloring','format':'pdf','filename':'holidays/'+dest.name,'status':'installed','language':'English','age':'Adults and teens / detailed designs' if detailed else 'All ages / family coloring','purpose':'Holiday coloring / '+', '.join(t['title'] for t in themes),'license':'DEJ Software / Data Ark original vector artwork. CC0 1.0 public-domain dedication. Freely copy, color, adapt and share. No agency or religious endorsement implied.','source_page':'/docs/20-Administration/FamilyResources.html','edition':'Original Ark edition 1','checked_at':datetime.now(timezone.utc).isoformat(),'bytes':len(data),'pages':len(themes),'sha256':hashlib.sha256(data).hexdigest()})
 (OUT/'sources.json').write_text(json.dumps(records,indent=2)+'\n')
 print('Built',len(records),'holiday packs;',len(themes),'pages each')
if __name__=='__main__':main()
