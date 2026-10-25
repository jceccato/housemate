#!/usr/bin/env python3
"""Housemate's kick-off endpoint: start an OpenCode job from Home Assistant.

Home Assistant (a voice blueprint, an update review) POSTs a request here. This
creates an OpenCode session through OpenCode's own server, hands it the
request without waiting for the reply, and tells the household with a phone
notification and a persistent notification. It then watches OpenCode's events
and sends another when a job needs an answer or is done.

    POST /kickoff   {"text": "...", "user_id": "...", "notify": "notify.mobile_app_x"}
                    -> 202 {"session_id": ..., "waiting_for_admin": bool, "url": ...}
                    With "prepare": true the text is put in a new chat and left there,
                    nothing run and nothing announced (the daily update review prepares
                    its briefed session this way; the notification it sends is its own).
                    Later questions and the finish are still announced to `notify`.
    GET  /healthz   -> 200

A request from anyone who is not a Home Assistant administrator (or from nobody
Home Assistant can name) is put in the chat and left there: nothing runs until
an administrator continues it. Who may call this is a matter of the network
(see the add-on's DOCS); the endpoint takes no credential of its own.

Standard library only. Runs inside the add-on; the Supervisor token is in its
environment and goes to the Supervisor, nowhere else.
"""

import base64
import json
import os
import re
import socket
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OPENCODE = os.environ.get("HOUSEMATE_OPENCODE_URL", "http://127.0.0.1:4096")
SUPERVISOR = os.environ.get("HOUSEMATE_SUPERVISOR_URL", "http://supervisor")
CORE = SUPERVISOR + "/core"
LISTEN = ("0.0.0.0", int(os.environ.get("HOUSEMATE_KICKOFF_PORT", "8765")))
# Where the notification opens: the add-on's page in Home Assistant's frontend.
# `/app/<slug>` is the route in Home Assistant 2026.10, which opens Housemate
# whether or not it is shown in the sidebar (older releases used
# `/hassio/ingress/<slug>`; the bare `/hassio/ingress/...` path is a plain 404
# there). Until the phone chat has a page per session this is the panel; the
# session's id is in the notification either way.
APP_PREFIX = os.environ.get("HOUSEMATE_APP_PREFIX", "/app")
CHAT_PATH = os.environ.get("HOUSEMATE_CHAT_PATH", "")
# The endpoint takes no credential and believes the user_id in the body, so it
# answers only Home Assistant Core, which reaches add-ons from the Supervisor
# network's gateway, 172.30.32.1 (and this container's own loopback). Any other
# caller's connection is closed unanswered. HOUSEMATE_KICKOFF_ALLOW replaces the
# Core address, for the tests, which have no Supervisor; Home Assistant never sets it.
ALLOWED = {os.environ.get("HOUSEMATE_KICKOFF_ALLOW", "172.30.32.1"), "127.0.0.1"}
STATE_FILE = os.environ.get("HOUSEMATE_KICKOFF_STATE", "/data/kickoff/sessions.json")
MAX_TEXT = 2000
MAX_TRACKED = 200

JOB_BRIEF = (
    "This job was started by voice, so the person who asked may be away from a screen. "
    "Get on with it; where a decision is theirs to make, ask with the question tool "
    "rather than guessing, and say plainly what you changed when you finish."
)

_lock = threading.Lock()
_sessions = {}  # session id -> {"notify", "title", "waiting", "busy"}
_slug = None


def log(msg):
    print(f"[kickoff] {msg}", flush=True)


# -- small HTTP helpers --------------------------------------------------------------

def call(method, url, body=None, token=None, timeout=15):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


def supervisor_token():
    return os.environ.get("SUPERVISOR_TOKEN", "")


# -- Home Assistant, through the Supervisor -----------------------------------------------

def addon_slug():
    global _slug
    if _slug is None:
        try:
            _slug = call("GET", SUPERVISOR + "/addons/self/info", token=supervisor_token())["data"]["slug"]
        except Exception as e:  # noqa: BLE001 - the notification still goes out, to the panel's usual path
            log(f"could not read the add-on's slug ({e}); using the default")
            return "housemate_edge"
    return _slug


def panel_url():
    return f"{APP_PREFIX}/{addon_slug()}{CHAT_PATH}"


def service(domain, name, data):
    try:
        call("POST", f"{CORE}/api/services/{domain}/{name}", data, token=supervisor_token())
        return True
    except Exception as e:  # noqa: BLE001
        log(f"{domain}.{name} failed: {e}")
        return False


