import portapy_sdk as ppy
# portapy_pragma ALLOW_MODULE
import pk_types as pk
import util


class WantedSync:
    """The server's reply: which files it wants, and from which offset."""

    def __init__(self):
        # type: () -> None
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]

    def add_file(self, md5, length, offset, hex_path):
        e = {}
        e['md5'] = md5
        e['length'] = length
        e['offset'] = offset
        e['hex_path'] = hex_path
        self.entries.append(e)

    def marshall(self):
        return ppy.bencode({'entries': self.entries})

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)


class WantedSyncUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        bd = ppy.bv_dict(ppy.bdecode(data))
        self.entries = bd['entries']

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)
