"""Filename strategy selection for the pybak client.

Portable from Python 2.0 to 3.x. No version checks and no OS-name checks:
every choice is a feature test, made once at startup by choose_naming().

A strategy is a tuple:

    (name_kind, root_to_native, name_to_raw)

- name_kind       recorded in the manifest header; tells the server how to
                  decode names for display.
- root_to_native  converts a sys.argv root into the native path type that
                  the strategy walks with (bytes or text).
- name_to_raw     converts one os.listdir() entry into raw bytes for hexing.

os.listdir() returns names of the same type as its argument, so once the
root is converted, the walk itself never converts anything except through
name_to_raw.
"""

import os
import sys
#portapy_pragma ALLOW_MODULE
import tempfile

# ---------------------------------------------------------------------------
# Feature flags, computed once.

# Is the native str type already bytes? Python 2: yes. Python 3: no.
try:
    NATIVE_STR_IS_BYTES = (bytes is str)
except NameError:
    NATIVE_STR_IS_BYTES = 1

NATIVE_STR = type('')

# Python 2's text type, or None on Python 3.
try:
    _UNICODE = unicode
except NameError:
    _UNICODE = None

# Code point -> one-character text, on every version.
try:
    _UNICHR = unichr
except NameError:
    _UNICHR = chr

NATIVE_BYTES = 'native-bytes'      # names are the filesystem's own bytes
WIN_UTF8 = 'win-utf8'              # Windows names as UTF-8 bytes (PEP 529)
WIN_UTF16LE = 'win-utf16le'        # Windows names as UTF-16LE code units
WIN_CODEPAGE = 'win-codepage'      # Windows names via ANSI code page: LOSSY


# ---------------------------------------------------------------------------
# Feature probes.

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


# ---------------------------------------------------------------------------
# Root converters: sys.argv entry -> native path for the walk.

def root_to_bytes(arg):
    """Root as raw bytes. Python 2 argv is already bytes."""
    if NATIVE_STR_IS_BYTES:
        return arg
    fsencode = getattr(os, 'fsencode', None)      # 3.2+
    if fsencode is not None:
        return fsencode(arg)
    enc = interpreter_name_codec()
    try:
        return arg.encode(enc, 'surrogateescape')  # 3.1
    except LookupError:
        return arg.encode(enc)                     # 3.0


def root_to_text(arg):
    """Root as text, for the UTF-16 strategy.

    Python 2 argv on Windows is code-page bytes: characters outside the code
    page have already become '?'. Refuse rather than walk the wrong path.
    """
    if _UNICODE is not None and type(arg) == NATIVE_STR:
        text = _UNICODE(arg, 'mbcs')
        if contains_question_mark(text):
            raise ValueError(
                "root path contains '?': its real name was lost by the "
                "Windows code page before Python saw it; pass a path "
                "without non-code-page characters")
        return text
    return arg


def root_identity(arg):
    return arg


def contains_question_mark(text):
    for c in text:
        if ord(c) == 63:
            return 1
    return 0


# ---------------------------------------------------------------------------
# Name converters: one os.listdir() entry -> raw bytes.

def name_identity(name):
    """The entry is already raw bytes."""
    return name


def name_to_utf16le(name):
    """Text entry -> UTF-16LE code units as bytes, lone surrogates kept."""
    try:
        return name.encode('utf-16-le', 'surrogatepass')   # 3.1+
    except LookupError:
        return name.encode('utf-16-le')   # Python 2 never rejects surrogates


# ---------------------------------------------------------------------------
# Strategy selection.

def choose_naming():
    """Return (name_kind, root_to_native, name_to_raw) for this interpreter."""
    enc = interpreter_name_codec()
    win32 = has_win32_core()
    if enc is None:
        # Python 2.0-2.2: no way to ask; the Win32 core means code pages.
        if win32:
            return (WIN_CODEPAGE, root_identity, name_identity)
        return (NATIVE_BYTES, root_to_bytes, name_identity)
    if enc == 'mbcs':
        # Python converts names through the ANSI code page: bytes API lossy.
        if unicode_filenames_supported():
            return (WIN_UTF16LE, root_to_text, name_to_utf16le)
        return (WIN_CODEPAGE, root_identity, name_identity)
    if win32 and is_utf8_name(enc):
        return (WIN_UTF8, root_to_bytes, name_identity)   # PEP 529, 3.6+
    return (NATIVE_BYTES, root_to_bytes, name_identity)


