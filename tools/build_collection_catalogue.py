from pathlib import Path
import json,re
from xml.sax.saxutils import escape
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, NextPageTemplate, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import argparse
parser=argparse.ArgumentParser(description='Build the standalone Data Ark collection catalogue (requires reportlab).')
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'app/static/collection-catalogue.pdf')
args=parser.parse_args()
R=Path(__file__).resolve().parents[1]
data=json.loads((R/'docs/10-User/CollectionCatalogue.json').read_text(encoding='utf-8'))
fonts=Path('C:/Windows/Fonts')
if fonts.exists():
    variants=[('Ark','arial.ttf'),('ArkBold','arialbd.ttf'),('ArkItalic','ariali.ttf')]
else:
    fonts=Path('/usr/share/fonts/truetype/dejavu')
    variants=[('Ark','DejaVuSans.ttf'),('ArkBold','DejaVuSans-Bold.ttf'),('ArkItalic','DejaVuSans-Oblique.ttf')]
for name,file in variants:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
BLUE=HexColor('#203e54');GOLD=HexColor('#b99138');INK=HexColor('#243544');CREAM=HexColor('#fbf9f3');GRAY=HexColor('#546470')
W,H=612,792
styles={
 'head':ParagraphStyle('head',fontName='ArkBold',fontSize=14,leading=17,textColor=BLUE,spaceBefore=14,spaceAfter=6,keepWithNext=True),
 'hook':ParagraphStyle('hook',fontName='ArkItalic',fontSize=10,leading=14,textColor=GRAY,spaceAfter=8,keepWithNext=True),
 'bullet':ParagraphStyle('bullet',fontName='Ark',fontSize=10,leading=14,textColor=INK,leftIndent=9,firstLineIndent=-9,spaceAfter=4),
 'small':ParagraphStyle('small',fontName='Ark',fontSize=8.2,leading=11,textColor=GRAY,spaceAfter=5),
 'tool':ParagraphStyle('tool',fontName='Ark',fontSize=10,leading=14,textColor=INK,spaceAfter=6),
 'cover':ParagraphStyle('cover',fontName='ArkBold',fontSize=32,leading=38,textColor=CREAM,spaceAfter=20),
 'coverbody':ParagraphStyle('coverbody',fontName='Ark',fontSize=13,leading=20,textColor=CREAM,spaceAfter=17),
 'covergold':ParagraphStyle('covergold',fontName='ArkBold',fontSize=16,leading=21,textColor=HexColor('#e0bd68'),spaceAfter=18),
}
def clean(s):return s.replace('\u2014',' - ').replace('\u2013','-').replace('\u2011','-').replace('\u2019',"'").replace('\u201c','"').replace('\u201d','"')
def p(text,style):return Paragraph(escape(clean(text)),styles[style])
def bg(canvas,doc):
 canvas.setFillColor(CREAM);canvas.rect(0,0,W,H,fill=1,stroke=0)
 canvas.setFillColor(BLUE);canvas.rect(0,H-82,W,82,fill=1,stroke=0)
 canvas.setFillColor(HexColor('#dfbb65'));canvas.setFont('ArkBold',10);canvas.drawString(42,H-29,'PHAROS  /  DATA ARK')
 canvas.setFillColor(CREAM);canvas.setFont('Ark',12);canvas.drawString(42,H-54,'THE COLLECTION / PRESERVED ON THE ARK')
 canvas.setStrokeColor(GOLD);canvas.line(42,43,W-42,43)
 canvas.setFont('Ark',8);canvas.setFillColor(GRAY);canvas.drawString(42,29,'DEJ SOFTWARE  |  COLLECTION SNAPSHOT: OCTOBER 26, 2026');canvas.drawRightString(W-42,29,str(doc.page))
