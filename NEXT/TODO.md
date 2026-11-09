# TODO

## Extra Unresolved

- the use of mypy quickly fell out of sync, it is borken now.
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

Everything is super-hard-coded-bencoded end-to-end, "because Python
2.0", and because becoding doesn't automagically round-trip native
Python types.

The main problem is there's no simple way to round-trip strings. Because
Python 2.x doesn't distinguish str vs. byte types, whereas Python 3.x does.
That means entries in dicts transferred cannot be unmarshalled easily into
the right type: all the 'str's that were put into a dict by Python 2.x look
like binary values in Python 3.x. Even in Python 2.x when you have a str
type you don't actually know if it is binary or text (in some encoding).
The intent is totally lost.

For our use case end to end, that means we have to hard-codedly assume
that everything (keys, values) is an ascii string, except for: the
file path, things that are integers; md5 could go either way. (The
file content data chunks are not going through marshalling.)

This could be addressed by extending the becoding to support marking
string-bytes vs. raw-bytes. Or by having an external schema, so the
unmarshalling would know what to convert back into the local string
type, vs. what to leave alone as bytes.
