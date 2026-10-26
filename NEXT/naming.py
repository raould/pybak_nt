import portapy_sdk as ppy
import sys
import os
#portapy_pragma ALLOW_MODULE
import pk_types as pk

#----------------------------------------
# Filename strategy for pybak.

"""
Portable from Python 2.0 to 3.x. No version checks and no OS-name checks:
every choice is a feature test, made once at startup by choose_naming().

A strategy is one of two classes, each with exactly one name type:

  BytesNaming   names are bytes: native-bytes (POSIX, macOS), win-utf8
                (Windows, Python 3.6+), win-codepage (Windows 2.0-2.2, 9x;
                LOSSY).
  TextNaming    names are text: win-utf16le (Windows, Python 2.3-3.5).

Both provide pk.PkNamingP: code above this module is written once, generic
over pk.PkOsName, and mypy checks it for bytes and for text separately.

Each class's own methods are typed with its one concrete type, so they are
checked against the real os.listdir, os.path.join, ... with no casts. The
logic the two share is in generic module functions (_listdir, ...).

  kind              PkNameKind: sent in the manifest header; tells the server
                    how to decode names for display.
  is_lossy          true if names cannot be trusted (win-codepage).

  argv_to_os_path(arg)            -> [root]: a path list from one sys.argv entry.
  ascii_to_os_name(a)             -> a constant, comparable with names.
  os_name_to_wire(name)           -> PkWireName: bytes to hexlify.
  wire_to_os_name(raw)            -> the name again: exact inverse.
  listdir(path_list)              -> [name, ...] in a directory.
  child(path_list, name)          -> the path list one level down.
  os_join_path(path_list)         -> the joined string, for one os call.
  has_suffix, split_name          name operations with ASCII constants.

Typed with type comments and checked by mypy. Lines that only run on
Python 2 carry '# type: ignore' with the reason.
"""

#
# Feature flags, computed once.
#

# Python 2's text type, or None on Python 3.
try:
    PPY_UNICODE = unicode  # type: ppy.PpyOptional[type]  # type: ignore[name-defined]
except NameError:
    PPY_UNICODE = None

# Code point -> one-character text, on every version.
try:
    PPY_UNICHR = unichr  # type: ppy.PpyCallable[[int], ppy.PpyText]  # type: ignore[name-defined]
except NameError:
    PPY_UNICHR = chr

PPY_NATIVE_BYTES = 'native-bytes'      # names are the filesystem's own bytes
PPY_WIN_UTF8 = 'win-utf8'              # Windows names as UTF-8 bytes (PEP 529)
PPY_WIN_UTF16LE = 'win-utf16le'        # Windows names as UTF-16LE code units
PPY_WIN_CODEPAGE = 'win-codepage'      # Windows names via ANSI code page: LOSSY


#
# Feature probes.
#

def interpreter_name_codec():
    # type: () -> ppy.PpyOptional[str]
    """The codec this interpreter uses for ALL OS names, lowercased.

    This is sys.getfilesystemencoding(), whose Python name is misleading: it
    does not inspect any filesystem or mount. It is one process-wide setting,
    chosen at startup (POSIX: from the locale or UTF-8 mode; Windows: 'mbcs'
    or 'utf-8'; macOS: 'utf-8'), telling how Python converts between its text
    type and the bytes the OS API uses for names. It says nothing about the
    encoding of names on a particular disk. Returns None before Python 2.3.
    """
    getter = getattr(sys, 'getfilesystemencoding', None)  # type: ppy.PpyOptional[ppy.PpyCallable[[], ppy.PpyOptional[str]]]
    if getter is None:
        return None
    enc = getter()
    if enc is None:
        return None
    return enc.lower()


def has_win32_core():
    # type: () -> int
    """True if Python is running on the Win32 API family (nt or ce core)."""
    names = sys.builtin_module_names
    if ('nt' in names) or ('ce' in names):
        return 1
    return 0


def unicode_filenames_supported():
    # type: () -> int
    """True if the OS layer accepts text paths without a code page (2.3+)."""
    supported = getattr(os.path, 'supports_unicode_filenames', 0)  # type: int
    return supported


def is_utf8_name(enc):
    # type: (ppy.PpyOptional[str]) -> int
    if enc == 'utf-8' or enc == 'utf8':
        return 1
    return 0


#
# Root converters: one sys.argv entry -> the root, as the first name of a path
# list. (The root may contain separators; no other name does.)
#

