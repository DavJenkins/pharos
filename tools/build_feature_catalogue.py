from pathlib import Path
import json,re
from xml.sax.saxutils import escape
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, NextPageTemplate, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from catalogue_artwork import cover_image
import argparse
parser=argparse.ArgumentParser(description='Build the Data Ark capability catalogue (requires reportlab).')
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'app/static/feature-catalogue.pdf')
args=parser.parse_args()
R=Path(__file__).resolve().parents[1]
data=json.loads((R/'docs/10-User/FeatureCatalogue.json').read_text(encoding='utf-8'))
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
 canvas.setFillColor(CREAM);canvas.setFont('Ark',12);canvas.drawString(42,H-54,'WHAT IT CAN DO / THE CAPABILITIES BEHIND THE COLLECTION')
 canvas.setStrokeColor(GOLD);canvas.line(42,43,W-42,43)
 canvas.setFont('Ark',8);canvas.setFillColor(GRAY);canvas.drawString(42,29,'DEJ SOFTWARE  |  '+data['edition'].split('|')[-1].strip().upper());canvas.drawRightString(W-42,29,str(doc.page))
def cover(canvas,doc):
 canvas.setFillColor(BLUE);canvas.rect(0,0,W,H,fill=1,stroke=0)
 canvas.setStrokeColor(GOLD);canvas.setLineWidth(1);canvas.rect(27,27,W-54,H-54,fill=0,stroke=1)
 logo=R/'app/static/assets/pharos-data-ark-flat.png'
 if logo.exists():canvas.drawImage(cover_image(logo),80,578,width=452,height=184,mask='auto',preserveAspectRatio=True,anchor='c')
 canvas.setFillColor(HexColor('#d4af37'));canvas.setFont('ArkBold',10);canvas.drawString(58,55,'DEJ SOFTWARE');canvas.setFont('Ark',9);canvas.drawRightString(W-58,55,'PRACTICAL SOFTWARE FOR REAL LIFE')

path=args.output
path.parent.mkdir(parents=True,exist_ok=True)
md=['# PHAROS Data Ark — What it can do', '', '*'+data['edition']+'*', '', '[Download the feature catalogue (PDF)](../../feature-catalogue.pdf) · [Companion: The Collection](CollectionCatalogue.md)', '', data['intro'], '', data['scope'], '', 'For the internal mechanisms and design decisions, see [Engineering behind the Ark](../30-Developer/Engineering.md).', '', '## At a glance', '']
for section in data['sections']:
    md.append(str(section['number'])+'. '+section['title'])
for section in data['sections']:
    md += ['', '## '+str(section['number'])+'. '+section['title'], '', '*'+section['hook']+'*', '']
    md += ['- '+item for item in section['items']]
    md += ['', '[Operating details]('+section['guide']+')']
md += ['', '## Practical limits', '']+['- '+item for item in data['limits']]
md += ['', 'This catalogue describes the implemented capabilities at the edition date. The operating guides and configured hardware determine the available settings on a particular Ark.', '']
(R/'docs/10-User/FeatureCatalogue.md').write_text('\n'.join(md),encoding='utf-8')
doc=BaseDocTemplate(str(path),pagesize=(W,H),title='Pharos Data Ark - What it can do',author='DEJ Software',allowSplitting=1)
frames=[Frame(42,59,255,635,id='left',leftPadding=0,rightPadding=8,topPadding=0,bottomPadding=0),Frame(315,59,255,635,id='right',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)]
doc.addPageTemplates([PageTemplate(id='cover',frames=[Frame(58,85,496,468,id='coverbody',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=cover),PageTemplate(id='inside',frames=frames,onPage=bg)])
story=[p('More than a library.','cover'),p(data['tagline'],'covergold'),p(data['intro'],'coverbody'),p(str(len(data['sections']))+' capability areas. One shared local resource.','covergold'),p('Connect. Share. Create. Coordinate. Maintain. Rebuild.','coverbody'),p(data['edition'],'coverbody'),NextPageTemplate('inside'),PageBreak(),p('What the Ark can do','head'),p(data['scope'],'tool')]
for section in data['sections']:
    story += [p(str(section['number']).zfill(2)+'  '+section['title'],'head'),p(section['hook'],'hook')]
    story += [p('• '+item,'bullet') for item in section['items']]
story += [p('Practical limits','head')]+[p('• '+item,'bullet') for item in data['limits']]
story += [p('Explore the operating guides','head'),p('The editable web edition links each capability area to its operating guide. Open the Ark documentation and choose “What the Ark can do.” The companion collection catalogue describes the saved knowledge itself.','tool'),p('DEJ Software | dejsoftware.com','small')]
doc.build(story)
print('Created',path)
print(len(data['sections']),'areas;',sum(len(s['items']) for s in data['sections']),'feature descriptions')
