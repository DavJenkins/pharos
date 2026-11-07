from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.enums import TA_CENTER
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader

import argparse
parser=argparse.ArgumentParser(description='Create a public quick-start sheet with a blank code, or a private card-specific copy.')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'docs/10-User/assets/data-ark-quick-start.pdf')
parser.add_argument('--code-file',type=Path,help='Private card-specific edition only; never publish this output.')
args=parser.parse_args()
out=args.output;out.parent.mkdir(parents=True,exist_ok=True)
code=args.code_file.read_text().strip() if args.code_file else '____'
if args.code_file:assert len(code)==4 and code.isascii() and code.isdigit()
navy=colors.HexColor('#172d40');gold=colors.HexColor('#b48721');ink=colors.HexColor('#203e54')
body=ParagraphStyle('body',fontName='Helvetica',fontSize=10.2,leading=13.6,textColor=ink,spaceAfter=3.5)
heading=ParagraphStyle('heading',parent=body,fontName='Helvetica-Bold',fontSize=11.2,leading=14,spaceBefore=6,spaceAfter=4)
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

p('This microSD contains a working Data Ark. <b>No internet connection, subscription or external content drive is needed to try it.</b>')
h('What you need')
p('A <b>Raspberry Pi 4</b>, a suitable USB-C power supply (preferably the official Pi 4 supply), cooling, and a phone, tablet or laptop with Wi-Fi. An optional supported USB Wi-Fi adapter can improve range; the built-in radio is sufficient to start.')
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
p('<b>Caretaker password:</b> changes settings and manages content through the website.<br/><b>Linux admin password:</b> provides SSH and terminal access; the username is <font name="Courier">admin</font>. Root login stays disabled.')
p('Five incorrect codes trigger a one-minute pause. Successful setup retires the code. <b>Browsing the library never requires a password.</b>')
h('Explore offline')
p('The interface, handbook and material prepared for your card work locally. Library capacity and the installed selection are chosen when the card is prepared; see <b>System / Library</b> for its actual storage. The full advertised collection is not implied. No online activation is required. Internet is needed only when you choose to acquire online content or updates.')
h('Optional desktop access')
p('Attach a monitor by micro-HDMI, plus a keyboard and mouse. Use the <b>Open Data Ark</b> desktop shortcut. A monitor is not required for setup or everyday browsing.')
h('Shut down before unplugging')
p('Use the desktop shutdown menu, or run this command from a terminal or SSH:')
story.append(Paragraph('sudo shutdown -h now',mono))
p('Wait for shutdown to finish before disconnecting power or removing the microSD.')

def frame(c,doc):
 w,h=doc.pagesize
 c.setFillColor(colors.HexColor('#f0eee5'));c.roundRect(36,h-100,w-72,84,8,fill=1,stroke=0)
 assets=Path(__file__).resolve().parents[1]/'app/static/assets'
 def crop(image,x,y,width,height,cx,cy,cw,ch,iw,ih):
  c.saveState();clip=c.beginPath();clip.rect(x,y,width,height);c.clipPath(clip,stroke=0,fill=0)
  scale=width/cw;c.drawImage(ImageReader(image),x-cx*scale,y-(ih-cy-ch)*scale,width=iw*scale,height=ih*scale,mask='auto');c.restoreState()
 crop(assets/'dej-software-footer.webp',50,h-45,115,21,281,23,450,82,1000,185)
 c.linkURL('https://www.dejsoftware.com/',(50,h-45,165,h-24),relative=0)
 unit=245/4420
 crop(assets/'pharos-data-ark-clean.png',50,h-77,1800*unit,350*unit,80,115,1800,350,1967,799)
 crop(assets/'pharos-data-ark-clean.png',50+1900*unit,h-77,2520*unit,350*unit,100,480,1800,250,1967,799)
 c.setFillColor(ink);c.setFont('Helvetica-Bold',15);c.drawRightString(w-50,h-40,'MicroSD quick start')
 c.setFont('Helvetica',9);c.drawRightString(w-50,h-58,'Reference: Raspberry Pi 4')
 c.setFont('Helvetica',10);c.drawString(50,h-92,'Your offline library starts here')
 c.setStrokeColor(gold);c.setLineWidth(1);c.line(50,35,w-50,35)
 c.setFillColor(ink);c.setFont('Helvetica',8);c.drawString(50,22,'DEJ Software');c.drawString(115,22,'Online version (internet required)');c.drawRightString(w-50,22,'Keep this sheet with your card')
 c.linkURL('https://www.dejsoftware.com/',(50,18,108,31),relative=0)
 c.linkURL('https://www.dejsoftware.com/data-ark/docs/10-User/assets/data-ark-quick-start.pdf',(115,18,255,31),relative=0)

doc=SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=50,rightMargin=50,topMargin=111,bottomMargin=45,title='Pharos Data Ark - MicroSD Quick Start',author='DEJ Software')
doc.build(story,onFirstPage=frame,onLaterPages=frame)
r=PdfReader(str(out));assert len(r.pages)==1, f'Unexpected {len(r.pages)} pages'
text=r.pages[0].extract_text();assert code in text and 'sudo shutdown -h now' in text
print('Created and verified one-page PDF:',out)

