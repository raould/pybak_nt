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
import util
#portapy_pragma ALLOW_MODULE
import manifest as mf
#portapy_pragma ALLOW_MODULE
import wanted_sync as ws
#portapy_pragma ALLOW_MODULE
import http_client
#portapy_pragma ALLOW_MODULE
import smells
#portapy_pragma ALLOW_MODULE
import manifest as mf
#portapy_pragma ALLOW_MODULE
import manifest_unmarshalled as mfu

_PYB_CHUNK_SIZE=1024*1024
_HTTP_TIMEOUT_SEC=10

# TODO: config / command line params for server address.

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

#----------------------------------------

def post_sender(hex_path_list, chunk, offset, system_metadata):
    pass

def sync_one(hex_path_list, sender, offset, chunk_size, system_metadata, N):
    pass

def server_request(manifest):
    # type: (ppy.PpyBencoded) -> ppy.PpyBencoded
    data = manifest.marshall()
    body = http_client.post_data('0.0.0.0', 8000, '/query', data, _HTTP_TIMEOUT_SEC)
    wanted = ws.WantedSyncUnmarshalled(body)
    for e in unmarsh.entries:
        wanted.add_file(
            e['md5'],
            e['length'],
            0,
            e['hex_path']
            )
    return wanted

def sync_manifest(manifest, N):
    # type: (Manifest, pk.PkNamingP[pk.PkOsName]) -> None
    # 0) add metadata (hostname, sysinfo, os.*, etc.)
    # 1) send manifest to the server.
    # 2) get back the 'wanted' list (subset of manifest).
    # 3) for each wanted, send it (chunked, with seek) to the server.
    wanted = server_request(manifest)
    ppy.prnt('wanted', wanted.to_debug_str())
    for w in wanted.entries:
        ppy.prnt('w', w['offset'], w['hex_path'])
        sync_one(w['hex_path'],
                 post_sender,
                 w['offset'],
                 _PYB_CHUNK_SIZE,
                 manifest.get_system_metadata(),
                 N)

# ---------------------------------------------------------------------------

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

def classify_entry(path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkEntryKind
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
            err = util.current_errno()
            return (kind_for_lstat_error(err), None, None, err)
        mode = lst[stat.ST_MODE]
        if not (is_link_mode(mode) or is_dir_reparse_point(lst)):
            return (kind_of_mode(mode), lst, lst, None)
        try:
            target = os.stat(N.os_join_path(path_list))
        except (OSError, IOError):
            err = util.current_errno()
            return (kind_for_target_error(err), lst, None, err)
        return ('link-' + kind_of_mode(target[stat.ST_MODE]), lst, target, None)
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
    # Avoid archiving existing archives. Only for files the policy would read:
    # the smell tests open files, so they must never see a FIFO or a device.
    if action == 'read' and target is not None:
        if smells.smells_like_canonical(path_list, N) or smells.smells_like_browse(path_list, target, N) or smells.smells_like_any_metadata(path_list, N):
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
    system_metadata = mf.system_metadata(N)
    crawl_dir(root_path_list, [root_key], allowed_devs, system_metadata, N)


def crawl_dir(root_path_list, root_key, allowed_devs, system_metadata, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkDirKey, pk.PkList[int], ppy.PpyBDict, pk.PkNamingP[pk.PkOsName]) -> None
    """Depth-first and iterative: a local stack of directories still to visit.
    Each loop lists one directory, syncs its files, and pushes its subdirectories.
    The stack is three parallel lists, pushed and popped together; the same index is one pending directory:
      pending_path_lists[i]  its path list
      pending_ancestors[i]   the dir keys of it and every directory above it (loop detection)
      pending_expected[i]    its stat when classified, re-checked before listing (None for the root)"""
    pending_path_lists = [root_path_list]  # type: pk.PkList[pk.PkOsPath[pk.PkOsName]]
    pending_ancestors = [[root_key]]  # type: pk.PkList[pk.PkList[pk.PkDirKey]]
    pending_expected = [None]  # type: pk.PkList[pk.PkOptional[pk.PkStat]]
    while len(pending_path_lists) > 0:
        dir_path_list = pending_path_lists.pop()
        ancestors = pending_ancestors.pop()
        expected = pending_expected.pop()
        if not is_still_dir(dir_path_list, expected, N):
            ppy.prntlog(ppy.PPY_WARN, 'changed before listing, skipped: %r' % (N.os_join_path(dir_path_list),))
            continue
        cur_manifest = mf.Manifest(system_metadata)
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
                    target = classification['target']
                    pending_path_lists.append(entry_path_list)
                    pending_ancestors.append(ancestors + [dir_key(target)])
                    pending_expected.append(target)
                elif action == 'read':
                    cur_manifest.add_file(entry_path_list, classification, N)
                    # do not commit this testing hack...
                    if len(cur_manifest.entries) == 2:
                        break
                    # ...do not commit this testing hack.
                elif action != 'skip':
                    raise Exception(action)
            except (IOError, OSError):
                # One bad entry must not end the whole crawl: log, go on.
                pe = ppy.current_exception()
                ppy.prntlog(ppy.PPY_ERROR, 'entry failed %r: %s' % (N.os_join_path(entry_path_list), pe))
        ppy.prnt('---', N.os_join_path(dir_path_list), cur_manifest.entries)
        if len(cur_manifest.entries) > 0:     # no request for directories without files
            sync_manifest(cur_manifest, N)
 
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
