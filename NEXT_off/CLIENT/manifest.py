import portapy_sdk as ppy
import stat
#portapy_pragma ALLOW_MODULE
import client_util as cu
#portapy_pragma ALLOW_MODULE
import util

# ---------------------------------------------------------------------------

def stat_for_server(st):
    # type: (pk.PkStat) -> ppy.PpyBDict
    """os.stat/lstat result -> dict, portable from Python 2.0 to 3.x."""
    fields = {}  # type: ppy.PpyBDict
    fields[ppy.bkey('mode')] = st[stat.ST_MODE]
    fields[ppy.bkey('ino')] = st[stat.ST_INO]
    fields[ppy.bkey('dev')] = st[stat.ST_DEV]
    fields[ppy.bkey('nlink')] = st[stat.ST_NLINK]
    fields[ppy.bkey('size')] = st[stat.ST_SIZE]
    # Indexing gives integer seconds on every version (only the st_mtime attribute
    # can be a float); int() makes that explicit, since bencode has no floats.
    fields[ppy.bkey('mtime')] = int(st[stat.ST_MTIME])
    fields[ppy.bkey('ctime')] = int(st[stat.ST_CTIME])
    mtime_ns = getattr(st, 'st_mtime_ns', None)       # 3.3+
    if mtime_ns is not None:
        fields[ppy.bkey('mtime_ns')] = mtime_ns
    for name in ('st_blocks', 'st_file_attributes'):
        value = getattr(st, name, None)
        if value is not None:
            fields[ppy.bkey(name[3:])] = value
    # st_birthtime is a float (macOS, BSD, Windows 3.12+); bencode has no
    # floats, so send whole seconds, or nanoseconds where Python has them.
    birth_ns = getattr(st, 'st_birthtime_ns', None)      # 3.12+
    if birth_ns is not None:
        fields[ppy.bkey('birthtime_ns')] = birth_ns
    birth = getattr(st, 'st_birthtime', None)
    if birth is not None:
        fields[ppy.bkey('birthtime')] = int(birth)
    return fields

def meta_stats_for_server(meta):
    # type: (pk.PkFileMetadata) -> ppy.PpyBDict
    """only copy over what we really need to send."""
    m = {}  # type: ppy.PpyBDict
    st = meta['stat']
    if st is not None:      # only sent when it differs from lstat
        m[ppy.bkey('stat')] = stat_for_server(st)
    m[ppy.bkey('lstat')] = stat_for_server(meta['lstat'])
    return m

def get_manifest_entry_sort_key(e):
    # type: (ppy.PpyBDict) -> ppy.PpyBValue
    return e[ppy.bkey('hexl_path')]

def _add_ascii_kv(bd, key, value):
    # type: (ppy.PpyBDict, ppy.PpyAsciiStr, pk.PkOptional[str]) -> None
    """Add a fact as ASCII bytes. Missing or non-ASCII facts are left out, not mangled."""
    if value is None:
        return
    try:
        ppy.require_ascii_str(key)
        ppy.require_ascii_str(value)
    except (ValueError, TypeError):
        return
    ppy.bd_add(bd, key, ppy.a2b(value))


def manifest_header(N):
    # type: (pk.PkNamingP[pk.PkOsName]) -> ppy.PpyBDict
    """What is true for every entry of a manifest from this client: the naming
    strategy and the facts about the client (display hints for the server)."""
    header = {}  # type: ppy.PpyBDict
    _add_ascii_kv(header, 'name_kind', N.kind)
    _add_ascii_kv(header, 'fs_codec', N.fs_codec)
    _add_ascii_kv(header, 'fs_errors', N.fs_errors)
    _add_ascii_kv(header, 'locale_codec', N.locale_codec)
    _add_ascii_kv(header, 'platform', N.platform)
    _add_ascii_kv(header, 'python', N.python)
    _add_ascii_kv(header, 'hostname', N.hostname)
    ppy.bd_add(header, 'win32', N.win32) # int
    return header


class Manifest:
    def __init__(self, header):
        # type: (ppy.PpyBDict) -> None
        """header: from manifest_header(N), the same for every manifest of a run."""
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]
        # note: there is bmetadata for the whole Manifest,
        # and there is also one bmetadata per file entry.
        self.bmetadata = header
    def get_name_kind(self):
        # type: () -> ppy.PpyAsciiStr
        return ppy.b2a(ppy.bd_get_bytes(self.bmetadata, 'name_kind'))
    def get_bmetadata(self):
        # type: () -> ppy.PpyBDict
        return self.bmetadata
    def to_debug_str(self):
        # type: () -> str
        return "%s %s" % (self.get_name_kind(), self.entries)
    def add_file(self, path_list, classification, N): # "everything is a file" ha ha.
        # type: (pk.PkOsPath[pk.PkOsName], pk.PkClassification, pk.PkNamingP[pk.PkOsName]) -> None
        """ if the file can't be opened safely, it won't be entered into the manifest.
        classification: the dict from classify_and_decide() for this entry. """
        ppy.prnt('path', N.os_join_path(path_list))
        try:
            target = classification['target']
            lst = classification['lst']
            if target is None or lst is None:
                raise IOError("no stat for a file classified as readable")
            opened = cu.open_for_read(path_list, target, N)
            fp = opened['fp']
            st = opened['st']
            if fp is None or st is None:
                raise IOError("could not read file: %s errno %s" % (opened['state'], opened['err']))
            try:
                md5_bytes, length = util.md5_and_length(fp, 8192)
            finally:
                fp.close()
            ppy.prnt(N.os_join_path(path_list), 'length', length, 'md5', md5_bytes)
            file_metadata = { 'lstat': lst, 'stat': None }  # type: pk.PkFileMetadata
            if lst != st:
                file_metadata['stat'] = st
            e = {}  # type: ppy.PpyBDict
            ppy.bd_add(e, 'hexl_path', util.to_hex_path_list(path_list, N))
            ppy.bd_add(e, 'md5', util.md5_hex(md5_bytes))
            ppy.bd_add(e, 'length', length)
            ppy.bd_add(e, 'bmetadata', meta_stats_for_server(file_metadata))
            self.entries.append(e)
        except (IOError, OSError): # PermissionError
            traceback.print_exc()
            err = ppy.current_exception()
            ppy.prntlog(ppy.PPY_ERROR, str(err))
            ppy.prntlog(ppy.PPY_ERROR, repr(N.os_join_path(path_list)))
    def marshall(self):
        # type: () -> ppy.PpyBencoded
        # enforce a canonical ordering, to make testing easier.
        bd = {}  # type: ppy.PpyBDict
        ppy.bd_add(bd, 'bmetadata', self.bmetadata)
        sorted = ppy.sorted_list(self.entries, get_manifest_entry_sort_key)
        ppy.bd_add(bd, 'entries', sorted)
        return ppy.bencode(bd)
