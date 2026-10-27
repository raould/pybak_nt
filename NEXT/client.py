import portapy_sdk as ppy
import sys
import os
import stat
import traceback
#portapy_pragma ALLOW_MODULE
import naming
#portapy_pragma ALLOW_MODULE
import pk_types as pk
#portapy_pragma ALLOW_MODULE
import client_util as cu
#portapy_pragma ALLOW_MODULE
import wanted_sync as ws
#portapy_pragma ALLOW_MODULE
import http_client
#portapy_pragma ALLOW_MODULE
import smells

_PYB_CHUNK_SIZE=1024*1024

# The naming strategy is chosen once, in main, and passed to everything that
# touches a name or path as N (pk.PkNamingP). Those functions are generic over
# pk.PkOsName, so mypy checks them once for bytes names and once for text names.

#
# a new pybak client, for ('any' OS) x (any Python version 2.0+).
#
# notes:
# - purposefully not calling os.path.split() for any paths.
# - we are using bencode for marshalling, which is quite invasive, because
# we are painted into a corner by having to support Python 2.0 - Python 3.x.

"""----------------------------------------
crawl TODOs:

- skip network mounts too unless they're explicitly listed. A hung NFS mount can block a read forever, and nothing in Python can time out a blocked file read.
- handle unbounded & special files.
- support macOS resource forks, NTFS alternate data streams, extended attributes and ACLs beyond the extras field, and snapshots for consistency (VSS, APFS, LVM, ZFS).
"""

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
class Manifest:
    def __init__(self, name_kind):
        # type: (pk.PkNameKind) -> None
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]
        # todo:
        # all the metadata that is true for the whole directory:
        # naming kind, filesystemencoding, et. al.
        self.bmetadata = {}  # type: ppy.PpyBDict
        ppy.bd_add(self.bmetadata, 'name_kind', ppy.a2b(name_kind))
    def get_name_kind(self):
        # type: () -> ppy.PpyAsciiStr
        return ppy.b2a(ppy.bd_get_bytes(self.bmetadata, 'name_kind'))
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
                md5_bytes, length = cu.md5_and_length(fp, 8192)
            finally:
                fp.close()
            ppy.prnt(N.os_join_path(path_list), 'length', length, 'md5', md5_bytes)
            file_metadata = { 'lstat': lst, 'stat': None }  # type: pk.PkFileMetadata
            if lst != st:
                file_metadata['stat'] = st
            e = {}  # type: ppy.PpyBDict
            ppy.bd_add(e, 'hexl_path', cu.to_hex_path_list(path_list, N))
            ppy.bd_add(e, 'md5', cu.md5_hex(md5_bytes))
            ppy.bd_add(e, 'length', length)
            ppy.bd_add(e, 'metadata', meta_stats_for_server(file_metadata))
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

class ManifestUnmarshalled:
    def __init__(self, data):
        # type: (ppy.PpyBencoded) -> None
        init = ppy.bv_dict(ppy.bdecode(data))
        self.bmetadata = ppy.bd_get_dict(init, 'bmetadata')
        self.entries = []  # type: pk.PkList[ppy.PpyBDict]
        for e in ppy.bd_get_list(init, 'entries'):
            self.entries.append(ppy.bv_dict(e))
    def get_name_kind(self):
        # type: () -> ppy.PpyAsciiStr
        return ppy.b2a(ppy.bd_get_bytes(self.bmetadata, 'name_kind'))
    def to_debug_str(self):
        # type: () -> str
        return "'%s' %s" % (self.bmetadata, self.entries)
        
def fake_sender(hex_path_list, chunk, pos):
    # type: (pk.PkHexPath, pk.PkFileBytes, pk.PkOffset) -> None
    ppy.prnt('>>> sending', pos, len(chunk), hex_path_list)

