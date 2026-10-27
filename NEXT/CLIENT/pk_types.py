"""pybak's Pk type tags. Portable from Python 2.0 to 3.x; typed for mypy with
type comments, and with the tag definitions under 'if MYPY:' (portapy's
TYPES.md explains the pattern). Use them through 'import pk_types as pk'.

Names and paths mirror each other on the two sides:

    this machine                              the wire
    PkOsName: one name                        PkHexName: one hexlified name
    PkOsPath[PkOsName]: [name, ...] root first  PkHexPath: [PkHexName, ...] root first

A run uses exactly one name type, chosen at startup by naming.choose_naming():
bytes (naming.BytesNaming: native-bytes, win-utf8, win-codepage) or text
(naming.TextNaming: win-utf16le). PkOsName is a type variable restricted to
exactly those two, so code written once against PkNamingP[PkOsName] is checked
by mypy twice, once as all-bytes and once as all-text: a bytes name can never
reach a text call. Only client.py's main sees both, in one isinstance dispatch.

The first element of a path is the root as given on the command line, so it
may contain separators ('/home/jo', 'C:\\Users\\jo'); every other element is
one name from os.listdir and never does. The joined string the OS wants is
made by N.os_join_path(path_list) for one os call. Variables holding a
PkOsPath or PkHexPath are named *_path_list, since 'path' alone reads as a
string.

The path of a name, from the disk to the server and back:

    sys.argv ---N.argv_to_os_path---> PkOsPath [root]
    N.listdir(PkOsPath) ---> [PkOsName];  N.child(path_list, name) ---> PkOsPath
    PkOsName ---N.os_name_to_wire---> PkWireName ---hexlify---> PkHexName
    PkHexPath   (in the manifest, echoed back by the server)
    PkHexName ---unhexlify---> PkWireName ---N.wire_to_os_name---> PkOsName
"""

import portapy_sdk as ppy

# ---------------------------------------------------------------------------
# Checking constructors for the derived tags (the runtime side of the NewTypes).

_HEX_DIGITS = ppy.a2b('0123456789abcdef')


def _require_bytes(b, what):
    # type: (object, str) -> None
    if type(b) != ppy.PpyBytes:
        raise TypeError("%s: expected bytes, got %s" % (what, type(b)))


def _require_hex(b, what):
    # type: (bytes, str) -> None
    _require_bytes(b, what)
    if len(b) % 2 != 0:
        raise ValueError("%s: odd number of hex digits" % what)
    i = 0
    while i < len(b):
        if _HEX_DIGITS.find(b[i:i + 1]) < 0:
            raise ValueError("%s: not lowercase hex" % what)
        i = i + 1


def _require_count(n, what):
    # type: (int, str) -> None
    ppy.bv_int(n)
    if n < 0:
        raise ValueError("%s: negative" % what)


def _check_bytes(b):
    # type: (bytes) -> bytes
    _require_bytes(b, 'bytes tag')
    return b


def _check_hex_name(b):
    # type: (bytes) -> bytes
    _require_hex(b, 'PkHexName')
    return b


def _check_hex_path(names):
    # type: (ppy.PpyList[bytes]) -> ppy.PpyList[bytes]
    for n in ppy.bv_list(names):        # raises TypeError unless names is a list
        _check_hex_name(ppy.bv_bytes(n))
    return names


def _check_md5_digest(b):
    # type: (bytes) -> bytes
    _require_bytes(b, 'PkMd5Digest')
    if len(b) != 16:
        raise ValueError("PkMd5Digest: expected 16 bytes, got %d" % len(b))
    return b


def _check_md5_hex(b):
    # type: (bytes) -> bytes
    _require_hex(b, 'PkMd5Hex')
    if len(b) != 32:
        raise ValueError("PkMd5Hex: expected 32 hex digits, got %d" % len(b))
    return b


def _check_count(n):
    # type: (int) -> int
    _require_count(n, 'count tag')
    return n


def _check_name_kind(s):
    # type: (str) -> str
    ppy.require_ascii_str(s)
    return s


