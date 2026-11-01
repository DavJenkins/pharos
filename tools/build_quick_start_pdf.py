from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.enums import TA_CENTER
from pypdf import PdfReader

import argparse
parser=argparse.ArgumentParser(description='Create a public quick-start sheet with a blank code, or a private card-specific copy.')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'docs/10-User/assets/data-ark-quick-start.pdf')
parser.add_argument('--code-file',type=Path,help='Private card-specific edition only; never publish this output.')
args=parser.parse_args()
out=args.output;out.parent.mkdir(parents=True,exist_ok=True)
code=args.code_file.read_text().strip() if args.code_file else '____'
if args.code_file:assert len(code)==4 and code.isascii() and code.isdigit()
navy=colors.HexColor('#172d40');gold=colors.HexColor('#b48721');ink=colors.HexColor('#203e54')
body=ParagraphStyle('body',fontName='Helvetica',fontSize=10.2,leading=13.6,textColor=ink,spaceAfter=4.5)
heading=ParagraphStyle('heading',parent=body,fontName='Helvetica-Bold',fontSize=11.2,leading=14,spaceBefore=7,spaceAfter=5)
small=ParagraphStyle('small',parent=body,fontSize=8.4,leading=11,spaceAfter=0)
center=ParagraphStyle('center',parent=body,alignment=TA_CENTER,fontSize=10,leading=14,spaceAfter=0)
code_style=ParagraphStyle('code',parent=center,fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=navy)
mono=ParagraphStyle('mono',parent=body,fontName='Courier',fontSize=10,leading=14,backColor=colors.HexColor('#f1f3f4'),borderPadding=7,spaceAfter=8)
story=[]
def p(text):story.append(Paragraph(text,body))
def h(text):story.append(Paragraph(text,heading))
def step(n,text):
 t=Table([[Paragraph(str(n)+'.',ParagraphStyle('n',parent=body,fontName='Helvetica-Bold',textColor=gold)),Paragraph(text,body)]],colWidths=[19,493])
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),3)]));story.append(t)

p('This microSD contains a working Data Ark and a small offline demonstration library. <b>No internet connection, subscription or external content drive is needed to try it.</b>')
h('What you need')
p('A <b>Raspberry Pi 4</b>, a suitable USB-C power supply (preferably the official Pi 4 supply), a case with cooling, and a phone, tablet or laptop with Wi-Fi.')
h('Start your Ark')
step(1,'With the Pi unplugged, insert the microSD into its underside slot.')
step(2,'Connect power. Leave Ethernet disconnected for an entirely offline demonstration. Allow a few minutes for the first startup.')
step(3,'Connect your phone or computer to <b>DataArk</b> Wi-Fi. It is an open network. If your device reports "No internet," choose to stay connected.')
step(4,'Open <b><link href="http://192.168.4.1/" color="#075a96">http://192.168.4.1/</link></b>. A network sign-in notification may also open the Ark.')
h('Make it yours')
p('Follow the setup banner and enter the pairing code below. Keep any leading zeroes. Complete setup privately, before inviting other users: the initial hotspot/HTTP exchange is not encrypted.')
box=Table([[Paragraph('ONE-TIME SETUP CODE - FOR THIS CARD',center),Paragraph(code,code_style)]],colWidths=[360,152])
box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#fbf4de')),('BOX',(0,0),(-1,-1),1,gold),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
story.append(box);story.append(Spacer(1,8))
p('Choose <b>two passwords, each at least 12 characters</b>:')
p('<b>Caretaker password:</b> changes settings and manages content through the website.<br/><b>Linux admin password:</b> provides SSH and terminal access; the username is <b>admin</b>. Root login stays disabled.')
p('Five incorrect codes trigger a one-minute pause. Successful setup retires the code. <b>Browsing the library never requires a password.</b>')
h('Explore offline')
p('The card includes a Wikipedia sample, documentation about the Ark and its collection, and the working interface and tools. It reserves <b>80 GiB for library content</b>; it does not contain the full advertised collection. It requires no online activation and can remain disconnected from the internet. Internet access is needed only when you choose to acquire online content or updates.')
h('Optional desktop access')
p('Attach a monitor by micro-HDMI, plus a keyboard and mouse. Use the <b>Open Data Ark</b> desktop shortcut. A monitor is not required for setup or everyday browsing.')
h('Shut down before unplugging')
p('Use the desktop shutdown menu, or run this command from a terminal or SSH:')
story.append(Paragraph('sudo shutdown -h now',mono))
p('Wait for shutdown to finish before disconnecting power or removing the microSD.')

def frame(c,doc):
 w,h=doc.pagesize
 c.setFillColor(navy);c.rect(0,h-96,w,96,fill=1,stroke=0)
 c.setFillColor(colors.HexColor('#e4bd55'));c.setFont('Helvetica-Bold',11);c.drawString(50,h-29,'PHAROS DATA ARK')
 c.setFillColor(colors.white);c.setFont('Helvetica-Bold',22);c.drawString(50,h-59,'Your offline library starts here')
 c.setFont('Helvetica',10);c.drawString(50,h-79,'MicroSD quick start  |  Raspberry Pi 4')
 c.setStrokeColor(gold);c.setLineWidth(2);c.line(0,h-97,w,h-97)
 c.setStrokeColor(colors.HexColor('#d5c79f'));c.setLineWidth(.5);c.line(50,35,w-50,35)
 c.setFillColor(ink);c.setFont('Helvetica',8);c.drawString(50,22,'DEJ Software | Online version (internet required)');c.drawRightString(w-50,22,'Keep this sheet with your card')
 c.linkURL('https://www.dejsoftware.com/data-ark/docs/10-User/assets/data-ark-quick-start.pdf',(50,18,215,30),relative=0)

doc=SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=50,rightMargin=50,topMargin=111,bottomMargin=45,title='Pharos Data Ark - MicroSD Quick Start',author='DEJ Software')
doc.build(story,onFirstPage=frame,onLaterPages=frame)
r=PdfReader(str(out));assert len(r.pages)==1, f'Unexpected {len(r.pages)} pages'
text=r.pages[0].extract_text();assert code in text and 'sudo shutdown -h now' in text
print('Created and verified one-page PDF:',out)