def sync_one(hex_path_list, sender, offset, chunk_size, N):
    # type: (pk.PkHexPath, pk.PkSender, pk.PkOffset, int, pk.PkNamingP[pk.PkOsName]) -> None
    """Send one wanted file from offset. The sender gets the hexl_path, as the server knows it."""
    path_list = cu.from_hex_path_list(hex_path_list, N)
    classified = classify_entry(path_list, N)
    target = classified['target']
    if (classified['kind'] != 'file' and classified['kind'] != 'link-file') or target is None:
        ppy.prntlog(ppy.PPY_WARN, 'not a file any more, not sent: %r' % (N.os_join_path(path_list),))
        return
    opened = cu.open_for_read(path_list, target, N)
    f = opened['fp']
    if f is None:
        ppy.prntlog(ppy.PPY_WARN, 'could not open, not sent: %r %s errno %s' % (N.os_join_path(path_list), opened['state'], opened['err']))
        return
    pos = offset
    try:
        f.seek(offset)
        while 1:
            chunk = pk.PkFileBytes(f.read(chunk_size))
            if not chunk:
                break
            sender(hex_path_list, chunk, pos)
            pos = pk.PkOffset(pos + len(chunk))
    finally:
        f.close()

def fake_server_sync(data):
    # type: (ppy.PpyBencoded) -> ppy.PpyBencoded
    # testing http.
    # http_client.post_data('0.0.0.0', 8000, '/sync', data, 10)

    # fake response: send all of every file.
    manifest = ManifestUnmarshalled(data)
    ppy.prnt('client manifest', manifest.to_debug_str())
    wanted = ws.WantedSync()
    for e in manifest.entries:
        wanted.add_file(
            ws.hex_path_list_from_bd(e),
            pk.PkOffset(0) # todo: server has to introspect storage.
            )
    ppy.prnt('response', wanted.to_debug_str())
    return wanted.marshall()

def sync_manifest(manifest, N):
    # type: (Manifest, pk.PkNamingP[pk.PkOsName]) -> None
    # 0) add metadata (hostname, sysinfo, os.*, etc.)
    # 1) send manifest to the server.
    # 2) get back the 'wanted' list (subset of manifest).
    # 3) for each wanted, send it (chunked, with seek) to the server.
    response = fake_server_sync(manifest.marshall())
    ppy.prnt('response', response)
    wanted = ws.WantedSyncUnmarshalled(response)
    ppy.prnt('wanted', wanted.to_debug_str())
    for w in wanted.entries:
        ppy.prnt('w', w.hex_path_list, w.offset)
        sync_one(w.hex_path_list, fake_sender, w.offset, _PYB_CHUNK_SIZE, N)

"""Crawl classification and policy for the pybak client.

Portable from Python 2.0 to 3.x (portapy subset). Uses only Python's own
interfaces: os.lstat, os.stat, os.open, os.fstat, the stat and errno modules
and st_dev/st_ino. No mount tables, no external commands, no lists of
filesystem types.

Vocabulary used in this module. Each term means exactly this and nothing
else, because "file" on Unix means a dozen different things.

  entry        A name inside a directory, as returned by os.listdir().
  lstat        Facts about the entry itself (os.lstat: never follows links).
  target       What the entry resolves to (os.stat: follows symlinks).
               For a non-link entry, target is the entry itself.
  kind         What the entry is, from lstat and, for links, its target:
                 'dir'            a directory
                 'file'           a regular file: bytes on disk, finite size
                 'special'        anything else that is not a link: FIFO,
                                  character or block device, socket, door
                 'link-dir'       symlink (or Windows directory reparse point
                                  such as a junction) whose target is a dir
                 'link-file'      symlink whose target is a regular file
                 'link-special'   symlink whose target is a special
                 'link-dangling'  symlink whose target does not exist, or
                                  that loops (ENOENT, ENOTDIR, ELOOP)
                 'vanished'       the entry disappeared before lstat
                                  (ENOENT, ENOTDIR)
                 'error'          lstat or stat failed for any other reason:
                                  permission denied, name too long, I/O
                                  error, ... The errno is returned with it.
  allowed devs The st_dev values the crawl may read from: the devices of the
               crawl roots. Listing a second disk as a root allows its device.
  relation     The target's device compared with the allowed devices:
                 'allowed'   its st_dev is one of the allowed devices
                 'other'     it is not: another filesystem of any sort
                             (a pseudo filesystem such as /proc, a network
                             share, a USB stick, a RAM disk, ...)
                 'unknown'   st_dev is 0 (Python 2 on Windows): no answer
  dir key      (st_dev, st_ino) of a directory, or None when the platform
               reports st_ino as 0 (Python 2 on Windows): no identity.
  ancestors    The dir keys of the directories from the crawl root down to
               the directory being listed, root first. Each pending directory
               carries its own list: its parent's list plus its own key.
  ancestry     The target compared with the ancestors:
                 'ok'        not one of them, and not too deep
                 'loop'      its dir key is one of the ancestors: entering
                             it would repeat the path forever (a bind mount
                             of a parent on the same device, for example)
                 'too-deep'  the ancestors already number MAX_DEPTH: the
                             backstop where dir keys are not available
  action       What the crawler does (archiving, not restoring: a link to a
               file is archived as the file's bytes; everything else that is
               not a plain dir or file is left out):
                 'descend'   enter the directory
                 'read'      read and upload the bytes (for 'link-file',
                             the target's bytes), opened with
                             open_for_read()
                 'skip'      leave it out

Rules of the code: classification functions answer one question each; the
policy is the POLICY table below; decide() only looks it up. A combination
no row matches is skipped, never read.
"""

