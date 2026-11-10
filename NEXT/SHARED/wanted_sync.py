import portapy_sdk as ppy
# portapy_pragma ALLOW_MODULE
import pk_types as pk
# portapy_pragma ALLOW_MODULE
import bencode as benc


class WantedSync:
    """The server's reply: which files it wants, and from which offset."""

    def __init__(self):
        # type: () -> None
        self.entries = []

    def add_file(self, md5, length, offset):
        e = {}
        e['md5'] = md5
        e['length'] = length
        e['offset'] = offset
        self.entries.append(e)

    def marshall(self):
        return benc.bencode({'entries': self.entries})

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)


class WantedSyncUnmarshalled:
    def __init__(self, data):
        bd = benc.bv_dict(benc.bdecode(data))
        self.entries = bd['entries']

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)
