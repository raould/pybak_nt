import sys
import portapy_sdk as ppysdk
#portapy_pragma ALLOW_MODULE
import binascii
#portapy_pragma ALLOW_MODULE
import os

#
# specifically for the client,
# for (any OS) x (any Python version):

# ----------------------------------------
# (1) we have to obtain the names of paths + files, and know what their type is.

if len(sys.argv) == 1:
    raise Exception("required argument: directory to crawl")

name_kind, root_to_native, name_to_raw = ppysdk.choose_naming()
cur_dir = root_to_native(sys.argv[1])

if not os.path.isdir(cur_dir):
    raise Exception("required argument: must be a directory")

# ----------------------------------------
# (2) get the path names.

for entry in os.listdir(cur_dir):
    ppysdk.prnt(str(os.lstat(os.path.join(cur_dir, entry))))

# ----------------------------------------
# (3) we have to convert them to hexl-ascii-string to send to the server.

def hex_encode(data):
    return str(binascii.hexlify(data).decode('ascii'))

def hex_decode(hexstr):
    return binascii.unhexlify(hexstr)

def ascii_to_wire(asciistr):
    return asciistr.encode('ascii')
    pass

def wire_to_ascii(data):
    return str(data.encode('ascii'))
    pass

#----------------------------------------

def make_bytes(ints):
    try:
        b = bytes(ints)
        if len(b) != len(ints):
            raise TypeError("bad buggy Python bytes implementation!!!")
        return b
    except (NameError, TypeError):
        c = []
        for i in ints:
            c.append(chr(i))
        return ''.join(c)

def test_hex_roundtrip():
    blist = []
    for v in range(255):
        blist.append(v)
    b = make_bytes(blist)
    h = hex_encode(b)
    d = hex_decode(h)
    assert len(d) == len(b)
    assert len(d) * 2 == len(h)

def tests():
    test_hex_roundtrip()
    # todo: test_wire_roundtrip()