def argv_to_bytes(arg):
    # type: (pk.PkArgvStr) -> bytes
    """Root as raw bytes. Python 2 argv is already bytes."""
    if ppy.PPY_NATIVE_STR_IS_BYTES:
        return arg  # type: ignore[return-value]  # Python 2: str is bytes
    fsencode = getattr(os, 'fsencode', None)  # type: ppy.PpyOptional[ppy.PpyCallable[[str], bytes]]  # 3.2+
    if fsencode is not None:
        return fsencode(arg)
    enc = interpreter_name_codec()
    if enc is None:
        raise ValueError("no filesystem encoding to convert the root with")
    try:
        return arg.encode(enc, 'surrogateescape')  # 3.1
    except LookupError:
        return arg.encode(enc)                     # 3.0


def argv_codepage_bytes(arg):
    # type: (pk.PkArgvStr) -> bytes
    """win-codepage (Python 2.0-2.2 or 9x): argv is already code-page bytes."""
    return arg  # type: ignore[return-value]  # Python 2 only: str is bytes


def argv_to_text(arg):
    # type: (pk.PkArgvStr) -> ppy.PpyText
    """Root as text, for the UTF-16 strategy.

    Python 2 argv on Windows is code-page bytes: characters outside the code
    page have already become '?'. Refuse rather than walk the wrong path.
    """
    if PPY_UNICODE is not None and type(arg) == type(''):
        text = PPY_UNICODE(arg, 'mbcs')  # type: ppy.PpyText  # Python 2 only: decode the code page
        if contains_question_mark(text):
            raise ValueError(
                "root path contains '?': its real name was lost by the "
                "Windows code page before Python saw it; pass a path "
                "without non-code-page characters")
        return text
    return arg


def contains_question_mark(text):
    # type: (ppy.PpyText) -> int
    for c in text:
        if ord(c) == 63:
            return 1
    return 0


def ascii_to_text(a):
    # type: (ppy.PpyAsciiStr) -> ppy.PpyText
    """An ASCII constant as text, for the UTF-16 strategy."""
    ppy.require_ascii_str(a)
    if PPY_UNICODE is not None:
        text = PPY_UNICODE(a)  # type: ppy.PpyText  # Python 2 only: unicode
        return text
    return a                      # Python 3: str is already text


#
# The logic both strategies share, written once, generic over the name type.
#

def _listdir(path_list):
    # type: (pk.PkOsPath[pk.PkOsName]) -> pk.PkOsPath[pk.PkOsName]
    return os.listdir(_os_join_path(path_list))


def _child(path_list, name):
    # type: (pk.PkOsPath[pk.PkOsName], pk.PkOsName) -> pk.PkOsPath[pk.PkOsName]
    """A new list: path_list itself is not changed."""
    return path_list + [name]


def _os_join_path(path_list):
    # type: (pk.PkOsPath[pk.PkOsName]) -> pk.PkOsName
    return os.path.join(*path_list)


def _has_suffix(name, suffix):
    # type: (pk.PkOsName, pk.PkOsName) -> int
    if name.endswith(suffix):
        return 1
    return 0


def _split_name(name, sep):
    # type: (pk.PkOsName, pk.PkOsName) -> pk.PkList[pk.PkOsName]
    return name.split(sep)


#
# The two strategies.
#

class BytesNaming:   # no '()': empty parentheses are a syntax error before Python 2.5
    """Names are bytes: they are their own wire bytes."""
    def __init__(self, kind, is_lossy, argv_to_root_fn):
        # type: (str, int, ppy.PpyCallable[[pk.PkArgvStr], bytes]) -> None
        self.kind = pk.PkNameKind(kind)
        self.is_lossy = is_lossy
        self._argv_to_root = argv_to_root_fn

    def argv_to_os_path(self, arg):
        # type: (pk.PkArgvStr) -> pk.PkOsPath[bytes]
        return [self._argv_to_root(arg)]

    def ascii_to_os_name(self, a):
        # type: (ppy.PpyAsciiStr) -> bytes
        return ppy.a2b(a)

    def os_name_to_wire(self, name):
        # type: (bytes) -> pk.PkWireName
        return pk.PkWireName(name)

    def wire_to_os_name(self, raw):
        # type: (pk.PkWireName) -> bytes
        return raw

    def listdir(self, path_list):
        # type: (pk.PkOsPath[bytes]) -> pk.PkOsPath[bytes]
        return _listdir(path_list)

    def child(self, path_list, name):
        # type: (pk.PkOsPath[bytes], bytes) -> pk.PkOsPath[bytes]
        return _child(path_list, name)

    def os_join_path(self, path_list):
        # type: (pk.PkOsPath[bytes]) -> bytes
        return _os_join_path(path_list)

    def has_suffix(self, name, ascii_suffix):
        # type: (bytes, ppy.PpyAsciiStr) -> int
        return _has_suffix(name, self.ascii_to_os_name(ascii_suffix))

    def split_name(self, name, ascii_sep):
        # type: (bytes, ppy.PpyAsciiStr) -> pk.PkList[bytes]
        return _split_name(name, self.ascii_to_os_name(ascii_sep))


