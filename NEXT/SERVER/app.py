"""pybak server: Python 3 only, FastAPI.

Speaks the client's protocol: bencoded bodies both ways, plain HTTP (the client
sends HTTP/1.0 with 'Connection: close' and reads to EOF, so every response
carries Content-Length). The message formats are defined once, in ../SHARED
(manifest.py, wanted_sync.py), and the server reads them with the same code the
client's tests use.

  POST /sync    body: a manifest (SHARED/manifest.py)
                reply: a WantedSync (SHARED/wanted_sync.py): the files the
                server wants, each with the offset to resume from.

  PYTHONPATH=$PORTAPY/src:../SHARED fastapi dev main.py

Annotations are postponed (the __future__ import): the Ppy and Pk tags such as
benc.PpyBValue and pk.PkHexPath exist only for mypy, so an annotation evaluated
when its 'def' runs would fail. Postponed, they are strings only mypy reads.
"""

from __future__ import annotations

import fastapi as fa
import os
import json
import portapy_sdk as ppy
import pk_types as pk
import manifest_unmarshalled as mfu
import wanted_sync as ws
import server_util as su
import util
import bencode as benc

BENCODE = 'application/x-pybak-bencode'  # our hacked bencoding.

# ----------------------------------------
# config

config = './config.json'
if not os.path.exists(config):
    raise Exception('./config.json required')

with open(config, 'r') as f:
    json = json.load(f)

canonical = json['canonical']
print('canonical', canonical, type(canonical))
if not os.path.exists(canonical):
    raise Exception("./config.json: invalid 'canonical' path '%s'" % canonical)

browse = json['browse']
if not os.path.exists(browse):
    raise Exception("./config.json: invalid 'browse' path '%s'" % browse)

# ----------------------------------------

app = fa.FastAPI()

# ----------------------------------------


def bencode_response(value: benc.PpyBValue, status_code: int) -> fa.Response:
    return fa.Response(content=benc.bencode(value), status_code=status_code, media_type=BENCODE)


def error_response(message: str, status_code: int) -> fa.Response:
    body: benc.PpyBDict = {}
    benc.bd_add(body, 'error', message.encode('ascii', 'replace'))
    return bencode_response(body, status_code)


def update_metadata(croot, system_metadata, lstat, stat):
    metadata_filename = util.metadata_filename_for(croot)


def calculate_offset(croot, length):
    print('offset_wanted', croot)
    if not os.path.exists(croot):
        return 0
    sofar = os.path.getsize(croot)
    print('offest_wanted: sofar', sofar, croot)
    if sofar < length:
        return sofar
    if sofar > length:
        ppy.prntlog(ppy.PPY_ERROR,
                    'ERROR: our local file is bigger than the client\'s.')
        return -1
    # we assume the md5 was already checked upon first completion.
    return None


def offset_wanted(system_metadata, md5, length, lstat, stat):
    cpath = su.canonical_path_for(md5, length)
    update_metadata(cpath, system_metadata, lstat, stat)
    offset_wanted = calculate_offset(cpath, length)
    print('offset_wanted', offset_wanted, md5)
    return offset_wanted


def wanted_for(manifest: mfu.ManifestUnmarshalled) -> ws.WantedSync:
    """Which of the manifest's files the server wants, and from which offset.
    todo:
    - look each md5_length up in the store: skip content that is complete,
    resume staged content from its size.
    - check and update archive metadata.
    - save manifest metadata for brose use.
    """
    wanted = ws.WantedSync()
    for entry in manifest.entries:
        md5 = entry['md5']
        length = entry['length']
        lstat = entry['lstat']
        stat = entry['stat']  # could be None.
        print("wanted_for", md5, length)
        offset = offset_wanted(
            manifest.system_metadata,
            md5,
            length,
            lstat,
            stat
        )
        if (offset is not None):
            # todo: update metadata on the files using decoded path.
            wanted.add_file(md5, length, pk.PkOffset(offset))
    return wanted


def save_chunk(headers, chunk):
    # 1) find the file based on the {md5}_{length}
    # 2) append the given chunk bytes.
    # 3) if the len(file) == length
    # 3.1) assert md5.
    # 3.2) update metadata.
    print('save_chunk', 'TODO', headers)


@app.post("/query")
async def post_sync(request: fa.Request) -> fa.Response:
    body = await request.body()
    try:
        manifest = mfu.ManifestUnmarshalled(body)
        wanted = wanted_for(manifest)
    except (ValueError, TypeError, KeyError) as e:
        import traceback
        print(str(e))
        traceback.print_tb(e.__traceback__)
        return error_response('error', 400)
    return fa.Response(content=wanted.marshall(), media_type=BENCODE)


@app.post("/sync")
async def post_sync(request: fa.Request) -> fa.Response:
    # todo: get metadata from xheaders???
    headers = await request.body()
    chunk = await request.body()
    print("chunk", len(chunk))
    ok = save_chunk(headers, chunk)
    return fa.Response()
