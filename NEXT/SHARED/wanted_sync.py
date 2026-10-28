import portapy_sdk as ppy
#portapy_pragma ALLOW_MODULE
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
        # keep it just a 1-level-deep dict.
        marsh = {}
        for i in range(len(self.entries)):
            e = self.entries[i]
            for k in e:
                marsh[ppy.a2b('%s%s%s' % (i, util.SEP, k))] = e[k]
        return ppy.bencode(marsh)

    def to_debug_str(self):
        # type: () -> str
        return str(self.entries)


class WantedSyncUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        bd = ppy.bv_dict(ppy.bdecode(data))
        self.entries = []  # type: pk.PkList[WantedEntry]
        for e in ppy.bd_get_list(bd, 'entries'):
            self.entries.append(
                self.wanted_entry_from_bd(ppy.bv_dict(e))
                )

    def hex_path_list_from_bd(self, bd):
        # type: (ppy.PpyBDict) -> pk.PkHexPath
        """bd['hex_path'] from decoded data, checked: a list of lowercase hex byte strings."""
        hexes = []  # type: pk.PkList[pk.PkHexName]
        for h in ppy.bd_get_list(bd, 'hex_path'):
            hexes.append(pk.PkHexName(ppy.PpyAsciiBytes(ppy.bv_bytes(h))))
        return pk.PkHexPath(hexes)

    def wanted_entry_from_bd(self, bd):
        # type: (ppy.PpyBDict) -> WantedEntry
        """Check one decoded entry and give it its types. Raises TypeError/ValueError if malformed."""
        e = {}
        ppy.bd_add(e, 'md5', ppy.bd_get(bd, 'md5'))
        ppy.bd_add(e, 'length', ppy.bd_get_int(bd, 'length'))
        ppy.bd_add(e, 'hex_path', self.hex_path_list_from_bd(bd))
        ppy.bd_add(e, 'offset', pk.PkOffset(ppy.bd_get_int(bd, 'offset')))
        return e

    def to_debug_str(self):
        # type: () -> str
        parts = []  # type: pk.PkList[str]
        for e in self.entries:
            parts.append('%s %d' % (e.hex_path_list, e.offset))
        return ', '.join(parts)
