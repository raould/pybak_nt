"""Functions shared by the pybak client and server. Portable from Python 2.0 to 3.x.

The server is Python 3 only, but uses these so that both ends compute md5s and
hex names the same way. Client-only code (crawling, naming) is in CLIENT/.
"""

import portapy_sdk as ppy
import sys
#portapy_pragma ALLOW_MODULE
import binascii
#portapy_pragma ALLOW_MODULE
import pk_types as pk

#----------------------------------------
# support MD5 file hashing.
try:
    #portapy_pragma ALLOW_MODULE
    import hashlib
    # todo: would want usedforsecurity=False (Python 3.9+) on FIPS systems
    hasher_new = hashlib.md5
    #portapy_pragma ALLOW_MODULE_END hashlib
except ImportError:
    #portapy_pragma ALLOW_MODULE
    import md5
    hasher_new = md5.new
    #portapy_pragma ALLOW_MODULE_END md5


def md5_and_length(fp, chunk_size=8192):
    # type: (pk.PkAny, int) -> pk.PkTuple[pk.PkMd5Digest, pk.PkLength]
    hasher = hasher_new()
    count = 0
    while 1:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        count = count + len(chunk)
    return (pk.PkMd5Digest(hasher.digest()), pk.PkLength(count))


def _hexlify(b):
    # type: (ppy.PpyBytes) -> pk.PkHexName
    """hexlify() gives lowercase hex digits: ASCII bytes, so a PkHexName."""
    return pk.PkHexName(ppy.PpyAsciiBytes(binascii.hexlify(b)))

def _unhexlify(h):
    # type: (pk.PkHexName) -> ppy.PpyBytes
    return ppy.PpyBytes(binascii.unhexlify(h))

# ----------------------------------------
# our md5 invocation returns bytes, make it ascii hex.

def md5_hex(digest):
    # type: (pk.PkMd5Digest) -> pk.PkMd5Hex
    return pk.PkMd5Hex(_hexlify(digest))

def md5_unhex(hex_digest):
    # type: (pk.PkMd5Hex) -> pk.PkMd5Digest
    return pk.PkMd5Digest(_unhexlify(hex_digest))

# ---------------------------------------------------------------------------
# Names <-> hexl_path. The only place either direction happens.

def hex_name(raw):
    # type: (pk.PkWireName) -> pk.PkHexName
    return _hexlify(raw)


def unhex_name(h):
    # type: (pk.PkHexName) -> pk.PkWireName
    return pk.PkWireName(binascii.unhexlify(h))


#----------------------------------------

def current_errno():
    # type: () -> pk.PkOptional[int]
    """errno of the exception being handled, or None.
    Uses sys.exc_info() because 'except E, e' (Python 2) and
    'except E as e' (Python 2.6+) have no common spelling.
    """
    return getattr(sys.exc_info()[1], 'errno', None)


# ---------------------------------------------------------------------------
# Path lists <-> hexl_path. Needs the client's naming strategy (N).

def to_hex_path_list(path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkHexPath
    """PkOsPath -> PkHexPath, element by element, root first."""
    hexes = []  # type: pk.PkList[pk.PkHexName]
    for name in path_list:
        hexes.append(
            util.hex_name(
                N.os_name_to_wire(name)
                )
            )
    return pk.PkHexPath(hexes)


def from_hex_path_list(hex_path_list, N):
    # type: (pk.PkHexPath, pk.PkNamingP[pk.PkOsName]) -> pk.PkOsPath[pk.PkOsName]
    """Exact inverse of to_hex_path_list() for the client that made it: the server never calls this."""
    names = []  # type: pk.PkOsPath[pk.PkOsName]
    for h in hex_path_list:
        names.append(
            N.wire_to_os_name(
                util.unhex_name(h)
                )
            )
    return names