S_ISLNK = getattr(stat, 'S_ISLNK', None)        # missing on some ports
FILE_ATTRIBUTE_REPARSE_POINT = 0x400             # Windows, Python 3.5+

MAX_DEPTH = 256

# ---------------------------------------------------------------------------
# Kind: what an entry is.

def is_link_mode(mode):
    # type: (int) -> int
    if S_ISLNK is None:
        return 0
    if S_ISLNK(mode):      # S_ISLNK comes from getattr(), so mypy cannot type its result
        return 1
    return 0


def is_dir_reparse_point(st):
    # type: (pk.PkStat) -> int
    """Windows junctions, volume mount points and directory symlinks.
    Only directories count: regular files can be reparse points too
    (OneDrive placeholders, deduplicated files) and are not links.
    """
    attributes = getattr(st, 'st_file_attributes', 0)
    if not attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return 0
    return stat.S_ISDIR(st[stat.ST_MODE])


def kind_of_mode(mode):
    # type: (int) -> str
    """'dir', 'file' or 'special' for a mode that is not a link."""
    if stat.S_ISDIR(mode):
        return 'dir'
    if stat.S_ISREG(mode):
        return 'file'
    return 'special'


def kind_for_lstat_error(err):
    # type: (pk.PkOptional[int]) -> str
    if err in cu.VANISHED_ERRNOS:
        return 'vanished'
    return 'error'


def kind_for_target_error(err):
    # type: (pk.PkOptional[int]) -> str
    if err in cu.DANGLING_ERRNOS:
        return 'link-dangling'
    return 'error'