def websocket_call(message):
    """One command on Home Assistant's websocket (through the Supervisor); returns its result."""
    host, port = SUPERVISOR.split("//", 1)[1], 80
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    sock = socket.create_connection((host, port), timeout=10)
    try:
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((
            f"GET /core/websocket HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        reader = sock.makefile("rb")
        if b" 101 " not in reader.readline():
            raise OSError("websocket refused")
        while reader.readline() not in (b"\r\n", b""):
            pass

        def send(obj):
            payload = json.dumps(obj).encode()
            mask = os.urandom(4)
            head = bytes([0x81])
            n = len(payload)
            if n < 126:
                head += bytes([0x80 | n])
            elif n < 65536:
                head += bytes([0x80 | 126]) + struct.pack(">H", n)
            else:
                head += bytes([0x80 | 127]) + struct.pack(">Q", n)
            sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

        def receive():
            while True:
                head = reader.read(2)
                if len(head) < 2:
                    raise OSError("websocket closed")
                length = head[1] & 0x7F
                if length == 126:
                    length = struct.unpack(">H", reader.read(2))[0]
                elif length == 127:
                    length = struct.unpack(">Q", reader.read(8))[0]
                payload = reader.read(length)
                if head[0] & 0x0F == 1:
                    return json.loads(payload)

        receive()  # auth_required
        send({"type": "auth", "access_token": supervisor_token()})
        if receive().get("type") != "auth_ok":
            raise OSError("websocket authentication refused")
        send({"id": 1, **message})
        reply = receive()
        if not reply.get("success"):
            raise OSError(f"websocket command failed: {reply.get('error')}")
        return reply["result"]
    finally:
        sock.close()


def who_asked(user_id):
    """(is_administrator, name) for a Home Assistant user id. Unknown or failing: not an administrator."""
    if not user_id:
        return False, None
    try:
        users = websocket_call({"type": "config/auth/list"})
    except Exception as e:  # noqa: BLE001
        log(f"could not look up users ({e}); treating the request as a non-admin's")
        return False, None
    for user in users:
        if user.get("id") == user_id and user.get("is_active", True):
            return bool(user.get("is_owner") or "system-admin" in user.get("group_ids", [])), user.get("name")
    return False, None


# -- notifications -------------------------------------------------------------------------

def normalise_target(target):
    """`notify.mobile_app_x` or `mobile_app_x` -> `mobile_app_x`; anything odd -> None."""
    if not target:
        return None
    name = target.split(".", 1)[1] if target.startswith("notify.") else target
    return name if re.fullmatch(r"[a-z0-9_]+", name) else None


def notify(session_id, target, title, message):
    url = panel_url()
    if target:
        service("notify", target, {
            "title": title,
            "message": message,
            "data": {"url": url, "clickAction": url, "tag": f"housemate_{session_id}"},
        })
    service("persistent_notification", "create", {
        "title": title,
        "message": f"{message}\n\n[Open Housemate]({url}) (session `{session_id}`)",
        "notification_id": f"housemate_{session_id}",
    })


# -- OpenCode -----------------------------------------------------------------------------------

def wait_for_opencode(seconds=60):
    """OpenCode may still be starting when the first request comes."""
    deadline = time.time() + seconds
    while True:
        try:
            call("GET", OPENCODE + "/global/health", timeout=5)
            return
        except Exception:  # noqa: BLE001
            if time.time() > deadline:
                raise
            time.sleep(1)


def create_session(title):
    return call("POST", OPENCODE + "/session", {"title": title})["id"]


def send_request(sid, text, run, asker):
    if run:
        body = {"parts": [{"type": "text", "text": text}], "system": JOB_BRIEF}
    else:
        who = asker or "Someone"
        body = {
            "noReply": True,
            "parts": [{"type": "text", "text": (
                f"{who} asked for this by voice and is not a Home Assistant administrator, "
                f"so nothing has been run. An administrator can continue this chat to go ahead.\n\n{text}")}],
        }
    call("POST", f"{OPENCODE}/session/{sid}/prompt_async", body)


# -- the record of jobs we notify about -------------------------------------------------------------

def load_state():
    try:
        with open(STATE_FILE) as f:
            _sessions.update(json.load(f))
    except (OSError, ValueError):
        pass


def save_state():
    os.makedirs(os.path.dirname(STATE_FILE), mode=0o700, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    keep = dict(list(_sessions.items())[-MAX_TRACKED:])
    with open(tmp, "w") as f:
        json.dump(keep, f)
    os.replace(tmp, STATE_FILE)


def track(sid, **fields):
    with _lock:
        _sessions.setdefault(sid, {}).update(fields)
        save_state()


# -- watching OpenCode's events ------------------------------------------------------------------------

def handle_event(event):
    """React to one OpenCode event for a tracked session."""
    props = event.get("properties", {})
    sid = props.get("sessionID")
    with _lock:
        job = dict(_sessions.get(sid, {})) if sid else None
    if not job:
        return
    kind = event.get("type")
    title = job.get("title", "Housemate job")
    if kind == "session.status" and props.get("status", {}).get("type") == "busy":
        track(sid, busy=True)
    elif kind == "question.asked":
        questions = props.get("questions") or [{}]
        ask = questions[0].get("question") or "A question is waiting."
        notify(sid, job.get("notify"), "Housemate needs you", f"{title}: {ask}")
    elif kind in ("permission.asked", "permission.updated"):
        what = props.get("title") or props.get("permission") or "permission to carry on"
        notify(sid, job.get("notify"), "Housemate needs you", f"{title}: asking for {what}.")
    elif kind == "session.error":
        err = props.get("error") or {}
        what = (err.get("data") or {}).get("message") or err.get("name") or "an error"
        track(sid, busy=False)
        notify(sid, job.get("notify"), "Housemate hit a problem", f"{title}: {what.splitlines()[0][:200]}")
    elif kind == "session.idle" and job.get("busy") and not job.get("done"):
        track(sid, busy=False, done=True)  # told once; later turns in the chat are the admin's own
        notify(sid, job.get("notify"), "Housemate finished", f"{title}: the job is done, or waiting for you to reply.")


def watch_events():
    while True:
        try:
            with urllib.request.urlopen(OPENCODE + "/event", timeout=3600) as stream:
                for raw in stream:
                    line = raw.decode(errors="replace").strip()
                    if line.startswith("data:"):
                        try:
                            handle_event(json.loads(line[5:]))
                        except ValueError:
                            pass
        except Exception as e:  # noqa: BLE001 - OpenCode restarting is normal; try again
            log(f"event stream ended ({e}); reconnecting")
        time.sleep(2)


# -- the endpoint --------------------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "housemate-kickoff"

    def log_message(self, fmt, *args):
        log(f"{self.address_string()} {fmt % args}")

    def reply(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/healthz":
            self.reply(200, {"ok": True})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/kickoff":
            return self.reply(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(min(length, 65536)) or b"{}")
        except ValueError:
            return self.reply(400, {"error": "the body must be JSON"})
        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            return self.reply(400, {"error": "text is required"})
        text = text.strip()
        if len(text) > MAX_TEXT:
            return self.reply(400, {"error": f"text is longer than {MAX_TEXT} characters"})
        target = normalise_target(body.get("notify"))
        if body.get("notify") and not target:
            return self.reply(400, {"error": "notify is not a notify service name"})

        prepare = body.get("prepare") is True
        is_admin, name = (False, None) if prepare else who_asked(body.get("user_id"))
        title = (body.get("title") or "Voice: " + text)[:70]
        try:
            wait_for_opencode()
            sid = create_session(title)
            # Tracked before the request is sent: its first events must not be missed.
            track(sid, notify=target, title=title, waiting=not is_admin and not prepare, busy=False, done=False)
            if prepare:
                call("POST", f"{OPENCODE}/session/{sid}/prompt_async",
                     {"noReply": True, "parts": [{"type": "text", "text": text}]})
                return self.reply(202, {"session_id": sid, "waiting_for_admin": False, "prepared": True, "url": panel_url()})
            send_request(sid, text, is_admin, name)  # once: a retry could run the job twice
        except Exception as e:  # noqa: BLE001
            log(f"could not start a session: {e}")
            return self.reply(502, {"error": "OpenCode did not take the request"})
        if is_admin:
            notify(sid, target, "Housemate started a job", f"{title}")
        else:
            notify(sid, target, "Housemate: a job is waiting for an admin",
                   f"{name or 'Someone'} asked: {text[:200]}. It is waiting in the chat for an administrator.")
        self.reply(202, {"session_id": sid, "waiting_for_admin": not is_admin, "url": panel_url()})


class Server(ThreadingHTTPServer):
    def verify_request(self, request, client_address):
        if client_address[0] in ALLOWED:
            return True
        log(f"refused a connection from {client_address[0]}")
        return False


def main():
    load_state()
    threading.Thread(target=watch_events, daemon=True).start()
    log(f"listening on {LISTEN[0]}:{LISTEN[1]}")
    Server(LISTEN, Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
