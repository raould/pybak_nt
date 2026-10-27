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
ppy.PpyBValue and pk.PkHexPath exist only for mypy, so an annotation evaluated
when its 'def' runs would fail. Postponed, they are strings only mypy reads.
"""

from __future__ import annotations

import fastapi as fa

import portapy_sdk as ppy
import pk_types as pk
import manifest as mf
import wanted_sync as ws

BENCODE = 'application/x-bencode'

app = fa.FastAPI()


def bencode_response(value: ppy.PpyBValue, status_code: int) -> fa.Response:
    return fa.Response(content=ppy.bencode(value), status_code=status_code, media_type=BENCODE)


def error_response(message: str, status_code: int) -> fa.Response:
    body: ppy.PpyBDict = {}
    ppy.bd_add(body, 'error', message.encode('ascii', 'replace'))
    return bencode_response(body, status_code)


def wanted_for(manifest: mf.ManifestUnmarshalled) -> ws.WantedSync:
    """Which of the manifest's files the server wants, and from which offset.

    todo: look each md5_length up in the store: skip content that is complete,
    resume staged content from its size. For now every file is wanted from 0.
    Sightings (.mdj) are not recorded yet either.
    """
    wanted = ws.WantedSync()
    for entry in manifest.entries:
        hex_path_list: pk.PkHexPath = ws.hex_path_list_from_bd(entry)
        wanted.add_file(hex_path_list, pk.PkOffset(0))
    return wanted


@app.post("/sync")
async def post_sync(request: fa.Request) -> fa.Response:
    body = await request.body()
    try:
        manifest = mf.ManifestUnmarshalled(ppy.PpyBencoded(body))
        wanted = wanted_for(manifest)
    except (ValueError, TypeError, KeyError) as e:
        return error_response('bad manifest: %r' % (e,), 400)
    return fa.Response(content=wanted.marshall(), media_type=BENCODE)
