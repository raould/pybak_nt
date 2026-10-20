"""Small Python 2.0-compatible SDK shims for portable python programs."""

import sys

try:
    basestring
except NameError:
    basestring = str


VERBOSE = 10
DEBUG = 20
WARN = 30
ERROR = 40
PRNTLOG_LEVEL = None
_DEFAULT_PRNTLOG_LEVEL = WARN


def _level_from_name(value):
    if value is None:
        return None
    value = value.upper()
    if value == "VERBOSE":
        return VERBOSE
    if value == "DEBUG":
        return DEBUG
    if value == "WARN":
        return WARN
    if value == "ERROR":
        return ERROR
    return None


def set_prntlog_level(level):
    """Set or clear the programmatic PRNTLOG threshold."""
    global PRNTLOG_LEVEL
    if level is None:
        PRNTLOG_LEVEL = None
        return
    if isinstance(level, basestring):
        level = _level_from_name(level)
    if level not in (VERBOSE, DEBUG, WARN, ERROR):
        raise ValueError("invalid PRNTLOG level")
    PRNTLOG_LEVEL = level


def _effective_prntlog_level():
    environment_level = _level_from_name(
        __import__("os").environ.get("PRNTLOGLEVEL")
    )
    if PRNTLOG_LEVEL is None:
        if environment_level is None:
            return _DEFAULT_PRNTLOG_LEVEL
        return environment_level
    if environment_level is None:
        return PRNTLOG_LEVEL
    if PRNTLOG_LEVEL < environment_level:
        return PRNTLOG_LEVEL
    return environment_level


def prntlog(level, message):
    """Write a gated diagnostic to stderr."""
    if isinstance(level, basestring):
        level = _level_from_name(level)
    if level is None or level < _effective_prntlog_level():
        return
    if level == VERBOSE:
        label = "VERBOSE"
    elif level == DEBUG:
        label = "DEBUG"
    elif level == WARN:
        label = "WARN"
    else:
        label = "ERROR"
    sys.stderr.write("[portapy:%s] %s\n" % (label, message))
    sys.stderr.flush()


def prnt(*values):
    """Write values separated by spaces and terminated by a newline."""
    index = 0
    while index < len(values):
        if index != 0:
            sys.stdout.write(" ")
        sys.stdout.write("%s" % values[index])
        index = index + 1
    sys.stdout.write("\n")


def write(value):
    """Write one value without adding a newline."""
    sys.stdout.write("%s" % value)


def int_div(left, right):
    """Return Python-style floor division without using `//` syntax."""
    return divmod(left, right)[0]


def exception_value():
    """Return the active exception value inside an except block."""
    return sys.exc_info()[1]
