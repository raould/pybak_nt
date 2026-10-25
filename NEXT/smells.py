def smells_like_canonical( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    if smells_like_any_metadata( path ):
        return False
    checksum = get_checksum_from_path( path )
    length = get_length_from_path( path )
    return checksum != None and length != None

def smells_like_browse( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    with open( path ) as f:
        for line in f:
            c = re.search( r'psync-o-pathics.com/canonical', line ) != None
            b = re.search( r'psync-o-pathics.com/browse', line ) != None
            t = re.search( r'<!-- mark -->', line ) != None
            if c or b or t:
               return True
    return False

def smells_like_any_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.PICKLE_DOTEXT, metadata.JSON_DOTEXT] )

def smells_like_pickled_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.PICKLE_DOTEXT] )

def smells_like_json_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.JSON_DOTEXT] )

def _smells_like_metadata_exts( path, exts ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    return reduce( lambda r,e: r or path.endswith(e), exts, False )
