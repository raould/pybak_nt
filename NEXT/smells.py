import sys
import os

#portapy_pragma ALLOW_MODULE
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

#portapy_pragma ALLOW_MODULE
import metadata_constants as mdc

def smells_like_canonical( path ):
    if not os.path.exists( path ):
        return 0
    if smells_like_any_metadata( path ):
        return 0
    checksum = get_checksum_from_path( path )
    length = get_length_from_path( path )
    return checksum != None and length != None

def smells_like_browse( path ):
    if not os.path.exists( path ):
        return 0
    f = open(path)
    try:
        for line in f:
                c = re.search( r'psync-o-pathics.com/canonical', line ) != None
                b = re.search( r'psync-o-pathics.com/browse', line ) != None
                t = re.search( r'<!-- mark -->', line ) != None
                if c or b or t:
                   return 1
        return 0
    finally:
        f.close()

def smells_like_any_metadata( path ):
    return _smells_like_metadata_exts( path, [mdc.PICKLE_DOTEXT, mdc.JSON_DOTEXT] )

def smells_like_pickled_metadata( path ):
    return _smells_like_metadata_exts( path, [mdc.PICKLE_DOTEXT] )

def smells_like_json_metadata( path ):
    return _smells_like_metadata_exts( path, [mdc.JSON_DOTEXT] )

def _smells_like_metadata_exts_reducer( path, exts ):
    return r or path.endswith(e)
def _smells_like_metadata_exts( path, exts ):
    if not os.path.exists( path ):
        return 0
    return reduce(_smells_like_metadata_exts_reducer, exts, 0 )
