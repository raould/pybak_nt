import portapy_sdk as ppy

# ---------------------------------------------------------------------------
"""bencode customized for pybak_nt, portable from Python 2.0 to 3.x.
    keys and values must be ascii strings or integers.
    raw bytes are disallowed (send them via hexl-ascii).
"""

try:
    # type: ignore[comparison-overlap]  # Python 2: true
    PPY_NATIVE_STR_IS_BYTES = int(bytes is str)
except NameError:
    PPY_NATIVE_STR_IS_BYTES = 1

try:
    _LONG = long  # type: ignore[name-defined]
except NameError:
    _LONG = int

_PPY_INT_TYPE = type(1)
_PPY_LONG_TYPE = type(_LONG(0))
# type: typing.Type[typing.Dict[typing.Any, typing.Any]]
_PPY_DICT_TYPE = type({})
_PPY_LIST_TYPE = type([])  # type: typing.Type[typing.List[typing.Any]]
_PPY_TUPLE_TYPE = type(())
_PPY_NATIVE_STR_TYPE = type('')

if PPY_NATIVE_STR_IS_BYTES:
    # type: typing.Type[bytes]  # type: ignore[assignment]  # Python 2: bytes is str
    _PPY_BYTES_TYPE = _PPY_NATIVE_STR_TYPE
else:
    _PPY_BYTES_TYPE = type('x'.encode('ascii'))

try:
    _PPY_TEXT_TYPE = unicode  # type: ignore[name-defined]
except NameError:
    _PPY_TEXT_TYPE = str


# ---------------------------------------------------------------------------
# Type tags (TYPES.md).
#
# Source tags are aliases: they name values that start life as plain Python
# values (literals, sys.argv, os results). Derived tags are NewTypes: only a
# conversion makes one, or the checking constructor of the same name at a
# trust boundary (an HTTP body, decoded data). mypy reads the 'if MYPY:'
# block; Python only parses it (so it uses no annotation syntax) and runs the
# 'else:' block, where the source tags are the real per-version types and the
# derived tags are the checking functions just below.

def _check_ascii_bytes(b):
    # type: (bytes) -> bytes
    """Mark bytes as ASCII-only bytes. Raises TypeError/ValueError if they are not."""
    if type(b) != _PPY_BYTES_TYPE:
        raise TypeError('expected bytes, got %s (%s)' % (type(b), b))
    if ascii_or_none(b) is None:
        raise ValueError('not ASCII')
    return b


def _check_bencoded(b):
    # type: (bytes) -> bytes
    """Mark bytes as bencoded data before bdecode(). Checks the type only; bdecode() checks the structure."""
    if type(b) != _PPY_BYTES_TYPE:
        raise TypeError('expected bytes, got %s' % type(b))
    return b


MYPY = 0  # hide all this from non-mypy tools.
if MYPY:
    # portapy_pragma ALLOW_MODULE
    import typing

    # Source tags.
    # type of a plain '...' literal: bytes on Python 2, text on Python 3. mypy sees only Python 3.
    PpyNativeStr = str
    PpyAsciiStr = str       # a PpyNativeStr holding only ASCII: the input of a2b(), bkey()
    PpyBytes = bytes        # real bytes: str on Python 2, bytes on Python 3
    # Python's text type (unicode on Python 2): code points, no encoding, contents not validated
    PpyText = str

    # Derived tags.
    PpyAsciiBytes = typing.NewType(
        'PpyAsciiBytes', bytes)      # output of a2b()
    # output of bkey(): a bencode dict key
    PpyBKey = typing.NewType('PpyBKey', PpyAsciiBytes)
    # output of bencode(), the only input to bdecode()
    PpyBencoded = typing.NewType('PpyBencoded', bytes)

    # Bencode values. Sequence/Mapping are read-only, so covariant: a list of
    # any bytes tag can be encoded without copying. Decoded values are concrete
    # lists/dicts: read them with bv_list/bv_dict and the bd_get_* readers.
    PpyBValue = typing.Union[bytes, int, typing.Sequence['PpyBValue'],
                             typing.Mapping[bytes, 'PpyBValue']]
    PpyBList = typing.List[PpyBValue]
    PpyBDict = typing.Dict[bytes, PpyBValue]

    # Generic helpers for type comments, so portable code needs no typing
    # import. Union cannot be aliased for any number of arguments: fixed arities.
    _GT = typing.TypeVar('_GT')
    _GK = typing.TypeVar('_GK')
    _GV = typing.TypeVar('_GV')
    _GR = typing.TypeVar('_GR')
    _GTs = typing.TypeVarTuple('_GTs')
    _GP = typing.ParamSpec('_GP')
    PpyList = typing.List[_GT]
    PpyDict = typing.Dict[_GK, _GV]
    PpyTuple = typing.Tuple[typing.Unpack[_GTs]]
    PpyOptional = typing.Optional[_GT]
    PpyUnion2 = typing.Union[_GT, _GK]
    PpyUnion3 = typing.Union[_GT, _GK, _GV]
    PpyCallable = typing.Callable[_GP, _GR]
    PpyAny = typing.Any
