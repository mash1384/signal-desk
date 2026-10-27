"""Own, verified local HTTP server with deterministic startup and teardown."""
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import urllib.request
from urllib.parse import urlsplit
import os

# 사이트 경로(기본 /signal-desk/ — 자체 도메인이면 배포 설정 SIGNAL_SITE_BASE=/ 와 같게)
PREFIX = os.environ.get("SIGNAL_SITE_BASE") or "/signal-desk/"


class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_args):
        pass

    def translate_path(self, path):
        path = urlsplit(path).path
        if not path.startswith(PREFIX):
            return str(Path(self.directory) / "__invalid_site_prefix__")
        return super().translate_path("/" + path[len(PREFIX):])


class Server(ThreadingHTTPServer):
    # Module preloads can arrive together. The default backlog of five
    # intermittently reset valid requests; keep every failure assertion.
    request_queue_size = 128
    daemon_threads = True


@contextmanager
def serve(site):
    site = Path(site).resolve()
    if not (site / "index.html").is_file():
        raise FileNotFoundError("build index.html missing: " + str(site))
    handler = partial(Handler, directory=str(site))
    server = Server(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d%s" % (server.server_port, PREFIX)
    try:
        with urllib.request.urlopen(base, timeout=5) as response:
            if response.status != 200 or b"<html" not in response.read().lower():
                raise RuntimeError("local site did not answer health probe")
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("local server failed to stop")
