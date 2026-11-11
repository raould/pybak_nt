import os

CHECKSUM_SLIT_LENGTH = 2
METADATA_JSON_EXT = 'mdj'


def get_data_path_list(checksum):
    if len(checksum) != 32:
        raise Exception("invalid checksum length")
    mids = []
    for i in range(0, len(checksum), CHECKSUM_SLIT_LENGTH):
        mids.append(checksum[i: i+CHECKSUM_SLIT_LENGTH])
    return mids


def canonical_path_for(croot, md5, length):
    filename = '%s_%s' % (md5, length)
    p = os.path.join(*get_data_path_list(md5))
    cpl = os.path.join(croot, p, filename)
    return cpl


def metadata_filename_for(croot):
    return '%s.%s' % (croot, METADATA_JSON_EXT)
