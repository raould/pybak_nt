from PIL import ImageFont
import sys

FONT_NAME="m821bt.ttf"
FONT_SIZE=16

def get_font():
    try:
        font = ImageFont.truetype( FONT_NAME, FONT_SIZE )
        if( not font ):
            raise MissingFont
    except Exception as e:
        sys.stderr.write( "Couldn't load font %s: %s\n" % (FONT_NAME, e) )
        raise e
    return font
