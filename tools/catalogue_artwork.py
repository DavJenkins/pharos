from pathlib import Path
from PIL import Image
import io
from reportlab.lib.utils import ImageReader

def cover_image(path):
    """Embed the cover lettering as a compact JPEG against its actual navy backdrop."""
    with Image.open(path) as source:
        image=source.convert('RGBA')
    background=Image.new('RGBA',image.size,'#203e54')
    background.alpha_composite(image)
    stream=io.BytesIO()
    background.convert('RGB').save(stream,format='JPEG',quality=90,optimize=True)
    stream.seek(0)
    return ImageReader(stream)