class TextNaming:
    """Names are text from the Windows wide API; UTF-16LE code units on the wire."""
    def __init__(self, kind, argv_to_root_fn):
        # type: (str, ppy.PpyCallable[[pk.PkArgvStr], ppy.PpyText]) -> None
        self.kind = pk.PkNameKind(kind)
        self.is_lossy = 0
        self._argv_to_root = argv_to_root_fn

    def argv_to_os_path(self, arg):
        # type: (pk.PkArgvStr) -> pk.PkOsPath[ppy.PpyText]
        return [self._argv_to_root(arg)]

    def ascii_to_os_name(self, a):
        # type: (ppy.PpyAsciiStr) -> ppy.PpyText
        return ascii_to_text(a)

    def os_name_to_wire(self, name):
        # type: (ppy.PpyText) -> pk.PkWireName
        """UTF-16LE code units, lone surrogates kept."""
        try:
            return pk.PkWireName(name.encode('utf-16-le', 'surrogatepass'))   # 3.1+
        except LookupError:
            return pk.PkWireName(name.encode('utf-16-le'))   # Python 2 never rejects surrogates

    def wire_to_os_name(self, raw):
        # type: (pk.PkWireName) -> ppy.PpyText
        """Exact inverse of os_name_to_wire."""
        try:
            return raw.decode('utf-16-le', 'surrogatepass')   # 3.1+
        except LookupError:
            return raw.decode('utf-16-le')   # Python 2 never rejects surrogates

    def listdir(self, path_list):
        # type: (pk.PkOsPath[ppy.PpyText]) -> pk.PkOsPath[ppy.PpyText]
        return _listdir(path_list)

    def child(self, path_list, name):
        # type: (pk.PkOsPath[ppy.PpyText], ppy.PpyText) -> pk.PkOsPath[ppy.PpyText]
        return _child(path_list, name)

    def os_join_path(self, path_list):
        # type: (pk.PkOsPath[ppy.PpyText]) -> ppy.PpyText
        return _os_join_path(path_list)

    def has_suffix(self, name, ascii_suffix):
        # type: (ppy.PpyText, ppy.PpyAsciiStr) -> int
        return _has_suffix(name, self.ascii_to_os_name(ascii_suffix))

    def split_name(self, name, ascii_sep):
        # type: (ppy.PpyText, ppy.PpyAsciiStr) -> pk.PkList[ppy.PpyText]
        return _split_name(name, self.ascii_to_os_name(ascii_sep))


MYPY = 0
if MYPY:
    #portapy_pragma ALLOW_MODULE
    import typing
    NamingChoice = typing.Union[BytesNaming, TextNaming]   # what choose_naming() returns: narrow it with isinstance


def make_win_clear_enc():
    # type: () -> BytesNaming
    """Windows, Python 2.0-2.2 or 9x/ME: names through the ANSI code page. LOSSY."""
    return BytesNaming(PPY_WIN_CODEPAGE, 1, argv_codepage_bytes)

def make_clear_enc():
    # type: () -> BytesNaming
    """POSIX (and macOS), every Python: names are the filesystem's own bytes."""
    return BytesNaming(PPY_NATIVE_BYTES, 0, argv_to_bytes)

def make_utf16le_enc():
    # type: () -> TextNaming
    """Windows, Python 2.3-3.5: names are text from the wide API; UTF-16LE on the wire."""
    return TextNaming(PPY_WIN_UTF16LE, argv_to_text)

def make_win_utf8_enc():
    # type: () -> BytesNaming
    """Windows, Python 3.6+ (PEP 529): names are UTF-8 bytes."""
    return BytesNaming(PPY_WIN_UTF8, 0, argv_to_bytes)

def choose_naming():
    # type: () -> NamingChoice
    """
    Return instance of Naming class.
    """
    enc = interpreter_name_codec()
    win32 = has_win32_core()
    if enc is None:
        # Python 2.0-2.2: no way to ask; the Win32 core means code pages.
        if win32:
            return make_win_clear_enc()
        return make_clear_enc()
    if enc == 'mbcs':
        # Python converts names through the ANSI code page: bytes API lossy.
        if unicode_filenames_supported():
            return make_utf16le_enc()
        return make_win_clear_enc()
    if win32 and is_utf8_name(enc):
        return make_win_utf8_enc()   # PEP 529, 3.6+
    return make_clear_enc()
