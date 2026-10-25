import portapy_sdk as ppy
import sys
import os
import stat
import traceback
#portapy_pragma ALLOW_MODULE
import binascii
#portapy_pragma ALLOW_MODULE
import errno


_PYB_CHUNK_SIZE=1024*1024

#
# a new pybak client, for ('any' OS) x (any Python version 2.0+).
#
# notes:
# - purposefully not calling os.path.split() for any paths.
# - we are using bencode for marshalling, which is quite invasive, because
# we are painted into a corner by having to support Python 2.0 - Python 3.x.

# ---------------------------------------------------------------------------

#----------------------------------------
# support MD5 file hashing.
try:
    #portapy_pragma ALLOW_MODULE
    import hashlib
    # todo: would want usedforsecurity=False (Python 3.9+) on FIPS systems
    hasher_new = hashlib.md5
    #portapy_pragma ALLOW_MODULE_END hashlib
except ImportError:
    #portapy_pragma ALLOW_MODULE
    import md5
    hasher_new = md5.new
    #portapy_pragma ALLOW_MODULE_END md5
def md5_and_length(fp, chunk_size=8192):
    hasher = hasher_new()
    count = 0
    while 1:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        count = count + len(chunk)
    return (hasher.digest(), count)

# ---------------------------------------------------------------------------

def hexlify_list(l):
    h = []
    for e in l:
        h.append(binascii.hexlify(e))
    return h
def unhexlify_list(l):
    u = []
    for e in l:
        u.append(binascii.unhexlify(e))
    return u

def stat_for_server(st):
    """os.stat/lstat result -> dict, portable from Python 2.0 to 3.x."""
    fields = {
        ppy.a2b('mode'):  st[stat.ST_MODE],
        ppy.a2b('ino'):   st[stat.ST_INO],
        ppy.a2b('dev'):   st[stat.ST_DEV],
        ppy.a2b('nlink'): st[stat.ST_NLINK],
        ppy.a2b('size'):  st[stat.ST_SIZE],
        ppy.a2b('mtime'): st[stat.ST_MTIME],      # integer seconds on every version
        ppy.a2b('ctime'): st[stat.ST_CTIME],
    }
    mtime_ns = getattr(st, 'st_mtime_ns', None)       # 3.3+
    if mtime_ns is not None:
        fields[ppy.a2b('mtime_ns')] = mtime_ns
    for name in ('st_blocks', 'st_file_attributes'):
        value = getattr(st, name, None)
        if value is not None:
            fields[ppy.a2b(name[3:])] = value
    # st_birthtime is a float (macOS, BSD, Windows 3.12+); bencode has no
    # floats, so send whole seconds, or nanoseconds where Python has them.
    birth_ns = getattr(st, 'st_birthtime_ns', None)      # 3.12+
    if birth_ns is not None:
        fields[ppy.a2b('birthtime_ns')] = birth_ns
    birth = getattr(st, 'st_birthtime', None)
    if birth is not None:
        fields[ppy.a2b('birthtime')] = int(birth)
    return fields

def meta_stats_for_server(meta):
    m = {}
    m[ppy.a2b('stat')] = stat_for_server(meta['stat'])
    m[ppy.a2b('lstat')] =  stat_for_server(meta['lstat'])
    return m

def get_digest_entry_sort_key(e):
    return e[ppy.bkey('hexl_path')]
class Digest:
    def __init__(self, entries=None):
        self.entries = entries or [] # public!
    def to_debug_str(self):
        return str(self.entries)
    def add_file(self, cursor, classification):
        """ if the file can't be opened safely, it won't be entered into the digest.
        classification: the tuple from classify_and_decide() for this entry. """
        ppy.prnt('cursor', str(cursor))
        try:
            path = os.path.join(*cursor)
            opened = open_for_read(path, classification['target'])
            fp = opened['fp']
            if fp is None:
                raise IOError("could not read file: %s errno %s" % (opened['state'], opened['err']))
            try:
                md5_bytes, length = md5_and_length(fp)
            finally:
                fp.close()
            # lstat: the entry as classified. stat: the object actually read.
            metadata = {'lstat': classification['lst'], 'stat': opened['st']}
            ppy.prnt('md5', md5_bytes)
            ppy.prnt('length', length)
            e = {}
            ppy.bd_add(e, 'hexl_path', hexlify_list(cursor))
            ppy.bd_add(e, 'md5', binascii.hexlify(md5_bytes))
            ppy.bd_add(e, 'length', length)
            ppy.bd_add(e, 'metadata', meta_stats_for_server(metadata))
            self.entries.append(e)
        except (IOError, OSError): # PermissionError
            traceback.print_exc()
            e = ppy.current_exception()
            ppy.prntlog(ppy.PPY_ERROR, str(e))
            ppy.prntlog(ppy.PPY_ERROR, type(cursor))
    def marshall(self):
        # enforce a canonical ordering, to make testing easier.
        sorted = ppy.sorted_list(self.entries, get_digest_entry_sort_key)
        return ppy.bencode(sorted)
    def foreach(self, on_entry): # nigh useless w/out lambda support.
        for e in self.entries:
            on_entry(e) # dict of {path, hexl_path, md5, length}
