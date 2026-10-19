"""Serve offline fixture responses over real local TLS sockets.

route.fulfill bypasses CDP download throttling. Rewriting to a local HTTPS
endpoint retains the same fixtures while letting Chrome throttle every byte.
The disposable self-signed certificate is only trusted by this test context.
"""
from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer
import gzip
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from tests.e2e.network import Offline
from tests.e2e.server import Handler


class WireReply:
    def __init__(self, url):
        self.request = SimpleNamespace(url=url, method='GET')
        self.payload = None

    def fulfill(self, **payload):
        self.payload = payload

    def continue_(self):
        raise ValueError('fixture proxy cannot recursively proxy itself')


class WireHandler(Handler):
    protocol_version = 'HTTP/1.1'
    def send_body(self, body, mime, status=200, headers=None):
        compressed = self.server.compression == 'gzip' and 'gzip' in self.headers.get('Accept-Encoding', '') and (
            mime.startswith('text/') or any(x in mime for x in ('json', 'javascript', 'svg')))
        if compressed:
            body = gzip.compress(body, compresslevel=6, mtime=0)
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if compressed:
            self.send_header('Content-Encoding', 'gzip')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browser cancellation (e.g. reduced-motion removes video).

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path != '/_fixture':
            path = Path(self.translate_path(self.path))
            if path.is_dir():
                path = path / 'index.html'
            if not path.is_file():
                return self.send_error(404)
            return self.send_body(path.read_bytes(), self.guess_type(str(path)))
        original = parse_qs(url.query)['url'][0]
        reply = WireReply(original)
        self.server.offline.handle(reply)
        values = reply.payload
        if values is None:
            raise ValueError('missing offline response')
        body = json.dumps(values['json']).encode() if 'json' in values else values.get('body', b'')
        if isinstance(body, str):
            body = body.encode()
        self.send_body(body, values.get('content_type', 'application/json'), values.get('status', 200), values.get('headers'))


class WireServer(ThreadingHTTPServer):
    # All independent CDN origins converge here. The default backlog of five
    # drops simultaneous font sockets under throttling, corrupting byte counts.
    request_queue_size = 128
    daemon_threads = True


@contextmanager
def serve_wire(site, flash, compression='gzip'):
    site = Path(site).resolve()
    if not (site / 'index.html').is_file():
        raise FileNotFoundError(site / 'index.html')
    with tempfile.TemporaryDirectory(prefix='signal-perf-tls-') as tmp:
        cert, key = Path(tmp) / 'cert.pem', Path(tmp) / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        server = WireServer(('127.0.0.1', 0), partial(WireHandler, directory=str(site)))
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        base = 'https://127.0.0.1:%d/signal-desk/' % server.server_port
        server.offline = Offline(site, flash, base)
        server.compression = compression
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield base
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError('performance fixture server did not stop')
