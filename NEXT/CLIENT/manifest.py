import portapy_sdk as ppy
import stat
import traceback
#portapy_pragma ALLOW_MODULE
import client_util as cu
#portapy_pragma ALLOW_MODULE
import util

# ---------------------------------------------------------------------------

def _get_manifest_entry_sort_key(e):
    return e['hex_path']

def _add_int_kv(d, key, value):
    """Add a fact as ASCII bytes. Missing or non-ASCII facts are left out, not mangled."""
    if value is None:
        return
    try:
        ppy.require_ascii_str(key)
    except (ValueError, TypeError):
        return
    d[ppy.a2b(key)] = value

def _add_ascii_kv(d, key, value):
    """Add a fact as ASCII bytes. Missing or non-ASCII facts are left out, not mangled."""
    if value is None:
        return
    try:
        ppy.require_ascii_str(key)
        ppy.require_ascii_str(value)
    except (ValueError, TypeError):
        return
    d[ppy.a2b(key)] = ppy.a2b(value)


def system_metadata(N):
    """What is true for every entry of a manifest from this client: the naming
    strategy and the facts about the client (display hints for the server)."""
    header = {}
    _add_ascii_kv(header, 'name_kind', N.kind)
    _add_ascii_kv(header, 'fs_codec', N.fs_codec)
    _add_ascii_kv(header, 'fs_errors', N.fs_errors)
    _add_ascii_kv(header, 'locale_codec', N.locale_codec)
    _add_ascii_kv(header, 'platform', N.platform)
    _add_ascii_kv(header, 'python', N.python)
    _add_ascii_kv(header, 'hostname', N.hostname)
    if N.win32:
        is_win32 = 'True'
    else:
        is_win32 = 'False'
    _add_ascii_kv(header, 'is_win32', is_win32)
    return header


class Manifest:
    def __init__(self, system_metadata):
        """header: from manifest_header(N), the same for every manifest of a run."""
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]

        # note: there is metadata for the whole Manifest,
        # and there is also one metadata per file entry.
        # note: keys and values are only ascii string bytes.
        self.system_metadata = system_metadata

    def get_name_kind(self):
        return self.system_metadata['name_kind']

    def get_system_metadata(self):
        return self.system_metadata

    def to_debug_str(self):
        return "%s %s" % (self.get_name_kind(), self.entries)

    def spk(self, pre, key):
        return '%s%s%s' % (pre, util.SEP, key)

    def add_stat_for_server(self, md, st):
        """os.stat/lstat result -> dict, portable from Python 2.0 to 3.x."""
        _add_int_kv(md, 'mode', st[stat.ST_MODE])
        _add_int_kv(md, 'ino', st[stat.ST_INO])
        _add_int_kv(md, 'dev', st[stat.ST_DEV])
        _add_int_kv(md, 'nlink', st[stat.ST_NLINK])
        _add_int_kv(md, 'size', st[stat.ST_SIZE])

        # Indexing gives integer seconds on every version (only the st_mtime attribute
        # can be a float); int() makes that explicit, since bencode has no floats.
        _add_int_kv(md, 'mtime', int(st[stat.ST_MTIME]))
        _add_int_kv(md,'ctime', int(st[stat.ST_CTIME]))

        mtime_ns = getattr(st, 'st_mtime_ns', None)       # 3.3+
        if mtime_ns is not None:
            _add_int_kv(md, 'mtime_ns', mtime_ns)
        for name in ('st_blocks', 'st_file_attributes'):
            value = getattr(st, name, None)
            if value is not None:
                _add_int_kv(md, name[3:], value)

        # st_birthtime is a float (macOS, BSD, Windows 3.12+); bencode has no
        # floats, so send whole seconds, or nanoseconds where Python has them.
        birth_ns = getattr(st, 'st_birthtime_ns', None)      # 3.12+
        if birth_ns is not None:
            _add_int_kv(md, 'birthtime_ns', birth_ns)
        birth = getattr(st, 'st_birthtime', None)
        if birth is not None:
            _add_int_kv(md, 'birthtime', int(birth))

    def add_meta_stats_for_server(self, e, file_metadata):
        lsd = {}
        self.add_stat_for_server(lsd, file_metadata['lstat'])
        e[ppy.a2b('lstat')] = lsd

        st = file_metadata['stat']
        if st is not None:
            sd = {}
            self.add_stat_for_server(sd, st)
            e[ppy.a2b('stat')] = sd

    def add_file(self, path_list, classification, N): # "everything is a file" ha ha.
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
            ppy.prnt('length', length, 'md5', md5_bytes)
            file_metadata = { 'lstat': lst, 'stat': None }  # type: pk.PkFileMetadata
            if lst != st:
                file_metadata['stat'] = st
            e = {
                ppy.a2b('md5'): util.b2ha(md5_bytes),
                ppy.a2b('length'): length,
                ppy.a2b('hex_path'): util.to_hex_path_list(path_list, N),
                }
            self.add_meta_stats_for_server(e, file_metadata)
            self.entries.append(e)
        except (IOError, OSError): # PermissionError
            traceback.print_exc()
            err = ppy.current_exception()
            ppy.prntlog(ppy.PPY_ERROR, str(err))
            ppy.prntlog(ppy.PPY_ERROR, repr(N.os_join_path(path_list)))

    def marshall(self):
        # keep it just a 1-level-deep dict.
        marsh = {
            ppy.a2b('system_metadata'): self.system_metadata,
            ppy.a2b('entries'): self.entries
            }
        try:
            return ppy.bencode(marsh)
        except:
            ppy.prntlog(ppy.PPY_ERROR, str(marsh))
            traceback.print_exc()
            raise
        