def cover(canvas,doc):
 canvas.setFillColor(BLUE);canvas.rect(0,0,W,H,fill=1,stroke=0)
 canvas.setStrokeColor(GOLD);canvas.setLineWidth(1);canvas.rect(27,27,W-54,H-54,fill=0,stroke=1)
 logo=R/'app/static/assets/pharos-data-ark-flat.png'
 if logo.exists():canvas.drawImage(ImageReader(str(logo)),80,578,width=452,height=184,mask='auto',preserveAspectRatio=True,anchor='c')
 canvas.setFillColor(HexColor('#d4af37'));canvas.setFont('ArkBold',10);canvas.drawString(58,55,'DEJ SOFTWARE');canvas.setFont('Ark',9);canvas.drawRightString(W-58,55,'PRACTICAL SOFTWARE FOR REAL LIFE')
page_names={2:'KNOWLEDGE, REPAIRS AND MAPS',3:'PREPAREDNESS, PAPERWORK AND LEARNING',4:'FIELD SKILLS, POWER, LAW AND RADIO',5:'FOOD, WATER, SHELTER AND CARE',6:'GARDENS, ANIMALS AND HOUSEHOLD RESILIENCE'}
path=args.output
path.parent.mkdir(parents=True,exist_ok=True)
doc=BaseDocTemplate(str(path),pagesize=(W,H),title='Pharos Data Ark - The Collection',author='DEJ Software',allowSplitting=1)
frames=[Frame(42,59,255,635,id='left',leftPadding=0,rightPadding=8,topPadding=0,bottomPadding=0),Frame(315,59,255,635,id='right',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]
doc.addPageTemplates([PageTemplate(id='cover',frames=[Frame(58,85,496,468,id='coverbody',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=cover),PageTemplate(id='inside',frames=frames,onPage=bg)])
story=[p('An extraordinary collection.\nReady without the internet.','cover'),p('An encyclopedia. A library of books. A repair bench, map cabinet, classroom and emergency reference shelf. All on one local device.','coverbody'),p('23 collections  /  50-state street maps\n1,391 preserved archives, publications, datasets and packs','covergold'),p('Read. Search. Repair. Learn. Prepare. Create.','coverbody'),p('Connect to the Ark and open a browser. Useful knowledge stays within reach when the internet is unavailable.','coverbody'),NextPageTemplate('inside'),PageBreak()]
groups=[list(range(1,24))]
for gi,group in enumerate(groups):
 for n in group:
  c=data['cards'][n-1];story += [p(str(n).zfill(2)+'  '+c['title'],'head'),p(c['hook'],'hook')]
  for item in c['items']:story.append(p('- '+item,'bullet'))
  if c['tools']:
   story.append(p('LOCAL TOOLS','small'))
   for item in c['tools']:story.append(p(item,'tool'))
 if False:
  story += [Spacer(1,10),p('A library within the library','head'),p('A single searchable archive contains an entire body of material. The 1,391-item inventory is not a count of individual books, articles, map features or pages. Wikipedia, WikiMed, iFixit and Project Gutenberg each open into much larger collections.','tool')]
 if False:story.append(p('The vehicle files are owner manuals and quick guides. Street maps are not nautical charts or a routing service. Massachusetts layers retain their regional scope.','small'))
 if False:story.append(p('State constitutional snapshots are not complete state statute books. Code files are the named amendments and references, not a complete licensed building-code library.','small'))
 if gi==len(groups)-1:
  story += [Spacer(1,10),p('A resource for the community','head'),p('The local community board supports announcements, requests, offers and conversations, even without upstream internet. Practical browser tools sit alongside the saved knowledge.','tool'),p('About this edition','head'),p('This catalogue describes installed content as of October 26, 2026. Uninstalled wishlist items and blocked acquisition attempts are excluded. Saved material retains its source edition; freshness varies. Original publisher rights and individual notices apply.','small'),p('DEJ Software | dejsoftware.com','small')]
 if gi<len(groups)-1:story.append(PageBreak())
doc.build(story)
print('Created',path)