class DigestFactory:
    def unmarshall(self, data):
        body = ppy.bdecode(data)
        return Digest(body)

class WantedSync:
    def __init__(self, data):
        self.body = ppy.bdecode(data)
    def foreach(self, on_entry): # nigh useless w/out lambda support.
        for b in self.body:
            on_entry(b) # dict of {path, offset}
        
def fake_sender(path, chunk, pos):
    ppy.prnt('>>> sending', pos, len(chunk), path)

def sync_one(path, sender, offset=0, chunk_size=_PYB_CHUNK_SIZE):
    classified = classify_entry(path)
    if classified['kind'] != 'file' and classified['kind'] != 'link-file':
        ppy.prntlog(ppy.PPY_WARN, 'not a file any more, not sent: %s' % (path,))
        return
    opened = open_for_read(path, classified['target'])
    f = opened['fp']
    if f is None:
        ppy.prntlog(ppy.PPY_WARN, 'could not open, not sent: %s %s errno %s' % (path, opened['state'], opened['err']))
        return
    pos = offset
    try:
        f.seek(offset)
        while 1:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sender(path, chunk, pos)
            pos = pos + len(chunk)
    finally:
        f.close()

def fake_server_sync(data):
    # fake response: send all of every file.
    wanted = []
    digest = DigestFactory().unmarshall(data)
    ppy.prnt('client digest', digest.to_debug_str())
    for e in digest.entries:
        w = {}
        w[ppy.bkey('hexl_path')] = e[ppy.bkey('hexl_path')]
        w[ppy.bkey('offset')] = 0
        wanted.append(w)
    ppy.prnt('response', wanted)
    return ppy.bencode(wanted)

def sync_digest(digest):
    # 0) add metadata (hostname, sysinfo, os.*, etc.)
    # 1) send digest to the server.
    # 2) get back the 'wanted' list (subset of digest).
    # 3) for each wanted, send it (chunked, with seek) to the server.
    response = fake_server_sync(digest.marshall())
    ppy.prnt('response', response)
    wanted = ppy.bdecode(response)
    ppy.prnt('wanted', wanted)
    for w in wanted:
        hexl_path = w[ppy.bkey('hexl_path')]
        ppy.prnt(hexl_path)
        cursor = unhexlify_list(hexl_path)
        ppy.prnt(cursor)
        path = os.path.join(*cursor)
        offset = w[ppy.bkey('offset')]
        sync_one(path, fake_sender, offset)

"""
crawl TODOs:

- Skip network mounts too unless they're explicitly listed. A hung NFS mount can block a read forever, and nothing in Python can time out a blocked file read.

- handle unbounded & special files.

- ignore bad-smelling files (based on filenames, extensions, etc.).

- support macOS resource forks, NTFS alternate data streams, extended attributes and ACLs beyond the extras field, and snapshots for consistency (VSS, APFS, LVM, ZFS).

"""

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

# errno values meaning "the name no longer leads anywhere". -1 stands in for
# a constant the platform lacks; no real errno is negative.
VANISHED_ERRNOS = (getattr(errno, 'ENOENT', -1), getattr(errno, 'ENOTDIR', -1))
DANGLING_ERRNOS = VANISHED_ERRNOS + (getattr(errno, 'ELOOP', -1),)

# Flags for open_for_read(). O_NONBLOCK makes opening a FIFO return at once
# instead of waiting for a writer; it does not change reads of a regular
# file. O_BINARY exists only on Windows. Constants a platform lacks are 0.
READ_FLAGS = (os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))


def current_errno():
    """errno of the exception being handled, or None.
    Uses sys.exc_info() because 'except E, e' (Python 2) and
    'except E as e' (Python 2.6+) have no common spelling.
    """
    return getattr(sys.exc_info()[1], 'errno', None)