else:
    PpyNativeStr = _PPY_NATIVE_STR_TYPE
    PpyAsciiStr = _PPY_NATIVE_STR_TYPE
    PpyBytes = _PPY_BYTES_TYPE
    PpyText = _PPY_TEXT_TYPE
    PpyAsciiBytes = _check_ascii_bytes
    PpyBKey = _check_ascii_bytes
    PpyBencoded = _check_bencoded


# ---------------------------------------------------------------------------
# The two str <-> bytes helpers. ASCII only, strict, exact inverses.


def require_ascii_bytes(b):
    if PPY_NATIVE_STR_IS_BYTES:
        for c in b:
            # type: ignore[arg-type]  # Python 2: c is a 1-char str
            if ord(c) > 127:
                return 0
        return 1
    try:
        return 1
    except UnicodeError:
        return 0


def ascii_or_none(b):
    # type: (PpyBytes) -> PpyOptional[PpyAsciiStr]
    """Bytes -> native str if pure ASCII, else None."""
    if PPY_NATIVE_STR_IS_BYTES:
        for c in b:
            # type: ignore[arg-type]  # Python 2: c is a 1-char str
            if ord(c) > 127:
                return None
        return b  # type: ignore[return-value]  # Python 2: bytes is str
    try:
        return b.decode('ascii')
    except UnicodeError:
        return None


def byte_from_int(n):
    # type: (int) -> PpyBytes
    """0..255 -> a one-byte bytes value, on every version."""
    if PPY_NATIVE_STR_IS_BYTES:
        return chr(n)  # type: ignore[return-value]  # Python 2: str is bytes
    return bytes((n,))


def is_ascii_str(s):
    # type: (PpyNativeStr) -> None
    if type(s) != _PPY_NATIVE_STR_TYPE:
        raise TypeError('expected native str, got %s' % type(s))
    for c in s:
        if ord(c) > 127:
            return 0
    return 1


def require_ascii_str(s):
    # type: (PpyNativeStr) -> None
    if not is_ascii_str(s):
        raise ValueError('not ASCII: %r' % s)


def a2b(s):
    # type: (PpyAsciiStr) -> PpyAsciiBytes
    """Native str literal -> bytes. Python 2: no-op. Python 3: encode ASCII."""
    require_ascii_str(s)
    if PPY_NATIVE_STR_IS_BYTES:
        return s  # type: ignore[return-value]  # Python 2: str is bytes
    return PpyAsciiBytes(s.encode('ascii'))


def b2a(b):
    # type: (PpyBytes) -> PpyAsciiStr
    """Bytes -> native str. Python 2: no-op. Python 3: decode ASCII.

    Raises ValueError if b is not ASCII, on every version.
    """
    if PPY_NATIVE_STR_IS_BYTES:
        # type: ignore[arg-type]  # Python 2: bytes is str
        require_ascii_str(b)
        return b  # type: ignore[return-value]
    if type(b) != _PPY_BYTES_TYPE:
        raise TypeError('expected bytes, got %s' % type(b))
    try:
        return b.decode('ascii')
    except UnicodeError:
        raise ValueError('not ASCII')


_PPY_B_I = a2b('i')
_PPY_B_L = a2b('l')
_PPY_B_D = a2b('d')
_PPY_B_E = a2b('e')
_PPY_B_COLON = a2b(':')
_PPY_B_MINUS = a2b('-')
_PPY_B_ZERO = a2b('0')
_PPY_B_EMPTY = a2b('')
_PPY_DIGIT_BYTES = a2b('0123456789')


