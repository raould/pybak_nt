#portapy_pragma ALLOW_MODULE
import binascii

#----------------------------------------
# support MD5 file hashing.
try:
    #portapy_pragma ALLOW_MODULE
    import hashlib
    # todo: would want usedforsecurity=False (Python 3.9+) on FIPS systems
    hasher_new = hashlib.md5
    #portapy_pragma ALLOW_MODULE_END hashlib
except ImportError:
    #portapy_pragma ALLOW_MODULE
    import md5
    hasher_new = md5.new
    #portapy_pragma ALLOW_MODULE_END md5
def md5_and_length(fp, chunk_size=8192):
    hasher = hasher_new()
    count = 0
    while 1:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        count = count + len(chunk)
    return (hasher.digest(), count)

# ---------------------------------------------------------------------------

def hexlify_list(l, name_to_bytes):
    h = []
    for e in l:
        b = name_to_bytes(e)
        h.append(binascii.hexlify(b))
    return h

def unhexlify_list(l, bytes_to_name):
    u = []
    for e in l:
        u = binascii.unhexlify(e)
        u.append(bytes_to_name(u))
    return u