MYPY = 0
if MYPY:
    #portapy_pragma ALLOW_MODULE
    import typing
    import os

    # Source tags.
    PkArgvStr = str     # one element of sys.argv: a PpyNativeStr

    # Names and paths on this machine (see the module docstring).
    PkOsName = typing.TypeVar('PkOsName', bytes, str)                   # one name: bytes or text, the same for a whole run
    PkOsPath = typing.List[PkOsName]                                    # [root, name, name, ...]: use as PkOsPath[PkOsName]

    # Derived tags.
    PkWireName = typing.NewType('PkWireName', bytes)                    # bytes of one PkOsName: UTF-16LE under win-utf16le, the OS's bytes otherwise
    PkHexName = typing.NewType('PkHexName', ppy.PpyAsciiBytes)          # hexlify(PkWireName): lowercase hex digits
    PkHexPath = typing.NewType('PkHexPath', typing.List[PkHexName])     # the hexl_path: one PkHexName per component, root first
    PkMd5Digest = typing.NewType('PkMd5Digest', bytes)                  # 16 raw bytes from an md5 hasher
    PkMd5Hex = typing.NewType('PkMd5Hex', PkHexName)                    # hexlify(PkMd5Digest): 32 lowercase hex digits
    PkLength = typing.NewType('PkLength', int)                          # a file length in bytes
    PkOffset = typing.NewType('PkOffset', int)                          # a byte offset into a file: distinct from PkLength
    PkFileBytes = typing.NewType('PkFileBytes', bytes)                  # a chunk read from a file
    PkNameKind = typing.NewType('PkNameKind', str)                      # 'native-bytes', 'win-utf8', 'win-utf16le', 'win-codepage'

    # Record shapes: the client uses dicts as records. Call form, since the
    # class form needs annotation syntax, which Python 2.0 cannot parse.
    PkStat = os.stat_result
    PkDirKey = typing.Optional[typing.Tuple[int, int]]
    PkEntryKind = typing.TypedDict('PkEntryKind', {'kind': str, 'lst': typing.Optional[PkStat], 'target': typing.Optional[PkStat], 'err': typing.Optional[int]})
    PkClassification = typing.TypedDict('PkClassification', {'action': str, 'kind': str, 'lst': typing.Optional[PkStat], 'target': typing.Optional[PkStat], 'err': typing.Optional[int]})
    PkOpened = typing.TypedDict('PkOpened', {'fp': typing.Any, 'st': typing.Optional[PkStat], 'state': typing.Optional[str], 'err': typing.Optional[int]})
    PkFileMetadata = typing.TypedDict('PkFileMetadata', {'lstat': PkStat, 'stat': typing.Optional[PkStat]})   # 'stat' is None when it equals 'lstat'
    PkHttpResponse = typing.TypedDict('PkHttpResponse', {'status': int, 'headers': typing.Dict[bytes, bytes], 'body': bytes})
    PkSender = typing.Callable[[PkHexPath, PkFileBytes, PkOffset], None]  # sends one chunk: (hexl_path, chunk, offset of the chunk)

    # What naming.BytesNaming and naming.TextNaming both provide, for code
    # written once for either. Class attributes give the types of the
    # instances' attributes (no annotation syntax: Python 2.0 parses this).
    class PkNamingP(typing.Protocol[PkOsName]):
        kind = PkNameKind('')  # type: PkNameKind
        is_lossy = 0  # type: int
        # Facts about this client, for the manifest header (naming.py's docstring).
        fs_codec = None  # type: typing.Optional[str]
        fs_errors = None  # type: typing.Optional[str]
        locale_codec = None  # type: typing.Optional[str]
        platform = ''  # type: str
        python = ''  # type: str
        hostname = None  # type: typing.Optional[str]
        win32 = 0  # type: int

        def argv_to_os_path(self, arg):
            # type: (PkArgvStr) -> typing.List[PkOsName]
            pass
        def ascii_to_os_name(self, a):
            # type: (str) -> PkOsName
            pass
        def os_name_to_wire(self, name):
            # type: (PkOsName) -> PkWireName
            pass
        def wire_to_os_name(self, raw):
            # type: (PkWireName) -> PkOsName
            pass
        def listdir(self, path_list):
            # type: (typing.List[PkOsName]) -> typing.List[PkOsName]
            pass
        def child(self, path_list, name):
            # type: (typing.List[PkOsName], PkOsName) -> typing.List[PkOsName]
            pass
        def os_join_path(self, path_list):
            # type: (typing.List[PkOsName]) -> PkOsName
            pass
        def has_suffix(self, name, ascii_suffix):
            # type: (PkOsName, str) -> int
            pass
        def split_name(self, name, ascii_sep):
            # type: (PkOsName, str) -> typing.List[PkOsName]
            pass

    # Generic helpers for type comments, as in portapy.
    _GT = typing.TypeVar('_GT')
    _GK = typing.TypeVar('_GK')
    _GV = typing.TypeVar('_GV')
    _GR = typing.TypeVar('_GR')
    _GTs = typing.TypeVarTuple('_GTs')
    _GP = typing.ParamSpec('_GP')
    PkList = typing.List[_GT]
    PkDict = typing.Dict[_GK, _GV]
    PkTuple = typing.Tuple[typing.Unpack[_GTs]]
    PkOptional = typing.Optional[_GT]
    PkUnion2 = typing.Union[_GT, _GK]
    PkUnion3 = typing.Union[_GT, _GK, _GV]
    PkCallable = typing.Callable[_GP, _GR]
    PkAny = typing.Any
else:
    PkArgvStr = ppy.PpyNativeStr
    PkWireName = _check_bytes
    PkHexName = _check_hex_name
    PkHexPath = _check_hex_path
    PkMd5Digest = _check_md5_digest
    PkMd5Hex = _check_md5_hex
    PkLength = _check_count
    PkOffset = _check_count
    PkFileBytes = _check_bytes
    PkNameKind = _check_name_kind