# ---------------------------------------------------------------------------
# Kind: what an entry is.

def is_link_mode(mode):
    if S_ISLNK is None:
        return 0
    return S_ISLNK(mode)


def is_dir_reparse_point(st):
    """Windows junctions, volume mount points and directory symlinks.
    Only directories count: regular files can be reparse points too
    (OneDrive placeholders, deduplicated files) and are not links.
    """
    attributes = getattr(st, 'st_file_attributes', 0)
    if not attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        return 0
    return stat.S_ISDIR(st[stat.ST_MODE])


def kind_of_mode(mode):
    """'dir', 'file' or 'special' for a mode that is not a link."""
    if stat.S_ISDIR(mode):
        return 'dir'
    if stat.S_ISREG(mode):
        return 'file'
    return 'special'


def kind_for_lstat_error(err):
    if err in VANISHED_ERRNOS:
        return 'vanished'
    return 'error'


def kind_for_target_error(err):
    if err in DANGLING_ERRNOS:
        return 'link-dangling'
    return 'error'


def _classify_entry(path):
    """Return (kind, lstat_result, target_stat, errno) for one entry.
    target_stat is what the crawler would read or descend into: the lstat
    result for non-links, the followed os.stat result for links, and None
    when a stat failed. errno is None unless a stat failed.
    """
    lstat = getattr(os, 'lstat', os.stat)
    try:
        lst = lstat(path)
    except (OSError, IOError):
        err = current_errno()
        return (kind_for_lstat_error(err), None, None, err)
    mode = lst[stat.ST_MODE]
    if not (is_link_mode(mode) or is_dir_reparse_point(lst)):
        return (kind_of_mode(mode), lst, lst, None)
    try:
        target = os.stat(path)
    except (OSError, IOError):
        err = current_errno()
        return (kind_for_target_error(err), lst, None, err)
    return ('link-' + kind_of_mode(target[stat.ST_MODE]), lst, target, None)
def classify_entry(path):
    t = _classify_entry(path)
    return {
        'kind': t[0],
        'lst': t[1],
        'target': t[2],
        'err': t[3]
        }

# ---------------------------------------------------------------------------
# Relation: is the target on one of the allowed devices?

def allowed_devs_for_roots(roots):
    """st_dev of each crawl root (native paths). Roots that fail are left out."""
    devs = []
    for root in roots:
        try:
            dev = os.stat(root)[stat.ST_DEV]
        except (OSError, IOError):
            continue
        if dev not in devs:
            devs.append(dev)
    return devs


def fs_relation(target_stat, allowed_devs):
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
    """(st_dev, st_ino), or None where the platform gives no inode."""
    if st is None or st[stat.ST_INO] == 0:
        return None
    return (st[stat.ST_DEV], st[stat.ST_INO])


def ancestry(target_stat, ancestors):
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
    return pattern is None or pattern == value


def decide(kind, relation, place):
    for row in POLICY:
        p = row[0]
        if matches(p[0], kind) and matches(p[1], relation) and matches(p[2], place):
            return row[1]
    return 'skip'


def _classify_and_decide(cursor, allowed_devs, ancestors):
    """One call per entry: returns (action, kind, lstat, target_stat, errno).
    ancestors: the dir keys from the crawl root down to the directory that
    holds this entry (see the vocabulary), NOT the path names.
    """
    path = os.path.join(*cursor)
    classified = classify_entry(path)
    target = classified['target']
    action = decide(classified['kind'], fs_relation(target, allowed_devs), ancestry(target, ancestors))
    return (action, classified['kind'], classified['lst'], target, classified['err'])
def classify_and_decide(cursor, allowed_devs, ancestors):
    t = _classify_and_decide(cursor, allowed_devs, ancestors)
    return {
        'action': t[0],
        'kind': t[1],
        'lst': t[2],
        'target': t[3],
        'err': t[4]
        }

# ---------------------------------------------------------------------------
# Reading: open what was classified, and only that.

def is_safe_stat(a, b):
    """True if two stat results describe the same object, as far as the
    platform can tell. A 0 st_dev or st_ino (Python 2 on Windows) is not
    compared."""
    dev_a = a[stat.ST_DEV]
    dev_b = b[stat.ST_DEV]
    if dev_a != 0 and dev_b != 0 and dev_a != dev_b:
        return 0
    ino_a = a[stat.ST_INO]
    ino_b = b[stat.ST_INO]
    if ino_a != 0 and ino_b != 0 and ino_a != ino_b:
        return 0
    return 1


