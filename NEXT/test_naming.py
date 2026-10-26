"""Contract tests for every naming strategy. Portable; run in every interpreter image.

Not type-checked by mypy: it feeds raw bytes and text straight into the
strategies on purpose, which the PkOsName/PkWireName tags exist to forbid.

Each make_*_enc() is tested on whatever machine runs this: the strategies are pure
conversions, so win-utf16le can be checked on Linux with text names. Only
test_chosen_matches_listdir needs the real platform.
"""

import sys
import os
import portapy_sdk as ppy
#portapy_pragma ALLOW_MODULE
import naming
#portapy_pragma ALLOW_MODULE
import pk_types as pk


def check(failures, cond, label):
    if not cond:
        failures.append(label)


def bytes_type():
    return type(ppy.a2b('x'))


def text_type():
    if naming.PPY_UNICODE is not None:
        return naming.PPY_UNICODE
    return type('')


def make_text(code_points):
    """Text from code points, on every version."""
    text = ''
    if naming.PPY_UNICODE is not None:
        text = naming.PPY_UNICODE(text)
    for cp in code_points:
        text = text + naming.PPY_UNICHR(cp)
    return text


def byte_samples():
    samples = [ppy.a2b('plain'), ppy.a2b('with space'), ppy.a2b('')]
    high = []
    i = 1
    while i < 256:
        if i != 47:                     # every byte a POSIX name may hold: not NUL, not '/'
            high.append(ppy.byte_from_int(i))
        i = i + 1
    samples.append(ppy.a2b('').join(high))
    return samples


def emoji_text():
    """U+1F600 as text: one character where the build allows it, else its surrogate pair (narrow Python 2).
    Python 3 joins a decoded pair into the one character, as Windows listdir returns it."""
    try:
        return make_text((0x1f600,))
    except ValueError:
        return make_text((0xd83d, 0xde00))


def text_samples():
    samples = [make_text((0x70, 0x6c, 0x61, 0x69, 0x6e)),          # plain
               make_text((0x63, 0x61, 0x66, 0xe9)),                # cafe with e-acute
               emoji_text(),                                       # above U+FFFF
               make_text((0x6c, 0x6f, 0x6e, 0x65, 0xd800, 0x78))]  # lone surrogate: legal on NTFS
    return samples


def raises(fn, arg):
    try:
        fn(arg)
    except Exception:
        return 1
    return 0


def check_strategy(failures, n, names, native_type, lossy):
    label = n.kind
    for name in names:
        raw = n.os_name_to_wire(name)
        check(failures, type(raw) == bytes_type(), "%s: os_name_to_wire gives bytes" % label)
        check(failures, n.wire_to_os_name(raw) == name, "%s: os_name_to_wire/wire_to_os_name round trip %r" % (label, name))
    for constant in ('_', '.jpg', 'Thumbs.db'):
        native = n.ascii_to_os_name(constant)
        check(failures, type(native) == native_type, "%s: ascii_to_os_name(%r) has the type listdir returns" % (label, constant))
    check(failures, raises(n.ascii_to_os_name, 'caf' + chr(0xe9)), "%s: ascii_to_os_name refuses non-ASCII" % label)
    check(failures, (not not n.is_lossy) == lossy, "%s: is_lossy" % label)
    jpg = n.ascii_to_os_name('photo.jpg')
    check(failures, n.has_suffix(jpg, '.jpg') and not n.has_suffix(jpg, '.png'), "%s: has_suffix" % label)
    parts = n.split_name(n.ascii_to_os_name('0123_42.mdj'), '_')
    check(failures, len(parts) == 2 and parts[1] == n.ascii_to_os_name('42.mdj'), "%s: split_name" % label)
    check(failures, len(n.ascii_to_os_name('abc')) == 3, "%s: names are plain bytes or text" % label)


def utf16_supported():
    """str.decode/bytes.decode exist from Python 2.2; the UTF-16 strategy needs 2.3+ anyway."""
    try:
        ppy.a2b('x').decode('ascii')
    except AttributeError:
        return 0
    return 1


def test_strategies(failures):
    check(failures, isinstance(naming.make_clear_enc(), naming.BytesNaming), "native-bytes is a BytesNaming")
    check(failures, isinstance(naming.make_win_utf8_enc(), naming.BytesNaming), "win-utf8 is a BytesNaming")
    check(failures, isinstance(naming.make_win_clear_enc(), naming.BytesNaming), "win-codepage is a BytesNaming")
    check(failures, isinstance(naming.make_utf16le_enc(), naming.TextNaming), "win-utf16le is a TextNaming")
    check_strategy(failures, naming.make_clear_enc(), byte_samples(), bytes_type(), 0)
    check_strategy(failures, naming.make_win_utf8_enc(), byte_samples(), bytes_type(), 0)
    check_strategy(failures, naming.make_win_clear_enc(), byte_samples(), bytes_type(), 1)
    if utf16_supported():
        check_strategy(failures, naming.make_utf16le_enc(), text_samples(), text_type(), 0)


def test_chosen_matches_listdir(failures):
    """The chosen strategy's name type is the type os.listdir() really returns here, and paths work end to end."""
    n = naming.choose_naming()
    check(failures, n.kind in (naming.PPY_NATIVE_BYTES, naming.PPY_WIN_UTF8, naming.PPY_WIN_UTF16LE, naming.PPY_WIN_CODEPAGE), "chosen kind %r" % n.kind)
    root_path_list = n.argv_to_os_path(os.path.dirname(os.path.abspath(sys.argv[0])))
    check(failures, len(root_path_list) == 1, "%s: argv_to_os_path gives a one-element path" % n.kind)
    entries = n.listdir(root_path_list)
    if len(entries) > 0:
        check(failures, type(entries[0]) == type(n.ascii_to_os_name('x')), "%s: listdir type %s vs ascii_to_os_name type %s" % (n.kind, type(entries[0]), type(n.ascii_to_os_name('x'))))
        first_path_list = n.child(root_path_list, entries[0])
        check(failures, len(first_path_list) == 2 and len(root_path_list) == 1, "%s: child makes a new path, root unchanged" % n.kind)
        check(failures, os.path.exists(n.os_join_path(first_path_list)), "%s: child + os_join_path + exists" % n.kind)
        check(failures, os.path.basename(n.os_join_path(first_path_list)) == entries[0], "%s: os_join_path joins the names" % n.kind)
        check(failures, ppy.get_lstat()(n.os_join_path(first_path_list)) is not None and os.stat(n.os_join_path(root_path_list)) is not None, "%s: lstat/stat through os_join_path" % n.kind)


def main():
    failures = []
    test_strategies(failures)
    test_chosen_matches_listdir(failures)
    if failures:
        for f in failures:
            sys.stdout.write("FAIL: %s\n" % f)
        sys.exit(1)
    sys.stdout.write("ok\n")


if __name__ == "__main__":
    main()
