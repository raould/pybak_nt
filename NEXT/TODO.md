# TODO

## Extra Unresolved

- the os.listdir() bugs across all (python version) x (os) x (filesystem).

## Naming

- The client figures out its kind of strings, and what the type of file system names is.
- The client knows how to round-trop its own values through binary, for network send.
- Problem: the server doesn't know how to decode hexl file paths, doesn't know encoding or anything.
  - e.g. ext filesystems have arbitrary raw bytes as the names.
  - so client cannot just convert to utf8/utf16, the raw name bytes on disk might not be allowed.
- Server should store the raw bytes (ie including surrogates) and a "showable" version thereof.
  - how to decode for showing?
  - can try to use the user's encoding.
  - can try a waterfall of try/catch decodings.
  - punting on the "showable" version for now!

## Marhsalling

* We assume all dict keys are ascii, so when they go through bencoding they should be decoded to an ascii string (whatever 'string' is in the given python).

* Everything is hard-coded-bencoded end to end, "because Python 2.0", and because becoding doesn't automagically round-trip native Python types.

- we need to send
- MANIFEST:
  - all the file entries.
  - metadata.
- ENTRY:
  - hexlized file path ([hex])
  - md5 sum (hex)
  - length (int)
  - offset (int)
  - name of the host (text)
  - stat, lstat
  - lots of text & int metadata