def _is_integer(v):
    # type: (object) -> int
    t = type(v)
    if t == _PPY_INT_TYPE or t == _PPY_LONG_TYPE:
        return 1
    if isinstance(v, _PPY_INT_TYPE):   # Python 3 bool
        return 1
    return 0


# ---------------------------------------------------------------------------
# Checked readers for decoded bencode values (untrusted data from the wire).
# Each returns its argument unchanged if it has the expected shape, else
# raises TypeError, so callers never index into a value of the wrong kind.


def bv_bytes(v):
    # type: (PpyBValue) -> PpyBytes
    if type(v) != _PPY_BYTES_TYPE:
        raise TypeError('bencode value: expected bytes, got %s' % type(v))
    return v


def bv_int(v):
    # type: (PpyBValue) -> int
    if not _is_integer(v):
        raise TypeError('bencode value: expected integer, got %s' % type(v))
    # type: ignore[return-value]  # _is_integer() checked it (int or long); mypy cannot narrow through it
    return v


def bv_list(v):
    # type: (PpyBValue) -> PpyBList
    if type(v) != _PPY_LIST_TYPE:
        raise TypeError('bencode value: expected list, got %s' % type(v))
    return v


def bv_dict(v):
    # type: (PpyBValue) -> PpyBDict
    if type(v) != _PPY_DICT_TYPE:
        raise TypeError('bencode value: expected dict, got %s' % type(v))
    return v


def bd_get_bytes(d, k):
    # type: (PpyBDict, PpyAsciiStr) -> PpyBytes
    return bv_bytes(bd_get(d, k))


def bd_get_int(d, k):
    # type: (PpyBDict, PpyAsciiStr) -> int
    return bv_int(bd_get(d, k))


def bd_get_list(d, k):
    # type: (PpyBDict, PpyAsciiStr) -> PpyBList
    return bv_list(bd_get(d, k))


def bd_get_dict(d, k):
    # type: (PpyBDict, PpyAsciiStr) -> PpyBDict
    return bv_dict(bd_get(d, k))


def bencode(value):
    parts = []
    _encode_into(value, parts)
    try:
        return PpyBencoded(_PPY_B_EMPTY.join(parts))
    except TypeError:
        ppy.prntlog(ppy.PPY_ERROR, 'bencode ERROR %s' % str(parts))
        raise


def _encode_into(value, parts):
    # type: (PpyAny, PpyList[bytes]) -> None
    t = type(value)
    # all bytes are to be ascii.
    # in other words we only allow strings, no bytes.
    # Python 2 case of str-is-bytes is firat,
    # before the Python 3 case of 'native string'.
    if t == _PPY_BYTES_TYPE:  # bytes, and Python 2 str.
        if not require_ascii_bytes(value):
            ppy.prntlog(ppy.PPY_ERROR, '_encode_into ERROR: %s' % value)
            raise TypeError('only ascii bytes allowed.')
        # they are ascii bytes (hopefully not just by accident).
        parts.append(a2b('%d:' % len(value)))
        parts.append(value)
    elif t == _PPY_NATIVE_STR_TYPE:  # Python 3 str.
        _encode_into(a2b(value), parts)
    elif _is_integer(value):
        parts.append(a2b('i%de' % value))
    elif t == _PPY_LIST_TYPE:
        parts.append(_PPY_B_L)
        for item in value:
            _encode_into(item, parts)
        parts.append(_PPY_B_E)
    elif t == _PPY_TUPLE_TYPE:
        parts.append(_PPY_B_L)
        for item in value:
            _encode_into(item, parts)
        parts.append(_PPY_B_E)
    elif t == _PPY_DICT_TYPE:
        keys = list(value.keys())
        for k in keys:
            if type(k) != _PPY_BYTES_TYPE and type(k) != _PPY_NATIVE_STR_TYPE:
                raise TypeError(
                    'bencode dict keys must be bytes; use a2b(\'%s\')' % k)
        try:
            keys.sort()
        except TypeError:
            ppy.prntlog(ppy.PPY_ERROR, str(ppy.current_exception()))
            ppy.prntlog(ppy.PPY_ERROR, keys)
            raise
        parts.append(_PPY_B_D)
        for k in keys:
            v = value[k]
            if type(k) == _PPY_NATIVE_STR_TYPE:
                assert is_ascii_str(k)
                k = a2b(k)
            _encode_into(k, parts)
            _encode_into(v, parts)
        parts.append(_PPY_B_E)
    elif t == _PPY_NATIVE_STR_TYPE:
        if not is_ascii_str(value):
            # Only reachable on Python 3: text where bytes are required.
            raise TypeError('str value %r: bencode strings are bytes; '
                            'e.g. use a2b() to pre-convert ASCII constants' % value)
        # they are ascii bytes (hopefully not just by accident).
        parts.append(a2b('%d:' % len(value)))
        parts.append(value)
    else:
        raise TypeError('cannot bencode %s' % t)


