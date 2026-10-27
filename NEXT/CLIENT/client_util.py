"""Client-only helpers: reading files safely, classifying stat errors, and
converting path lists to and from the wire. Shared helpers are in SHARED/util.py."""

import portapy_sdk as ppy
import os
import stat
#portapy_pragma ALLOW_MODULE
import errno
#portapy_pragma ALLOW_MODULE
import pk_types as pk
#portapy_pragma ALLOW_MODULE
import util

# errno values meaning "the name no longer leads anywhere". -1 stands in for
# a constant the platform lacks; no real errno is negative.
VANISHED_ERRNOS = (getattr(errno, 'ENOENT', -1), getattr(errno, 'ENOTDIR', -1))
DANGLING_ERRNOS = VANISHED_ERRNOS + (getattr(errno, 'ELOOP', -1),)

# Flags for open_for_read(). O_NONBLOCK makes opening a FIFO return at once
# instead of waiting for a writer; it does not change reads of a regular
# file. O_BINARY exists only on Windows. Constants a platform lacks are 0.
READ_FLAGS = (os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))


# Reading: open what was classified, and only that.

def is_safe_stat(a, b):
    # type: (pk.PkStat, pk.PkStat) -> int
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

def open_for_read_T(path_list, target_stat, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkStat, pk.PkNamingP[pk.PkOsName]) -> pk.PkTuple[pk.PkAny, pk.PkOptional[pk.PkStat], pk.PkOptional[str], pk.PkOptional[int]]
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
        fd = os.open(N.os_join_path(path_list), READ_FLAGS)
    except (OSError, IOError):
        return (None, None, 'error', util.current_errno())
    try:
        st = os.fstat(fd)
    except (OSError, IOError):
        err = util.current_errno()
        os.close(fd)
        return (None, None, 'error', err)
    if not stat.S_ISREG(st[stat.ST_MODE]) or not is_safe_stat(st, target_stat):
        os.close(fd)
        return (None, st, 'changed', None)
    return (os.fdopen(fd, 'rb'), st, None, None)
def open_for_read(path_list, target_stat, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkStat, pk.PkNamingP[pk.PkOsName]) -> pk.PkOpened
    t = open_for_read_T(path_list, target_stat, N)
    return {
        'fp': t[0],
        'st': t[1],
        'state': t[2],
        'err': t[3]
        }


# ---------------------------------------------------------------------------
# Path lists <-> hexl_path. Needs the client's naming strategy (N).

def to_hex_path_list(path_list, N):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkNamingP[pk.PkOsName]) -> pk.PkHexPath
    """PkOsPath -> PkHexPath, element by element, root first."""
    hexes = []  # type: pk.PkList[pk.PkHexName]
    for name in path_list:
        hexes.append(util.hex_name(N.os_name_to_wire(name)))
    return pk.PkHexPath(hexes)


def from_hex_path_list(hex_path_list, N):
    # type: (pk.PkHexPath, pk.PkNamingP[pk.PkOsName]) -> pk.PkOsPath[pk.PkOsName]
    """Exact inverse of to_hex_path_list() for the client that made it: the server never calls this."""
    names = []  # type: pk.PkOsPath[pk.PkOsName]
    for h in hex_path_list:
        names.append(N.wire_to_os_name(util.unhex_name(h)))
    return names
