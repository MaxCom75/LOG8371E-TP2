"""HTTP hop: delay once per incoming request before forwarding to Keycloak.

This changes the generator -> proxy -> authentication-service path, NOT PostgreSQL
network latency. Compare both arms through this hop. Control is separate from traffic.
POST /delay on port 9090 with {"milliseconds":300,"seconds":20}; automatic expiry.
POST {"milliseconds":0} to stop. Lab-only; compose binds host ports to loopback.
"""
import http.client
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

state = {'milliseconds': 0, 'until': 0}
lock = threading.Lock()
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
       'te', 'trailer', 'transfer-encoding', 'upgrade', 'host', 'content-length'}


def delay_seconds():
    with lock:
        return state['milliseconds'] / 1000 if time.monotonic() < state['until'] else 0


class Control(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/delay':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length < 1024:
                raise ValueError('body length')
            payload = json.loads(self.rfile.read(length))
            ms, seconds = float(payload['milliseconds']), float(payload.get('seconds', 20))
            if not 0 <= ms <= 1000 or not 0 < seconds <= 60:
                raise ValueError('bounds')
        except (ValueError, KeyError, TypeError):
            self.send_error(400, 'milliseconds 0..1000; seconds (0,60]')
            return
        with lock:
            state.update(milliseconds=ms, until=time.monotonic() + seconds)
        self.send_response(204)
        self.end_headers()


class Proxy(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def forward(self):
        if self.headers.get('Transfer-Encoding'):
            self.send_error(400, 'chunked requests unsupported in this lab')
            return
        if self.path != '/realms/perf/protocol/openid-connect/token':
            self.send_error(404)
            return
        upstream = urlsplit(os.environ.get('UPSTREAM', 'http://127.0.0.1:8080'))
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        time.sleep(delay_seconds())
        conn = http.client.HTTPConnection(upstream.hostname, upstream.port or 80, timeout=5)
        try:
            conn.request(self.command, self.path, body,
                         {k: v for k, v in self.headers.items() if k.lower() not in HOP})
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self.send_error(502, 'upstream unavailable')
        finally:
            conn.close()

    do_POST = forward

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    control = ThreadingHTTPServer(('0.0.0.0', 9090), Control)
    threading.Thread(target=control.serve_forever, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8081), Proxy).serve_forever()
