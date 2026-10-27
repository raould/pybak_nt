import portapy_sdk as ppy
#portapy_pragma ALLOW_MODULE
import socket
#portapy_pragma ALLOW_MODULE
import pk_types as pk

_PYB_CHUNK_SIZE=1024*1024

#----------------------------------------
# http over socket, "because Python 2.0".

"""Minimal HTTP/1.0 client over raw sockets, portable from Python 2.0 to 3.x.

One request per connection: the client sends 'Connection: close', the server
answers and closes, and the client reads until EOF. That is all HTTP/1.0 needs,
and it avoids keep-alive and chunked encoding entirely. Bodies are bytes; the
caller chooses the format (pybak uses bencode both ways).

  r = http_request('192.168.1.10', 8765, 'POST', '/digest', body_bytes, 'application/x-bencode', 60)
  r['status'], r['headers'][b'content-type'], r['body']

Header names in r['headers'] are lowercased bytes. A response is rejected if it
uses chunked transfer encoding, or if it is shorter than its Content-Length (the
connection was cut off).

Timeouts need socket.settimeout (Python 2.3+). On older versions timeout_seconds
is ignored and a dead server can block the client.
"""

_HTTP_CRLF = ppy.a2b('\r\n')
_HTTP_HEADER_END = ppy.a2b('\r\n\r\n')
_HTTP_SPACE = ppy.a2b(' ')
_HTTP_COLON = ppy.a2b(':')
_HTTP_EMPTY = ppy.a2b('')
_HTTP_CONTENT_LENGTH = ppy.a2b('content-length')
_HTTP_TRANSFER_ENCODING = ppy.a2b('transfer-encoding')
_HTTP_RECV_SIZE = 65536


class HttpError(Exception):
    pass


def send_all(sock, data):
    # type: (socket.socket, ppy.PpyBytes) -> None
    """sock.sendall where it exists, else a send() loop."""
    sendall = getattr(sock, 'sendall', None)
    if sendall is not None:
        sendall(data)
        return
    while len(data) > 0:
        sent = sock.send(data)
        data = data[sent:]


def recv_until_eof(sock):
    # type: (socket.socket) -> ppy.PpyBytes
    parts = []  # type: pk.PkList[ppy.PpyBytes]
    while 1:
        data = sock.recv(_HTTP_RECV_SIZE)
        if not data:
            break
        parts.append(data)
    return _HTTP_EMPTY.join(parts)


def build_request(host, port, method, path, body, content_type):
    # type: (ppy.PpyAsciiStr, int, ppy.PpyAsciiStr, ppy.PpyAsciiStr, ppy.PpyBytes, ppy.PpyAsciiStr) -> ppy.PpyBytes
    """Request head + body as bytes. host, method, path, content_type: ASCII native str."""
    parts = []  # type: pk.PkList[ppy.PpyAsciiStr]
    parts.append('%s %s HTTP/1.0\r\n' % (method, path))
    parts.append('Host: %s:%d\r\n' % (host, port))
    parts.append('Content-Type: %s\r\n' % content_type)
    parts.append('Content-Length: %d\r\n' % len(body))
    parts.append('Connection: close\r\n\r\n')
    head = ''.join(parts)
    return ppy.a2b(head) + body


def parse_response(data):
    # type: (ppy.PpyBytes) -> pk.PkHttpResponse
    """Raw response bytes -> {'status': int, 'headers': {lowercased bytes: bytes}, 'body': bytes}."""
    end = data.find(_HTTP_HEADER_END)
    if end < 0:
        raise HttpError("no end of headers in response (%d bytes)" % len(data))
    lines = data[:end].split(_HTTP_CRLF)
    status_parts = lines[0].split(_HTTP_SPACE)
    if len(status_parts) < 2:
        raise HttpError("bad status line")
    status = int(ppy.b2a(status_parts[1]))
    headers = {}  # type: pk.PkDict[ppy.PpyBytes, ppy.PpyBytes]
    for line in lines[1:]:
        colon = line.find(_HTTP_COLON)
        if colon < 0:
            continue
        headers[line[:colon].strip().lower()] = line[colon + 1:].strip()
    # headers.get(): 'in' on a dict needs 2.2+, and the old method is gone in 3.
    if headers.get(_HTTP_TRANSFER_ENCODING) is not None:
        raise HttpError("transfer encoding not supported")
    body = data[end + len(_HTTP_HEADER_END):]
    content_length = headers.get(_HTTP_CONTENT_LENGTH)
    if content_length is not None:
        length = int(ppy.b2a(content_length))
        if len(body) < length:
            raise HttpError("response cut off: %d of %d body bytes" % (len(body), length))
        body = body[:length]
    return {'status': status, 'headers': headers, 'body': body}


def http_request(host, port, method, path, body, content_type, timeout_seconds):
    # type: (ppy.PpyAsciiStr, int, ppy.PpyAsciiStr, ppy.PpyAsciiStr, ppy.PpyBytes, ppy.PpyAsciiStr, int) -> pk.PkHttpResponse
    """One HTTP/1.0 request on a fresh connection. Raises HttpError or socket.error."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        settimeout = getattr(sock, 'settimeout', None)      # 2.3+
        if settimeout is not None:
            settimeout(timeout_seconds)
        sock.connect((host, port))
        send_all(sock, build_request(host, port, method, path, body, content_type))
        data = recv_until_eof(sock)
    finally:
        sock.close()
    return parse_response(data)


def post_data(host, port, path, value, timeout_seconds):
    # type: (ppy.PpyAsciiStr, int, ppy.PpyAsciiStr, ppy.PpyBencoded, int) -> ppy.PpyBencoded
    """POST data, return the reply's body. Non-200 raises HttpError."""
    r = http_request(host, port, 'POST', path, value, 'application/x-bencode', timeout_seconds)
    if r['status'] != 200:
        raise HttpError("HTTP %d from %s: %r" % (r['status'], path, r['body'][:200]))
    return ppy.PpyBencoded(r['body'])

def post_data_bencoded(host, port, path, value, timeout_seconds):
    # type: (ppy.PpyAsciiStr, int, ppy.PpyAsciiStr, ppy.PpyBValue, int) -> ppy.PpyBValue
    """POST bencode(data), return the reply's bdecode(body). Non-200 raises HttpError."""
    bv = ppy.bencode(value)
    body = post_data(host, port, path, bv, timeout_seconds)
    return ppy.bdecode(body)
