import portapy_sdk as ppy
import os
#portapy_pragma ALLOW_MODULE
import pk_types as pk
#portapy_pragma ALLOW_MODULE
import naming
#portapy_pragma ALLOW_MODULE
import re
#portapy_pragma ALLOW_MODULE
import metadata_constants as mdc
#portapy_pragma ALLOW_MODULE
import filename_util as fe

#----------------------------------------
# todo: convert all of this to handle the binary paths!!!!!!!!!!!!!!
#
# path: a PkOsPath (a list of names, root first). N: the Naming instance from
# naming.choose_naming(). Names are compared with constants only through N
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

def smells_like_browse( path_list, N ):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> int
    path = N.os_join_path( path_list )
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
    except UnicodeDecodeError:
        return 0
    finally:
        f.close()
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
