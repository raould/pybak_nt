import portapy_sdk as ppy
import os
#portapy_pragma ALLOW_MODULE
import pk_types as pk
#portapy_pragma ALLOW_MODULE
import metadata_constants as mdc
#portapy_pragma ALLOW_MODULE
import client_util as cu
#portapy_pragma ALLOW_MODULE
import filename_util as fe

#----------------------------------------
# todo: convert all of this to handle the binary paths!!!!!!!!!!!!!!
#
# path_list: a PkOsPath (a list of names, root first). N: the naming strategy
# (pk.PkNamingP). Names are compared with constants only through N
# (N.has_suffix, N.ascii_to_os_name), so both sides are the same type (bytes,
# or text under win-utf16le).

def smells_like_canonical( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> int
    path = N.os_join_path( path_list )
    if not os.path.exists( path ):
        return 0
    if smells_like_any_metadata( path_list, N ):
        return 0
    checksum = fe.get_checksum_from_path_list( path_list, N )
    length = fe.get_length_from_path_list( path_list, N )
    return checksum != None and length != None

# Markers that pybak's own browse pages carry. Looked for in the first
# BROWSE_SNIFF_BYTES only, as ASCII bytes: no decoding, no regular expressions.
BROWSE_MARKERS = ('psync-o-pathics.com/canonical', 'psync-o-pathics.com/browse', '<!-- mark -->')
BROWSE_SNIFF_BYTES = 65536

def smells_like_browse( path_list, target_stat, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkStat, pk.PkNamingP[pk.PkOsName]) -> int
    """True if the file starts like one of pybak's own browse pages.

    Only call this for an entry the policy said to 'read': it opens the file
    with cu.open_for_read (non-blocking, checked against target_stat), so a
    FIFO, a device or a swapped file is never read, and it reads at most
    BROWSE_SNIFF_BYTES."""
    opened = cu.open_for_read( path_list, target_stat, N )
    fp = opened['fp']
    if fp is None:
        return 0
    try:
        head = fp.read( BROWSE_SNIFF_BYTES )
    finally:
        fp.close()
    for marker in BROWSE_MARKERS:
        if head.find( ppy.a2b( marker ) ) >= 0:
            ppy.prnt('skipping \'browse\' file', repr( N.os_join_path( path_list ) ))
            return 1
    return 0

#----------------------------------------
# note: technically we only support ASCII file extensions
# because it is the lowest common denominator.

def smells_like_any_metadata( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> int
    return _smells_like_metadata_exts( path_list, N, [mdc.PICKLE_DOTEXT, mdc.JSON_DOTEXT] )

def smells_like_pickled_metadata( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> int
    return _smells_like_metadata_exts( path_list, N, [mdc.PICKLE_DOTEXT] )

def smells_like_json_metadata( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> int
    return _smells_like_metadata_exts( path_list, N, [mdc.JSON_DOTEXT] )

def _smells_like_metadata_exts( path_list, N, exts ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName], pk.PkList[ppy.PpyAsciiStr]) -> int
    if not os.path.exists( N.os_join_path( path_list ) ):
        return 0
    for e in exts:
        if N.has_suffix( path_list[-1], e ):
            return 1
    return 0