def classify_entry_T(path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkTuple[str, pk.PkOptional[pk.PkStat], pk.PkOptional[pk.PkStat], pk.PkOptional[int]]
    """Return (kind, lstat_result, target_stat, errno) for one entry.
    target_stat is what the crawler would read or descend into: the lstat
    result for non-links, the followed os.stat result for links, and None
    when a stat failed. errno is None unless a stat failed.
    """
    try:
        lst = ppy.get_lstat()(N.os_join_path(path_list))
    except (OSError, IOError):
        err = cu.current_errno()
        return (kind_for_lstat_error(err), None, None, err)
    mode = lst[stat.ST_MODE]
    if not (is_link_mode(mode) or is_dir_reparse_point(lst)):
        return (kind_of_mode(mode), lst, lst, None)
    try:
        target = os.stat(N.os_join_path(path_list))
    except (OSError, IOError):
        err = cu.current_errno()
        return (kind_for_target_error(err), lst, None, err)
    return ('link-' + kind_of_mode(target[stat.ST_MODE]), lst, target, None)
def classify_entry(path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkEntryKind
    t = classify_entry_T(path_list, N)
    return {
        'kind': t[0],
        'lst': t[1],
        'target': t[2],
        'err': t[3]
        }

# ---------------------------------------------------------------------------
# Relation: is the target on one of the allowed devices?

def allowed_devs_for_roots(root_path_lists, N):
    # type: (pk.PkList[pk.PkOsPath[pk.PkOsName]], pk.PkNamingP[pk.PkOsName]) -> pk.PkList[int]
    """st_dev of each crawl root (native paths). Roots that fail are left out."""
    devs = []  # type: pk.PkList[int]
    for root_path_list in root_path_lists:
        try:
            dev = os.stat(N.os_join_path(root_path_list))[stat.ST_DEV]
        except (OSError, IOError):
            continue
        if dev not in devs:
            devs.append(dev)
    return devs


def fs_relation(target_stat, allowed_devs):
    # type: (pk.PkOptional[pk.PkStat], pk.PkList[int]) -> str
    if target_stat is None:
        return 'unknown'
    dev = target_stat[stat.ST_DEV]
    if dev == 0:
        return 'unknown'
    if dev in allowed_devs:
        return 'allowed'
    return 'other'


# ---------------------------------------------------------------------------
# Ancestry: would entering this directory repeat the path?

def dir_key(st):
    # type: (pk.PkOptional[pk.PkStat]) -> pk.PkDirKey
    """(st_dev, st_ino), or None where the platform gives no inode."""
    if st is None or st[stat.ST_INO] == 0:
        return None
    return (st[stat.ST_DEV], st[stat.ST_INO])


def ancestry(target_stat, ancestors):
    # type: (pk.PkOptional[pk.PkStat], pk.PkList[pk.PkDirKey]) -> str
    if len(ancestors) >= MAX_DEPTH:
        return 'too-deep'
    key = dir_key(target_stat)
    if key is not None and key in ancestors:
        return 'loop'
    return 'ok'


# ---------------------------------------------------------------------------
# Policy: (kind, relation, ancestry) -> action. First matching row wins.
# None matches anything. Edit rows here; do not add conditionals elsewhere.

POLICY = (
    (('vanished',      None,      None),       'skip'),
    (('error',         None,      None),       'skip'),
    (('special',       None,      None),       'skip'),
    (('link-special',  None,      None),       'skip'),
    (('link-dangling', None,      None),       'skip'),
    (('link-dir',      None,      None),       'skip'),
    (('dir',           None,      'loop'),     'skip'),
    (('dir',           None,      'too-deep'), 'skip'),
    (('dir',           'allowed', None),       'descend'),
    (('dir',           'unknown', None),       'descend'),
    (('dir',           'other',   None),       'skip'),
    (('file',          'allowed', None),       'read'),
    (('file',          'unknown', None),       'read'),
    (('file',          'other',   None),       'skip'),
    (('link-file',     'allowed', None),       'read'),
    (('link-file',     'unknown', None),       'read'),
    (('link-file',     'other',   None),       'skip'),
)


def matches(pattern, value):
    # type: (pk.PkOptional[str], str) -> bool
    return pattern is None or pattern == value


def decide(kind, relation, place):
    # type: (str, str, str) -> str
    for row in POLICY:
        p = row[0]
        if matches(p[0], kind) and matches(p[1], relation) and matches(p[2], place):
            return row[1]
    return 'skip'


def classify_and_decide_T(path_list, allowed_devs, ancestors, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkList[int], pk.PkList[pk.PkDirKey], pk.PkNamingP[pk.PkOsName]) -> pk.PkTuple[str, str, pk.PkOptional[pk.PkStat], pk.PkOptional[pk.PkStat], pk.PkOptional[int]]
    """One call per entry: returns (action, kind, lstat, target_stat, errno).
    ancestors: the dir keys from the crawl root down to the directory that
    holds this entry (see the vocabulary), NOT the path names.
    """
    classified = classify_entry(path_list, N)
    target = classified['target']
    action = decide(classified['kind'], fs_relation(target, allowed_devs), ancestry(target, ancestors))
    # avoid archiving existing archives.
    if smells.smells_like_canonical(path_list, N) or \
        smells.smells_like_browse(path_list, N) or \
        smells.smells_like_any_metadata(path_list, N):
        action = 'skip'
    return (action,
            classified['kind'],
            classified['lst'],
            target,
            classified['err'])
def classify_and_decide(path_list, allowed_devs, ancestors, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkList[int], pk.PkList[pk.PkDirKey], pk.PkNamingP[pk.PkOsName]) -> pk.PkClassification
    t = classify_and_decide_T(path_list, allowed_devs, ancestors, N)
    return {
        'action': t[0],
        'kind': t[1],
        'lst': t[2],
        'target': t[3],
        'err': t[4]
        }


#----------------------------------------

def is_still_dir(dir_path_list, expected, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkOptional[pk.PkStat], pk.PkNamingP[pk.PkOsName]) -> int
    """Re-check a directory just before listing it: still a directory, not a
    link, and the same object that was classified. Closes most of the window
    in which a directory can be swapped for a symlink (os.fwalk closes it
    completely with directory descriptors, but needs Python 3.3+ on POSIX).
    expected None (the root) is not checked."""
    if expected is None:
        return 1
    now = classify_entry(dir_path_list, N)
    target = now['target']
    return now['kind'] == 'dir' and target is not None and cu.is_safe_stat(target, expected)

def crawl_tree(root_path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> None
    allowed_devs = allowed_devs_for_roots([root_path_list], N)
    ppy.prnt('allowed_devs', allowed_devs)
    root_key = dir_key(os.stat(N.os_join_path(root_path_list)))
    crawl_dir(root_path_list, [root_key], None, allowed_devs, N)


def crawl_dir(dir_path_list, ancestors, expected, allowed_devs, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkList[pk.PkDirKey], pk.PkOptional[pk.PkStat], pk.PkList[int], pk.PkNamingP[pk.PkOsName]) -> None
    """List one directory, sync its files, then descend into its subdirectories (depth-first).
    Recursion is bounded by MAX_DEPTH (the 'too-deep' policy row), far below Python's limit."""
    if not is_still_dir(dir_path_list, expected, N):
        ppy.prntlog(ppy.PPY_WARN, 'changed before listing, skipped: %r' % (N.os_join_path(dir_path_list),))
        return
    cur_manifest = Manifest(N.kind)
    # Subdirectories to enter after this directory is synced: their path lists, and their stats at the same index.
    subdir_path_lists = []  # type: pk.PkList[pk.PkOsPath[pk.PkOsName]]
    subdir_stats = []  # type: pk.PkList[pk.PkOptional[pk.PkStat]]
    entries = []  # type: pk.PkList[pk.PkOsName]
    try:
        entries = N.listdir(dir_path_list)
    except (IOError, OSError):
        pe = ppy.current_exception()
        ppy.prntlog(ppy.PPY_WARN, 'cannot list %r: %s' % (N.os_join_path(dir_path_list), pe))
    for entry in entries:
        entry_path_list = N.child(dir_path_list, entry)
        try:
            classification = classify_and_decide(entry_path_list, allowed_devs, ancestors, N)
            action = classification['action']
            ppy.prnt('???', action, N.os_join_path(entry_path_list))
            if action == 'descend':
                subdir_path_lists.append(entry_path_list)
                subdir_stats.append(classification['target'])
            elif action == 'read':
                cur_manifest.add_file(entry_path_list, classification, N)
            elif action != 'skip':
                raise Exception(action)
        except (IOError, OSError):
            # One bad entry must not end the whole crawl: log, go on.
            pe = ppy.current_exception()
            ppy.prntlog(ppy.PPY_ERROR, 'entry failed %r: %s' % (N.os_join_path(entry_path_list), pe))
    ppy.prnt('---', N.os_join_path(dir_path_list), cur_manifest.entries)
    if len(cur_manifest.entries) > 0:     # no request for directories without files
        sync_manifest(cur_manifest, N)
    i = 0
    while i < len(subdir_path_lists):
        crawl_dir(subdir_path_lists[i], ancestors + [dir_key(subdir_stats[i])], subdir_stats[i], allowed_devs, N)
        i = i + 1

# ----------------------------------------
# (1) we have to obtain the names of paths + files, and know what their type is.

def get_start_arg():
    # type: () -> pk.PkArgvStr
    ppy.prnt(','.join(sys.argv))
    if len(sys.argv) != 2:
        raise Exception('required argument: directory to crawl')
    return sys.argv[1]


def run(arg, N):
    # type: (pk.PkArgvStr, pk.PkNamingP[pk.PkOsName]) -> None
    """Everything after the naming choice: written once, checked for bytes and for text names."""
    start_path_list = N.argv_to_os_path(arg)
    if not os.path.isdir(N.os_join_path(start_path_list)):
        sys.stderr.write('required argument: must be a directory\n')
        sys.exit(1)
    ppy.prnt('start_dir', N.os_join_path(start_path_list))
    crawl_tree(start_path_list, N)


def main():
    # type: () -> None
    N = naming.choose_naming()
    # windows on python 2.x is uniquely broken.
    if N.is_lossy:
        sys.stderr.write("FAIL: unsupported due to lossy conversion issues inherent in Python+OS+FS, sorry.\n")
        sys.exit(1)
    arg = get_start_arg()
    # The only place both name types appear. The branches look the same, but
    # mypy checks run() as text names in the first and as bytes in the second.
    if isinstance(N, naming.TextNaming):
        run(arg, N)
    else:
        run(arg, N)


if __name__ == '__main__':
    main()
