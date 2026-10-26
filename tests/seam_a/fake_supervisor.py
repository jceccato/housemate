"""A stand-in for the Supervisor, for the tests that need more than options.

Runs inside the add-on image (it has python3), as the host named `supervisor`:

* GET  /addons/self/options/config   the add-on's options (what the base image reads)
* GET  /addons/self/info             slug and hostname, as the Supervisor reports them
* POST /core/api/services/<d>/<s>    Home Assistant service calls; recorded
* WS   /core/websocket               Home Assistant's websocket, enough for `config/auth/list`
* GET  /core/api/states            entity states, from states.json (default: none)
* GET  /core/api/config            Core as running, in UTC
* WS   config/entity_registry/list  from registry.json (default: none); repairs/list_issues: none
* WS   get_states, the device and area registries, get_services  from house.json (onboarding's scan)
* GET  /_calls                       the recorded service calls, as a JSON list
* GET  /_model_requests              what the language model was asked: path, model, Authorization header
* POST /v1/chat/completions (port 8081)  a language model: answers "Done.", or, when asked to
                                     "ask me", calls OpenCode's question tool first

State comes from the directory in $FAKE_DIR: `options.json`, `users.json`.
It records and answers; it checks nothing, so the tests read the record.
"""

import base64
import hashlib
import json
import os
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DIR = os.environ.get("FAKE_DIR", "/fake")
SLUG = "local_housemate_edge"
CALLS = []
MODEL_REQUESTS = []
LOCK = threading.Lock()
# What onboarding's scan asks Core for: websocket command -> key in house.json.
HOUSE_COMMANDS = {
    "get_states": "states",
    "config/device_registry/list": "devices",
    "config/area_registry/list": "areas",
    "get_services": "services",
}


def load(name, default=None):
    try:
        with open(os.path.join(DIR, name)) as f:
            return json.load(f)
    except FileNotFoundError:
        if default is None:
            raise
        return default


def ws_read(rfile):
    head = rfile.read(2)
    if len(head) < 2:
        return None
    opcode = head[0] & 0x0F
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", rfile.read(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", rfile.read(8))[0]
    mask = rfile.read(4) if head[1] & 0x80 else b"\0\0\0\0"
    data = bytes(b ^ mask[i % 4] for i, b in enumerate(rfile.read(length)))
    return opcode, data


def ws_send(wfile, obj):
    data = json.dumps(obj).encode()
    n = len(data)
    head = b"\x81" + (bytes([n]) if n < 126 else b"\x7e" + struct.pack(">H", n))
    wfile.write(head + data)
    wfile.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/addons/self/options/config":
            self.send_json({"result": "ok", "data": load("options.json")})
        elif self.path == "/addons/self/info":
            self.send_json({"result": "ok", "data": {"slug": SLUG, "hostname": SLUG.replace("_", "-")}})
        elif self.path == "/core/api/states":
            self.send_json(load("states.json", []))
        elif self.path == "/core/api/config":
            self.send_json({"state": "RUNNING", "version": "2026.10.4", "time_zone": "UTC"})
        elif self.path == "/core/api/":
            self.send_json({"message": "API running."})
        elif self.path == "/_model_requests":
            with LOCK:
                self.send_json(MODEL_REQUESTS)
        elif self.path == "/_calls":
            with LOCK:
                self.send_json(CALLS)
        elif self.path == "/core/websocket":
            self.websocket()
        else:
            self.send_json({"result": "error", "message": "not found"}, 404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/core/api/services/"):
            with LOCK:
                CALLS.append({
                    "service": self.path[len("/core/api/services/"):],
                    "data": json.loads(body or b"{}"),
                    "authorized": self.headers.get("Authorization", "").startswith("Bearer "),
                })
            self.send_json([])
        elif self.path == "/addons/self/options":
            with LOCK:
                CALLS.append({"service": "addons/self/options", "data": json.loads(body or b"{}"),
                              "authorized": self.headers.get("Authorization", "").startswith("Bearer ")})
            self.send_json({"result": "ok", "data": {}})
        elif self.path == "/core/restart":
            with LOCK:
                CALLS.append({"service": "core/restart", "data": {}})
            self.send_json({"result": "ok"})
        elif self.path == "/core/api/config/core/check_config":
            self.send_json({"result": "valid", "errors": None})
        else:
            self.send_json({"result": "error", "message": "not found"}, 404)

    def websocket(self):
        key = self.headers["Sec-WebSocket-Key"]
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        ws_send(self.wfile, {"type": "auth_required"})
        while True:
            frame = ws_read(self.rfile)
            if frame is None or frame[0] == 8:
                return
            if frame[0] != 1:
                continue
            msg = json.loads(frame[1])
            if msg["type"] == "auth":
                ws_send(self.wfile, {"type": "auth_ok"})
            elif msg["type"] == "config/auth/list":
                ws_send(self.wfile, {"id": msg["id"], "type": "result", "success": True, "result": load("users.json")})
            elif msg["type"] == "config/entity_registry/list":
                ws_send(self.wfile, {"id": msg["id"], "type": "result", "success": True, "result": load("registry.json", [])})
            elif msg["type"] == "repairs/list_issues":
                ws_send(self.wfile, {"id": msg["id"], "type": "result", "success": True, "result": {"issues": []}})
            elif msg["type"] in HOUSE_COMMANDS and os.path.exists(os.path.join(DIR, "house.json")):
                ws_send(self.wfile, {"id": msg["id"], "type": "result", "success": True,
                                     "result": load("house.json")[HOUSE_COMMANDS[msg["type"]]]})
            else:
                ws_send(self.wfile, {"id": msg["id"], "type": "result", "success": False,
                                     "error": {"code": "unknown_command", "message": "no"}})


class Model(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with LOCK:
            MODEL_REQUESTS.append({"path": self.path, "model": request.get("model"),
                                   "authorization": self.headers.get("Authorization")})
        messages = request.get("messages", [])
        asked = any(m.get("role") == "user" and "ask me" in json.dumps(m.get("content")) for m in messages)
        answered = any(m.get("role") == "tool" for m in messages)
        if asked and not answered:
            delta = {"tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {
                "name": "question",
                "arguments": json.dumps({"questions": [{
                    "question": "Which room is the night light for?", "header": "Room",
                    "options": [{"label": "Hall", "description": "the hall"}, {"label": "Study", "description": "the study"}],
                }]})}}]}
            finish = "tool_calls"
        else:
            delta, finish = {"content": "Done."}, "stop"

        def chunk(d, f=None, **extra):
            return "data: " + json.dumps({"id": "c1", "object": "chat.completion.chunk", "created": 0,
                                          "model": request.get("model", "m"),
                                          "choices": [{"index": 0, "delta": d, "finish_reason": f}], **extra}) + "\n\n"

        body = (chunk({"role": "assistant", **delta}) + chunk({}, finish,
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}) + "data: [DONE]\n\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", 8081), Model).serve_forever, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