# ---------------------------------------------------------------------------
# Decoding. Uses slices, never indexing: indexing bytes gives a 1-character
# str on Python 2 but an int on Python 3.

def bdecode(data):
    # type: (PpyBencoded) -> PpyBValue
    found = _decode_at(data, 0)
    value = found[0]  # type: PpyBValue
    if found[1] != len(data):
        raise ValueError('trailing data after bencoded value')
    return value


def _decode_at(data, pos):
    # type: (bytes, int) -> PpyTuple[PpyAny, int]
    c = data[pos:pos + 1]
    ppy.prntlog(ppy.PPY_VERBOSE, '_decode_at: %s %s' % (pos, c))
    if c == _PPY_B_EMPTY:
        raise ValueError('unexpected end of data')
    if c == _PPY_B_I:
        return _decode_int(data, pos + 1)
    if c == _PPY_B_L:
        items = []  # type: PpyBList
        pos = pos + 1
        while data[pos:pos + 1] != _PPY_B_E:
            item, pos = _decode_at(data, pos)
            items.append(item)
        return (items, pos + 1)
    if c == _PPY_B_D:
        result = {}  # type: PpyBDict
        pos = pos + 1
        previous = None  # type: PpyOptional[bytes]
        while data[pos:pos + 1] != _PPY_B_E:
            key, pos = _decode_at(data, pos)
            if type(key) == _PPY_BYTES_TYPE:
                raise TypeError('failed to decode key bytes')
            if type(key) != _PPY_NATIVE_STR_TYPE:
                raise ValueError('dict key did not decode to a native string')
            require_ascii_str(key)
            if previous is not None and not (previous < key):
                raise ValueError('bencode dict keys not sorted or repeated')
            previous = key
            value, pos = _decode_at(data, pos)
            result[key] = value
        return (result, pos + 1)
    if _PPY_DIGIT_BYTES.find(c) >= 0:
        decoded = _decode_bytes(data, pos)
        # we're only allowing ascii strings.
        return (b2a(decoded[0]), decoded[1])
    raise ValueError('bad bencode type at offset %d' % pos)


def _decode_int(data, pos):
    # type: (bytes, int) -> PpyTuple[int, int]
    end = data.find(_PPY_B_E, pos)
    if end < 0:
        raise ValueError('unterminated integer')
    digits = data[pos:end]
    body = digits
    if body[:1] == _PPY_B_MINUS:
        body = body[1:]
        if body == _PPY_B_ZERO:
            raise ValueError('negative zero in bencode integer')
    if body == _PPY_B_EMPTY:
        raise ValueError('empty bencode integer')
    if len(body) > 1 and body[:1] == _PPY_B_ZERO:
        raise ValueError('leading zero in bencode integer')
    _require_digits(body)
    return (_LONG(b2a(digits)), end + 1)


def _require_digits(b):
    # type: (bytes) -> None
    i = 0
    while i < len(b):
        if _PPY_DIGIT_BYTES.find(b[i:i + 1]) < 0:
            raise ValueError('non-digit in bencode number')
        i = i + 1


def _decode_bytes(data, pos):
    # type: (bytes, int) -> PpyTuple[bytes, int]
    colon = data.find(_PPY_B_COLON, pos)
    if colon < 0:
        raise ValueError('unterminated string length')
    length_digits = data[pos:colon]
    if length_digits == _PPY_B_EMPTY:
        raise ValueError('empty string length')
    _require_digits(length_digits)
    if len(length_digits) > 1 and length_digits[:1] == _PPY_B_ZERO:
        raise ValueError('leading zero in string length')
    length = _LONG(b2a(length_digits))
    start = colon + 1
    end = start + length
    if end > len(data):
        raise ValueError('len(data) doesn\'t match expected length')
    result = (data[start:end], end)
    ppy.prntlog(ppy.PPY_VERBOSE, '_decode_bytes: %s %s' %
                (data[pos:end], result))
    return result
