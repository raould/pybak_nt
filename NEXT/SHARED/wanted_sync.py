import portapy_sdk as ppy
#portapy_pragma ALLOW_MODULE
import pk_types as pk


def make_wanted_entry(hex_path_list, offset):
    # type: (pk.PkHexPath, pk.PkOffset) -> ppy.PpyBDict
    e = {}  # type: ppy.PpyBDict
    ppy.bd_add(e, 'hexl_path', hex_path_list)
    ppy.bd_add(e, 'offset', offset)
    return e


class WantedSync:
    """The server's reply: which files it wants, and from which offset."""
    def __init__(self):
        # type: () -> None
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]

    def add_file(self, hex_path_list, offset):
        # type: (pk.PkHexPath, pk.PkOffset) -> None
        self.entries.append(make_wanted_entry(hex_path_list, offset))

    def marshall(self):
        # type: () -> ppy.PpyBencoded
        bd = {}  # type: ppy.PpyBDict
        ppy.bd_add(bd, 'entries', self.entries)
        return ppy.bencode(bd)

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)


class WantedEntry:
    """One checked entry of a WantedSync reply."""
    def __init__(self, hex_path_list, offset):
        # type: (pk.PkHexPath, pk.PkOffset) -> None
        self.hex_path_list = hex_path_list
        self.offset = offset


def hex_path_list_from_bd(bd):
    # type: (ppy.PpyBDict) -> pk.PkHexPath
    """bd['hexl_path'] from decoded data, checked: a list of lowercase hex byte strings."""
    hexes = []  # type: pk.PkList[pk.PkHexName]
    for h in ppy.bd_get_list(bd, 'hexl_path'):
        hexes.append(pk.PkHexName(ppy.PpyAsciiBytes(ppy.bv_bytes(h))))
    return pk.PkHexPath(hexes)


def wanted_entry_from_bd(bd):
    # type: (ppy.PpyBDict) -> WantedEntry
    """Check one decoded entry and give it its types. Raises TypeError/ValueError if malformed."""
    return WantedEntry(hex_path_list_from_bd(bd), pk.PkOffset(ppy.bd_get_int(bd, 'offset')))


class WantedSyncUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        bd = ppy.bv_dict(ppy.bdecode(data))
        self.entries = []  # type: pk.PkList[WantedEntry]
        for e in ppy.bd_get_list(bd, 'entries'):
            self.entries.append(wanted_entry_from_bd(ppy.bv_dict(e)))

    def to_debug_str(self):
        # type: () -> str
        parts = []  # type: pk.PkList[str]
        for e in self.entries:
            parts.append('%s@%d' % (e.hex_path_list, e.offset))
        return ', '.join(parts)
