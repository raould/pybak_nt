"""Reading a manifest: what the client sends to the server's /sync, one per directory."""

import portapy_sdk as ppy
# portapy_pragma ALLOW_MODULE
import pk_types as pk
# portapy_pragma ALLOW_MODULE
import util


def _upsert_collating(collating, collid, k, v):
    if collid not in collating:
        collating[collid] = {}
    collating[collid][k] = v


class ManifestUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        """Decode and check the outer shape. Raises ValueError/TypeError/KeyError if malformed."""
        self.entries = []
        self.system_metadata = {}
        unmarsh = ppy.bv_dict(ppy.bdecode(data))

        collating = {}
        for k in unmarsh.keys():
            kp = k.split(util.SEP)
            v = unmarsh[k]
            if k.startswith(util.SYSTEM_METADATA_PREFIX):
                assert len(kp) == 2
                smkey = kp[1]
                self.system_metadata[smkey] = ppy.b2a(v)
            else:
                if len(kp) == 3:
                    collid = kp[0]
                    sk = kp[1]
                    mk = kp[2]
                    _upsert_collating(collating, collid, '%s%s%s' %
                                      (sk, util.SEP, mk), v)
                    pass
                elif len(kp) == 2:
                    collid = kp[0]
                    mk = kp[1]
                    _upsert_collating(collating, collid, mk, v)
                    pass
                else:
                    assert False, kp
        for ck in collating.keys():
            cv = collating[ck]
            self.entries.append(cv)

    def get_name_kind(self):
        return self.system_metadata['name_kind']

    def get_system_metadata(self):
        return self.system_metadata

    def to_debug_str(self):
        return "'%s' %s" % (self.system_metadata, self.entries)