def _open_for_read(path, target_stat):
    """Open a file the policy said to 'read', without trusting the name.

    Between classification and open, the name can be replaced by a FIFO
    (opening it normally would wait forever for a writer), a device, or a
    different file. This opens without blocking, then checks the open
    handle itself with os.fstat: still a regular file, and the same device
    and inode as target_stat.

    Returns (file_object, fstat_result, problem, errno):
      (f, st, None, None)        open: read from f, close it when done
      (None, st, 'changed', None)  not the object that was classified
      (None, None, 'error', err)   open or fstat failed
    """
    try:
        fd = os.open(path, READ_FLAGS)
    except (OSError, IOError):
        return (None, None, 'error', current_errno())
    try:
        st = os.fstat(fd)
    except (OSError, IOError):
        err = current_errno()
        os.close(fd)
        return (None, None, 'error', err)
    if not stat.S_ISREG(st[stat.ST_MODE]) or not is_safe_stat(st, target_stat):
        os.close(fd)
        return (None, st, 'changed', None)
    return (os.fdopen(fd, 'rb'), st, None, None)
def open_for_read(path, target_stat):
    t = _open_for_read(path, target_stat)
    return {
        'fp': t[0],
        'st': t[1],
        'state': t[2],
        'err': t[3]
        }
#----------------------------------------


#----------------------------------------

def is_still_dir(dir_path, expected):
    """Re-check a directory just before listing it: still a directory, not a
    link, and the same object that was classified. Closes most of the window
    in which a directory can be swapped for a symlink (os.fwalk closes it
    completely with directory descriptors, but needs Python 3.3+ on POSIX).
    expected None (the root) is not checked."""
    if expected is None:
        return 1
    now = classify_entry(dir_path)
    return now['kind'] == 'dir' and is_safe_stat(now['target'], expected)

def crawl_tree(root):
    allowed_devs = allowed_devs_for_roots([root])
    ppy.prnt('allowed_devs', allowed_devs)
    # Each pending item: {cursor, ancestors, expected}. Stack: depth-first.
    pending_dirs = [{'cursor': [root], 'ancestors': [dir_key(os.stat(root))], 'expected': None}]
    while len(pending_dirs) > 0:
        item = pending_dirs.pop()
        cursor = item['cursor']
        ancestors = item['ancestors']
        dir_path = os.path.join(*cursor)
        if not is_still_dir(dir_path, item['expected']):
            ppy.prntlog(ppy.PPY_WARN, 'changed before listing, skipped: %s' % (dir_path,))
            continue
        cur_digest = Digest()
        entries = []
        try:
            entries = os.listdir(dir_path)
        except (IOError, OSError):
            pe = ppy.current_exception()
            ppy.prntlog(ppy.PPY_WARN, 'cannot list %s: %s' % (dir_path, pe))
        for entry in entries:
            cursor.append(entry)
            entry_path = os.path.join(*cursor)
            try:
                classification = classify_and_decide(cursor, allowed_devs, ancestors)
                action = classification['action']
                ppy.prnt('???', action, entry_path)
                if action == 'descend':
                    target = classification['target']
                    pending_dirs.append({'cursor': cursor[:], 'ancestors': ancestors + [dir_key(target)], 'expected': target})
                elif action == 'read':
                    cur_digest.add_file(cursor[:], classification)
                elif action != 'skip':
                    raise Exception(action)
            except (IOError, OSError):
                # One bad entry must not end the whole crawl: log, go on.
                pe = ppy.current_exception()
                ppy.prntlog(ppy.PPY_ERROR, 'entry failed %s: %s' % (entry_path, pe))
            cursor.pop()
        ppy.prnt('---', dir_path, cur_digest.entries)
        sync_digest(cur_digest)

# ----------------------------------------
# (1) we have to obtain the names of paths + files, and know what their type is.

if __name__ == '__main__':
    ppy.prnt(','.join(sys.argv))
    if len(sys.argv) == 1:
        raise Exception('required argument: directory to crawl')
    name_kind, root_to_native, name_to_raw = ppy.choose_naming()
    start_dir = root_to_native(sys.argv[1])
    ppy.prnt('start_dir', start_dir, os.path.isdir(start_dir))
    if not os.path.isdir(start_dir):
        raise Exception('required argument: must be a directory')
    crawl_tree(start_dir)
