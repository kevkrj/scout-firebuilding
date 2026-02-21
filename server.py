#!/usr/bin/env python3
"""Scout Firebuilding Competition - Backend Server (no dependencies)"""
import json, os, time, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DIR, 'data.json')
HTML_FILE = os.path.join(DIR, 'index.html')
lock = threading.Lock()

def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"teams": [], "scores": {}, "timer": None, "completionTimes": {}}

def save(data):
    tmp = DATA_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/data':
            data = load()
            data['serverTime'] = time.time()
            self._json(data)
        elif path in ('/', '/index.html'):
            self._file(HTML_FILE, 'text/html; charset=utf-8')
        elif path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(n)) if n > 0 else {}
        except Exception:
            self.send_error(400); return

        path = urlparse(self.path).path
        with lock:
            data = load()
            ok = True

            if path == '/api/teams/add':
                name = body.get('name', '').strip()
                if name and name not in data['teams']:
                    data['teams'].append(name)

            elif path == '/api/teams/remove':
                name = body.get('name', '')
                if name in data['teams']:
                    data['teams'].remove(name)
                    data['scores'].pop(name, None)
                    data['completionTimes'].pop(name, None)

            elif path == '/api/scores':
                name = body.get('name', '')
                cat = str(body.get('category', ''))
                vals = body.get('values', [])
                if name not in data['scores']:
                    data['scores'][name] = {}
                data['scores'][name][cat] = vals

            elif path == '/api/timer/start':
                dur = int(body.get('duration', 600))
                data['timer'] = {
                    'startTime': time.time(),
                    'duration': dur,
                    'running': True
                }
                data['completionTimes'] = {}

            elif path == '/api/timer/stop':
                data['timer'] = None

            elif path == '/api/mark-time':
                name = body.get('name', '')
                t = data.get('timer')
                if t and t.get('running') and name in data['teams']:
                    elapsed = time.time() - t['startTime']
                    if elapsed <= t['duration'] and name not in data.get('completionTimes', {}):
                        data['completionTimes'][name] = round(elapsed, 1)

            elif path == '/api/unmark-time':
                name = body.get('name', '')
                data.get('completionTimes', {}).pop(name, None)

            elif path == '/api/reset-scores':
                data['scores'] = {}
                data['completionTimes'] = {}

            elif path == '/api/reset-all':
                data = {"teams": [], "scores": {}, "timer": None, "completionTimes": {}}

            else:
                ok = False
                self.send_error(404)

            if ok:
                save(data)
                self._json({"ok": True})

    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.send_header('Content-Length', len(b))
        self.end_headers()
        self.wfile.write(b)

    def _file(self, filepath, ct):
        try:
            with open(filepath, 'rb') as f:
                b = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', len(b))
            self.end_headers()
            self.wfile.write(b)
        except FileNotFoundError:
            self.send_error(404)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *a):
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f'Scout Firebuilding server running on http://0.0.0.0:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped')
