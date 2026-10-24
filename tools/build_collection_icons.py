#!/usr/bin/env python3
"""Render original Data Ark collection pictograms; no external assets or fonts."""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
ICONS = {
    'ifixit': ('Repair', '#245b8a'),
    'preparedness': ('Preparedness', '#b04435'),
    'forms-templates': ('Forms', '#386e74'),
    'family-resources': ('Family', '#875a98'),
    'resilience': ('Resilience', '#43764e'),
    'civic-reference': ('Civic', '#876435'),
    'radio-study': ('Radio', '#345e98'),
    'drinking-water': ('Water', '#286b9a'),
    'shelter-winter': ('Shelter', '#4b6389'),
    'first-aid-care': ('Care', '#667d61'),
    'sanitation': ('Sanitation', '#3a6e78'),
}
def render(name, color):
    image = Image.new('RGBA', (256, 256))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((8, 8, 248, 248), radius=44, fill=color)
    ink = '#fffdf5'
    def line(points, width=10): d.line(points, fill=ink, width=width, joint='curve')
    if name == 'Repair':
        # Open-ended spanner, screwdriver, and repair fastener.
        line([(62, 63), (62, 100), (92, 121), (117, 100), (117, 63)])
        line([(90, 120), (90, 195)], 17)
        d.ellipse((78, 177, 102, 201), outline=ink, width=7)
        line([(166, 62), (166, 130)], 12)
        d.rounded_rectangle((150, 125, 182, 197), radius=10, outline=ink, width=8)
    elif name == 'Preparedness':
        d.rounded_rectangle((50, 91, 206, 190), radius=14, outline=ink, width=9)
        line([(100, 90), (100, 65), (156, 65), (156, 90)], 8)
        d.rectangle((119, 110, 137, 170), fill=ink)
        d.rectangle((98, 131, 158, 149), fill=ink)
    elif name == 'Forms':
        d.rounded_rectangle((65, 43, 191, 213), radius=8, outline=ink, width=8)
        for y in [85, 129, 173]:
            d.rectangle((85, y-7, 101, y+9), outline=ink, width=4)
            line([(116,y+1), (170,y+1)], 6)
    elif name == 'Family':
        # Crayon and paper, with a playful star.
        d.rounded_rectangle((47, 48, 151, 205), radius=7, outline=ink, width=7)
        d.polygon([(97,73),(106,94),(129,96),(112,111),(117,134),(97,122),(77,134),(82,111),(65,96),(88,94)], outline=ink, width=5)
        d.polygon([(155,169),(181,70),(202,76),(176,175),(158,195)], outline=ink, width=7)
        line([(158,156),(180,162)], 6)
    elif name == 'Resilience':
        d.polygon([(38,192),(99,86),(155,192)], outline=ink, width=8)
        line([(99,86),(99,192)], 6)
        d.ellipse((162,51,198,87), outline=ink, width=7)
        for a,b in [((180,32),(180,42)),((180,96),(180,106)),((143,69),(153,69)),((207,69),(217,69))]:line([a,b],5)
        d.polygon([(181,125),(161,162),(178,162),(168,201),(204,149),(185,149)], fill=ink)
    elif name == 'Civic':
        d.polygon([(45,83),(128,43),(211,83)], outline=ink, width=7)
        line([(45,94),(211,94)],7)
        for x in [72,110,148,186]:line([(x,107),(x,181)],10)
        line([(51,191),(205,191)],8);line([(40,208),(216,208)],8)
    elif name == 'Radio':
        d.rounded_rectangle((60,111,196,201), radius=13, outline=ink, width=8)
        line([(95,110),(77,50)],7)
        d.rounded_rectangle((80,130,146,152),radius=3,outline=ink,width=5)
        d.ellipse((160,129,182,151),outline=ink,width=5)
        for y in [172,184]:line([(81,y),(144,y)],5)
        d.arc((114,39,213,138),220,317,fill=ink,width=7)
        d.arc((130,55,197,122),220,317,fill=ink,width=7)
    elif name == 'Water':
        d.polygon([(128,39),(73,118),(61,151),(64,177),(81,199),(104,211),(151,211),(177,197),(193,173),(195,149),(181,117)],fill=ink)
        d.arc((84,133,169,191),20,135,fill=color,width=9)
    elif name == 'Shelter':
        line([(40,126),(128,49),(216,126)],10)
        line([(61,114),(61,207),(195,207),(195,114)],9)
        d.rectangle((111,149,146,207),outline=ink,width=7)
        for x,y in [(78,155),(173,157)]:
            line([(x-13,y),(x+13,y)],5);line([(x,y-13),(x,y+13)],5)
    elif name == 'Care':
        d.ellipse((75,58,133,116),fill=ink);d.ellipse((123,58,181,116),fill=ink)
        d.polygon([(76,95),(180,95),(128,159)],fill=ink)
        line([(49,161),(80,191),(175,191),(207,160)],12)
    elif name == 'Sanitation':
        d.rounded_rectangle((48,135,208,207),radius=24,outline=ink,width=8)
        d.ellipse((82,151,174,187),outline=ink,width=6)
        for x,y,r in [(78,107,12),(118,72,15),(172,109,10)]:d.ellipse((x-r,y-r,x+r,y+r),outline=ink,width=6)
    return image.resize((128,128),Image.Resampling.LANCZOS)
if __name__ == '__main__':
    out=ROOT/'app/static/assets/icons'
    for _,(name,color) in ICONS.items(): render(name,color).save(out/(name+'.png'))
