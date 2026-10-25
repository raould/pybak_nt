import portapy_sdk as ppy

class WantedSync:
    def __init__(self):
        self.entries = []
    def add_file(self, hexl_path, offset):
        e = {}
        ppy.bd_add(e, 'hexl_path', hexl_path)
        ppy.bd_add(e, 'offset', offset)
        self.entries.append(e)
    def marshall(self):
        bd = {}
        ppy.bd_add(bd, 'entries', self.entries)
        return ppy.bencode(bd)
    def to_debug_str(self):
        return str(self.entries)

class WantedSyncUnmarshalled:
    def __init__(self, data):
        bd = ppy.bdecode(data)
        self.entries = bd[ppy.bkey('entries')]
    def to_debug_str(self):
        return str(self.entries)
