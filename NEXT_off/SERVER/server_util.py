gChecksumSplitLength = 2

def get_data_path_list( checksum ):
    if len(checksum) != 32:
        raise Exception("invalid checksum length")
    mids = []
    for i in range( 0, len(checksum), gChecksumSplitLength ):
        mids.append( checksum[ i : i+gChecksumSplitLength ] )
    return mids
