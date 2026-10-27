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


def md5_hex(digest):
    # type: (pk.PkMd5Digest) -> pk.PkMd5Hex
    return pk.PkMd5Hex(_hexlify(digest))

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
