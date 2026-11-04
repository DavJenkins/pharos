"""Build the OFL-derived Data Ark Blackletter with an unmistakable lowercase k.

Requires fontTools. All other glyph outlines and metrics are preserved.
The reserved upstream family name is not used for the modified font.
"""
from pathlib import Path
import hashlib,json,shutil
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'app/static/assets/fonts/unifrakturcook'
DEST=ROOT/'app/static/assets/fonts/data-ark-blackletter'

def build():
    font=TTFont(SOURCE/'UnifrakturCook-Bold.ttf',recalcTimestamp=False)
    pen=TTGlyphPen(None)
    # Keep the ascender and diamond foot characteristic of the source family.
    # Two clearly separated diagonal strokes replace its f-like loop/crossbar.
    for points in [
        [(426,1535),(96,1356),(135,1294),(146,1114),(139,444),(139,336),(30,240),(324,15),(546,259),(412,326),(386,437),(460,530),(710,15),(885,190),(560,650),(898,920),(746,1080),(390,660),(396,1301)],
    ]:
        pen.moveTo(points[0])
        for point in points[1:]:pen.lineTo(point)
        pen.closePath()
    glyph=pen.glyph();glyph.recalcBounds(font['glyf']);font['glyf']['k']=glyph
    font['hmtx']['k']=(930,30)
    names={1:'Data Ark Blackletter',2:'Bold',3:'DEJ:DataArkBlackletter-Bold:1.0',4:'Data Ark Blackletter Bold',6:'DataArkBlackletter-Bold',16:'Data Ark Blackletter',17:'Bold'}
    for record in font['name'].names:
        if record.nameID in names:record.toUnicode();record.string=names[record.nameID].encode(record.getEncoding(),errors='replace')
    DEST.mkdir(parents=True,exist_ok=True)
    path=DEST/'DataArkBlackletter-Bold.ttf';font.save(path)
    shutil.copy2(SOURCE/'OFL.txt',DEST/'OFL.txt')
    (DEST/'source.json').write_text(json.dumps({'family':'Data Ark Blackletter','derived_from':'UnifrakturCook Bold','upstream':json.loads((SOURCE/'source.json').read_text()),'modification':'Lowercase k has explicit upper and lower diagonals; other glyph outlines unchanged. Modified family renamed under OFL reserved-name requirements.','build_script':'tools/build_ark_blackletter.py','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'license':'SIL Open Font License 1.1'},indent=2)+'\n')
    return path

if __name__=='__main__':print(build())
