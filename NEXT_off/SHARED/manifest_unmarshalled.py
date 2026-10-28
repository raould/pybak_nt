"""Reading a manifest: what the client sends to the server's /sync, one per directory.

Portable from Python 2.0 to 3.x, typed with type comments. The client builds
manifests (CLIENT/client.py: manifest_header, Manifest); both ends read them
with this, so the format is defined once.

    {'bmetadata': {'name_kind': ..., 'fs_codec': ..., ...},     the header
     'entries': [{'hexl_path': [hex, ...], 'md5': hex, 'length': n,
                  'metadata': {'lstat': {...}, 'stat': {...}}}, ...]}
"""

import portapy_sdk as ppy
#portapy_pragma ALLOW_MODULE
import pk_types as pk


class ManifestUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        """Decode and check the outer shape. Raises ValueError/TypeError/KeyError if malformed."""
        init = ppy.bv_dict(ppy.bdecode(data))
        # everything looks to decode into bytes, so text (e.g. md5 hexl ascii) is bytes.
        self.bmetadata = ppy.bd_get_dict(init, 'bmetadata')
        ppy.prnt("mfu bmetadata", init)
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]
        for e in ppy.bd_get_list(init, 'entries'):
            self.entries.append(e)
    def get_name_kind(self):
        # type: () -> ppy.PpyAsciiStr
        return ppy.b2a(ppy.bd_get_bytes(self.bmetadata, 'name_kind'))
    def get_bmetadata(self):
        # type: () -> ppy.PpyBDict
        return self.bmetadata
    def to_debug_str(self):
        # type: () -> str
        return "'%s' %s" % (self.bmetadata, self.entries)
