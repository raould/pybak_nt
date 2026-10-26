import portapy_sdk as ppy
import sys
import os

#----------------------------------------
# Filename strategy for pybak.

"""
Portable from Python 2.0 to 3.x. No version checks and no OS-name checks:
every choice is a feature test, made once at startup by choose_naming().

A strategy is a tuple:

    (name_kind, argv_to_native, name_to_bytes, bytes_to_name)

- name_kind       recorded in the manifest header; tells the server how to
                  decode names for display.
- argv_to_native  converts a sys.argv root into the native path type that
                  the strategy walks with (bytes or text).
- name_to_bytes     converts a os.listdir() entry into raw bytes for hexing.
- bytes_to_name     mystr == bytes_to_name(name_to_bytes(mystr))
- ascii_to_native ascii -> 'native', whatever that means.

os.listdir() returns names of the same type as its argument, so once the
root is converted, the walk itself never converts anything except through
name_to_bytes.
"""

#
# Feature flags, computed once.
# Many of these are just for pybak.
#

# Is the native str type already bytes? Python 2: yes. Python 3: no.
try:
    PPY_NATIVE_STR_IS_BYTES = (bytes is str)
except NameError:
    PPY_NATIVE_STR_IS_BYTES = 1

_PPY_NATIVE_STR = type('')

# Python 2's text type, or None on Python 3.
try:
    PPY_UNICODE = unicode
except NameError:
    PPY_UNICODE = None

# Code point -> one-character text, on every version.
try:
    PPY_UNICHR = unichr
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
    """The codec this interpreter uses for ALL OS names, lowercased.

    This is sys.getfilesystemencoding(), whose Python name is misleading: it
    does not inspect any filesystem or mount. It is one process-wide setting,
    chosen at startup (POSIX: from the locale or UTF-8 mode; Windows: 'mbcs'
    or 'utf-8'; macOS: 'utf-8'), telling how Python converts between its text
    type and the bytes the OS API uses for names. It says nothing about the
    encoding of names on a particular disk. Returns None before Python 2.3.
    """
    getter = getattr(sys, 'getfilesystemencoding', None)
    if getter is None:
        return None
    enc = getter()
    if enc is None:
        return None
    return enc.lower()


def has_win32_core():
    """True if Python is running on the Win32 API family (nt or ce core)."""
    names = sys.builtin_module_names
    return ('nt' in names) or ('ce' in names)


def unicode_filenames_supported():
    """True if the OS layer accepts text paths without a code page (2.3+)."""
    return getattr(os.path, 'supports_unicode_filenames', 0)


def is_utf8_name(enc):
    return enc == 'utf-8' or enc == 'utf8'


#
# Root converters: sys.argv entry -> native path for the walk.
#

def argv_to_bytes(arg):
    """Root as raw bytes. Python 2 argv is already bytes."""
    if PPY_NATIVE_STR_IS_BYTES:
        return arg
    fsencode = getattr(os, 'fsencode', None)      # 3.2+
    if fsencode is not None:
        return fsencode(arg)
    enc = interpreter_name_codec()
    try:
        return arg.encode(enc, 'surrogateescape')  # 3.1
    except LookupError:
        return arg.encode(enc)                     # 3.0


def argv_to_text(arg):
    """Root as text, for the UTF-16 strategy.

    Python 2 argv on Windows is code-page bytes: characters outside the code
    page have already become '?'. Refuse rather than walk the wrong path.
    """
    if PPY_UNICODE is not None and type(arg) == _PPY_NATIVE_STR:
        text = PPY_UNICODE(arg, 'mbcs')
        if contains_question_mark(text):
            raise ValueError(
                "root path contains '?': its real name was lost by the "
                "Windows code page before Python saw it; pass a path "
                "without non-code-page characters")
        return text
    return arg


def argv_identity(arg):
    return arg


def contains_question_mark(text):
    for c in text:
        if ord(c) == 63:
            return 1
    return 0


#
# Name converters: one os.listdir() entry -> raw bytes.
#

def name_identity(name):
    """The entry is already raw bytes."""
    return name


def name_to_utf16le(name):
    """Text entry -> UTF-16LE code units as bytes, lone surrogates kept."""
    try:
        return name.encode('utf-16-le', 'surrogatepass')   # 3.1+
    except LookupError:
        return name.encode('utf-16-le')   # Python 2 never rejects surrogates


def utf16le_to_name(utf):
    """UTF-16LE code units as bytes -> Text entry, lone surrogates kept."""
    try:
        return name.decode('utf-16-le', 'surrogatepass')   # 3.1+
    except LookupError:
        return name.decode('utf-16-le')   # Python 2 never rejects surrogates

#
# ASCII to 'native' string format, so the ASCII can be
# compared with the results of os.listdir(), (before those
# reults are converted to binary with other functions.)
#

def ascii_to_str(a):
    return ppy.a2b(a)

def ascii_to_utf16le(a):
    """Text entry -> UTF-16LE code units as bytes, lone surrogates kept."""
    try:
        return name.encode('utf-16-le', 'surrogatepass')   # 3.1+
    except LookupError:
        return name.encode('utf-16-le')   # Python 2 never rejects surrogates

#
# Strategy selection.
#

def choose_naming_T():
    """
    This is currently mainly just for pybak.
    Return (name_kind, argv_to_native, name_to_bytes) for this interpreter.
    name_kind: NATIVE_BYTES, WIN_UTF8, WIN_UTF16LE, WIN_CODEPAGE.
    argv_to_native: convert sys.argv input to a type to pass to os.listdir.
    name_to_bytes: convert path names from os.listdir into byte equivalent.
    bytes_to_name: convert byte strings back to original python string format.
    ascii_to_native: ascii -> 'native' string format, whatever that means.
    """
    enc = interpreter_name_codec()
    win32 = has_win32_core()
    if enc is None:
        # Python 2.0-2.2: no way to ask; the Win32 core means code pages.
        if win32:
            return (PPY_WIN_CODEPAGE, argv_identity, name_identity, name_identity)
        return (PPY_NATIVE_BYTES, argv_to_bytes, name_identity, name_identity)
    if enc == 'mbcs':
        # Python converts names through the ANSI code page: bytes API lossy.
        if unicode_filenames_supported():
            return (PPY_WIN_UTF16LE, argv_to_text, name_to_utf16le, utf16le_to_name)
        return (PPY_WIN_CODEPAGE, argv_identity, name_identity, name_identity)
    if win32 and is_utf8_name(enc):
        return (PPY_WIN_UTF8, argv_to_bytes, name_identity, name_identity)   # PEP 529, 3.6+
    return (PPY_NATIVE_BYTES, argv_to_bytes, name_identity, name_identity)

def choose_naming():
    t = choose_naming_T()
    return {
        'name_kind': t[0],
        'argv_to_native': t[1],
        'name_to_bytes': t[2],
        'bytes_to_name': t[3]
    }

def is_lossy(name_kind):
    return name_kind == PPY_WIN_CODEPAGE
