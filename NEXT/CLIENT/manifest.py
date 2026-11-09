import portapy_sdk as ppy
import stat
import traceback
# portapy_pragma ALLOW_MODULE
import client_util as cu
# portapy_pragma ALLOW_MODULE
import util


def system_metadata(N):  # todo: implement in metadata_unmarshall
    """What is true for every entry of a manifest from this client: the naming
    strategy and the facts about the client (display hints for the server)."""
    header = {}
    header['name_kind'] = ppy.a2b(N.kind)
    header['fs_codec'] = ppy.a2b(N.fs_codec)
    header['fs_errors'] = ppy.a2b(N.fs_errors)
    header['locale_codec'] = ppy.a2b(N.locale_codec)
    header['platform'] = ppy.a2b(N.platform)
    header['python'] = ppy.a2b(N.python)
    header['hostname'] = ppy.a2b(N.hostname)
    if N.win32:
        is_win32 = 1
    else:
        is_win32 = 0
    header['is_win32'] = is_win32
    return header


class Manifest:
    def __init__(self, system_metadata):
        """header: from manifest_header(N), the same for every manifest of a run."""
        self.entries = []

        # note: there is metadata for the whole Manifest,
        # and there is also one metadata per file entry.
        # note: keys and values are only ascii string bytes.
        self.system_metadata = system_metadata

    def get_name_kind(self):
        return ppy.b2a(self.system_metadata['name_kind'])

    def get_system_metadata(self):
        return self.system_metadata

    def to_debug_str(self):
        return "%s %s" % (self.get_name_kind(), self.entries)

    def spk(self, pre, key):
        return '%s%s%s' % (pre, util.SEP, key)

    def add_stat_for_server(self, md, st):
        """os.stat/lstat result -> dict, portable from Python 2.0 to 3.x."""
        md['mode'] = st[stat.ST_MODE]
        md['ino'] = st[stat.ST_INO]
        md['dev'] = st[stat.ST_DEV]
        md['nlink'] = st[stat.ST_NLINK]
        md['size'] = st[stat.ST_SIZE]

        # Indexing gives integer seconds on every version (only the st_mtime attribute
        # can be a float); int() makes that explicit, since bencode has no floats.
        md['mtime'] = int(st[stat.ST_MTIME])
        md['ctime'] = int(st[stat.ST_CTIME])

        mtime_ns = getattr(st, 'st_mtime_ns', None)       # 3.3+
        if mtime_ns is not None:
            md['mtime_ns'] = mtime_ns
        for name in ('st_blocks', 'st_file_attributes'):
            value = getattr(st, name, None)
            if value is not None:
                md[name[3:]] = value

        # st_birthtime is a float (macOS, BSD, Windows 3.12+); bencode has no
        # floats, so send whole seconds, or nanoseconds where Python has them.
        birth_ns = getattr(st, 'st_birthtime_ns', None)      # 3.12+
        if birth_ns is not None:
            md['birthtime_ns'] = birth_ns
        birth = getattr(st, 'st_birthtime', None)
        if birth is not None:
            md['birthtime'] = int(birth)

    def add_meta_stats_for_server(self, e, file_metadata):
        lsd = {}
        self.add_stat_for_server(lsd, file_metadata['lstat'])
        e['lstat'] = lsd

        st = file_metadata['stat']
        if st is not None:
            sd = {}
            self.add_stat_for_server(sd, st)
            e['stat'] = sd

    # "everything is a file" ha ha.
    def add_file(self, path_list, classification, N):
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
                raise IOError("could not read file: %s errno %s" %
                              (opened['state'], opened['err']))
            try:
                md5, length = util.md5_and_length(fp, 8192)
            finally:
                fp.close()
            ppy.prnt('length', length, 'md5', md5)
            e = {
                'md5': ppy.a2b(md5),
                'length': length,
                'hex_path': util.to_wire_path_list(path_list, N),
            }
            file_metadata = {'lstat': lst, 'stat': None}
            if lst != st:
                file_metadata['stat'] = st
            self.add_meta_stats_for_server(e, file_metadata)
            self.entries.append(e)
        except (IOError, OSError):  # PermissionError
            traceback.print_exc()
            err = ppy.current_exception()
            ppy.prntlog(ppy.PPY_ERROR, str(err))
            ppy.prntlog(ppy.PPY_ERROR, repr(N.os_join_path(path_list)))

    def marshall(self):
        # keep it just a 1-level-deep dict.
        marsh = {
            ppy.a2b(util.MANIFEST_SYSTEM_METADATA_KEY): self.system_metadata,
            # todo: sort entries into a canonical ordering, to make test easier. (ha ha)
            ppy.a2b(util.MANIFEST_ENTRIES_KEY): self.entries
        }
        try:
            return ppy.bencode(marsh)
        except:
            ppy.prntlog(ppy.PPY_ERROR, str(marsh))
            traceback.print_exc()
            raise