def is_lossy(name_kind):
    return name_kind == WIN_CODEPAGE


# ---------------------------------------------------------------------------
# Other OS functions that exotic ports may lack.

def get_lstat():
    """os.lstat where it exists (Python 2 on Windows has none), else os.stat."""
    return getattr(os, 'lstat', os.stat)


# ---------------------------------------------------------------------------
# Active self-test: confirm the chosen strategy really round-trips names.

def make_bytes(ints):
    if NATIVE_STR_IS_BYTES:
        chars = []
        for i in ints:
            chars.append(chr(i))
        return ''.join(chars)
    return bytes(ints)


def probe_text():
    """'probe-' + e-acute + a character above U+FFFF, as text."""
    text = 'probe-'
    if _UNICODE is not None:
        text = _UNICODE(text)
    text = text + _UNICHR(0xe9)
    try:
        text = text + _UNICHR(0x1f600)
    except ValueError:
        # Narrow Python 2 build: write the surrogate pair explicitly.
        text = text + _UNICHR(0xd83d) + _UNICHR(0xde00)
    return text


# UTF-8 bytes of probe_text(): "probe-" + C3 A9 + F0 9F 98 80
PROBE_UTF8 = (0x70, 0x72, 0x6f, 0x62, 0x65, 0x2d,
              0xc3, 0xa9, 0xf0, 0x9f, 0x98, 0x80)


def make_temp_dir():
    mkdtemp = getattr(tempfile, 'mkdtemp', None)      # 2.3+
    if mkdtemp is not None:
        return mkdtemp()
    path = tempfile.mktemp()
    os.mkdir(path)
    return path


def self_test_naming(strategy):
    """Create a probe file in a temp dir and check the strategy round-trips it.

    Returns (ok, message). ok is 1 or 0. Never touches the user's folders.
    Exact bytes may differ on normalizing filesystems (e.g. HFS+ NFD); that
    is reported as information, not failure, as long as the listed name
    re-opens the same file.
    """
    name_kind = strategy[0]
    root_to_native = strategy[1]
    name_to_raw = strategy[2]
    if is_lossy(name_kind):
        return (0, "lossy strategy %s: no round-trip possible" % name_kind)
    temp_dir = make_temp_dir()
    try:
        result = _probe(temp_dir, name_kind, root_to_native, name_to_raw)
    finally:
        _remove_tree_one_level(temp_dir)
    return result


def _probe(temp_dir, name_kind, root_to_native, name_to_raw):
    native_dir = root_to_native(temp_dir)
    if name_kind == WIN_UTF16LE:
        created = probe_text()
        expected_raw = name_to_utf16le(created)
    else:
        created = make_bytes(PROBE_UTF8)
        expected_raw = created
    marker = make_bytes((0x70, 0x79, 0x62, 0x61, 0x6b))   # "pybak"
    try:
        handle = open(os.path.join(native_dir, created), 'wb')
        try:
            handle.write(marker)
        finally:
            handle.close()
    except (IOError, OSError, UnicodeError):
        return (0, "cannot create probe file with strategy %s" % name_kind)
    entries = os.listdir(native_dir)
    if len(entries) != 1:
        return (0, "expected 1 probe entry, found %d" % len(entries))
    listed = entries[0]
    raw = name_to_raw(listed)
    handle = open(os.path.join(native_dir, listed), 'rb')
    try:
        content = handle.read()
    finally:
        handle.close()
    if content != marker:
        return (0, "listed name did not re-open the probe file")
    if raw != expected_raw:
        return (1, "ok; filesystem changed the name bytes "
                   "(normalizing filesystem)")
    return (1, "ok")


def _remove_tree_one_level(path):
    # The temp dir holds only probe files; remove them, then the dir.
    # Listing with the same type as `path` keeps the joined paths valid.
    for name in os.listdir(path):
        try:
            os.remove(os.path.join(path, name))
        except (IOError, OSError):
            pass
    try:
        os.rmdir(path)
    except (IOError, OSError):
        pass


# ---------------------------------------------------------------------------

def main():
    strategy = choose_naming()
    sys.stdout.write("name_kind=%s interpreter_name_codec=%s win32=%s\n" % (
        strategy[0], interpreter_name_codec(), has_win32_core()))
    ok_message = self_test_naming(strategy)
    sys.stdout.write("self_test ok=%s %s\n" % (ok_message[0], ok_message[1]))
    if not ok_message[0]:
        sys.exit(1)


if __name__ == "__main__":
    main()
