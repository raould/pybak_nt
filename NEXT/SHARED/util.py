"""Functions shared by the pybak client and server. Portable from Python 2.0 to 3.x.

The server is Python 3 only, but uses these so that both ends compute md5s and
hex names the same way. Client-only code (crawling, naming) is in CLIENT/.
"""

import portapy_sdk as ppy
import sys
# portapy_pragma ALLOW_MODULE
import binascii
# portapy_pragma ALLOW_MODULE
import pk_types as pk

# ----------------------------------------
# support MD5 file hashing.
try:
    # portapy_pragma ALLOW_MODULE
    import hashlib
    # todo: would want usedforsecurity=False (Python 3.9+) on FIPS systems
    hasher_new = hashlib.md5
    # portapy_pragma ALLOW_MODULE_END hashlib
except ImportError:
    # portapy_pragma ALLOW_MODULE
    import md5
    hasher_new = md5.new
    # portapy_pragma ALLOW_MODULE_END md5


def md5_and_length(fp, chunk_size=8192):
    hasher = hasher_new()
    count = 0
    while 1:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        count = count + len(chunk)
    return (hasher.hexdigest(), pk.PkLength(count))

# ----------------------------------------


def b2ha(b):
    # type: (ppy.PpyBytes) -> pk.PkHexName
    """hexlify() gives lowercase hex digits: ASCII bytes, so a PkHexName."""
    return pk.PkHexName(ppy.PpyAsciiBytes(binascii.hexlify(b)))


def ha2b(h):
    # type: (pk.PkHexName) -> ppy.PpyBytes
    return ppy.PpyBytes(binascii.unhexlify(h))

# ----------------------------------------
# our md5 invocation returns bytes, make it ascii hex.


def md5_b2a(digest):
    # type: (pk.PkMd5Digest) -> pk.PkMd5Hex
    return pk.PkMd5Hex(b2ha(digest))


def md5_a2b(hex_digest):
    # type: (pk.PkMd5Hex) -> pk.PkMd5Digest
    return pk.PkMd5Digest(ha2b(hex_digest))

# ---------------------------------------------------------------------------
# Names <-> hexl_path. The only place either direction happens.


def hex_name(raw):
    # type: (pk.PkWireName) -> pk.PkHexName
    return b2ha(raw)


def unhex_name(h):
    # type: (pk.PkHexName) -> pk.PkWireName
    return pk.PkWireName(ha2b(h))

# ----------------------------------------


def current_errno():
    # type: () -> pk.PkOptional[int]
    """errno of the exception being handled, or None.
    Uses sys.exc_info() because 'except E, e' (Python 2) and
    'except E as e' (Python 2.6+) have no common spelling.
    """
    return getattr(sys.exc_info()[1], 'errno', None)

# ---------------------------------------------------------------------------
# Path lists <-> hexl_path. Needs the client's naming strategy (N).


def name_to_wire_list(path_list, N):
    wire = []
    for name in path_list:
        wire.append(N.os_name_to_wire(name))
    return wire


def wire_to_name_list(wire_list, N):
    names = []
    for wire in wire_list:
        names.append(N.wire_to_os_name(wire))
    return names


def to_wire_path_list(path_list, N):
    ws = []
    for name in path_list:
        ws.append(
            N.os_name_to_wire(name)
        )
    return ws


def from_wire_path_list(wire_path_list, N):
    names = []
    for w in wire_path_list:
        names.append(
            N.wire_to_os_name(w)
        )
    return names
