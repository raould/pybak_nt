"""Reading a manifest: what the client sends to the server's /sync, one per directory."""

import portapy_sdk as ppy
# portapy_pragma ALLOW_MODULE
import pk_types as pk
# portapy_pragma ALLOW_MODULE
import util
# portapy_pragma ALLOW_MODULE
import naming
# portapy_pragma ALLOW_MODULE
import bencode as benc


def un_system_metadata(data):
    un = {}
    un['name_kind'] = data['name_kind']
    un['fs_codec'] = data['fs_codec']
    un['fs_errors'] = data['fs_errors']
    un['locale_codec'] = data['locale_codec']
    un['platform'] = data['platform']
    un['python'] = data['python']
    un['hostname'] = data['hostname']
    un['is_win32'] = data['is_win32']
    return un


def un_entry(data, N):
    e = {}
    e['md5'] = data['md5']
    e['length'] = data['length']
    e['hex_path'] = data['hex_path']
    e['lstat'] = data['lstat']
    e['stat'] = data['stat']
    return e


class ManifestUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        unmarsh = benc.bv_dict(benc.bdecode(data))

        smd = unmarsh[util.MANIFEST_SYSTEM_METADATA_KEY]
        self.system_metadata = un_system_metadata(smd)

        N = naming.make_naming(self.get_name_kind())
        es = unmarsh[util.MANIFEST_ENTRIES_KEY]
        self.entries = []
        for e in es:
            self.entries.append(un_entry(e, N))

    def get_name_kind(self):
        return self.system_metadata['name_kind']

    def get_system_metadata(self):
        return self.system_metadata

    def to_debug_str(self):
        return "'%s' %s" % (self.system_metadata, self.entries)
