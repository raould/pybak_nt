"""Small Python 2.0-compatible SDK shims for portable python programs."""

import printlog
import naming

set_prntlog_level = printlog.set_prntlog_level
prntlog = printlog.prntlog
prnt = printlog.prnt
write = printlog.write
int_div = printlog.int_div
exception_value = printlog.exception_value

interpreter_name_codec = naming.interpreter_name_codec
has_win32_core = naming.has_win32_core
unicode_filenames_supported = naming.unicode_filenames_supported
is_utf8_name = naming.is_utf8_name
root_to_bytes = naming.root_to_bytes
root_to_text = naming.root_to_text
root_identity = naming.root_identity
contains_question_mark = naming.contains_question_mark
name_identity = naming.name_identity
name_to_utf16le = naming.name_to_utf16le
choose_naming = naming.choose_naming
is_lossy = naming.is_lossy
get_lstat = naming.get_lstat
make_bytes = naming.make_bytes
probe_text = naming.probe_text
make_temp_dir = naming.make_temp_dir
self_test_naming = naming.self_test_naming
