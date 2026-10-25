#!/usr/bin/env python3
"""Send commands to Home Assistant's websocket API and print the replies as JSON.

    ha_ws.py '{"type": "config/area_registry/list"}'
    ha_ws.py '{"type": "render_template", "template": "{{ states(\\"sun.sun\\") }}"}' --events 1

Several commands may be given; each is sent in turn and its result printed on
one line. A refused command prints {"error": ...} and the exit status is 1.
Inside the Housemate add-on no setup is needed: it connects to
ws://supervisor/core/websocket with $SUPERVISOR_TOKEN. Elsewhere set
HA_WS_URL (ws://host:8123/api/websocket) and HA_TOKEN (a long-lived token).
The token is read from the environment and never printed.

Only the standard library is used: Home Assistant images carry no websocket
client, and the handshake and framing needed here are small.
"""

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import urllib.parse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class Socket:
    def __init__(self, url, timeout):
        parts = urllib.parse.urlparse(url)
        if parts.scheme != "ws":
            sys.exit("ha_ws: only ws:// is supported (inside the add-on and on a home network it is plain)")
        self.sock = socket.create_connection((parts.hostname, parts.port or 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = parts.path or "/"
        self.sock.sendall(
            (
                f"GET {path} HTTP/1.1\r\nHost: {parts.netloc}\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                sys.exit("ha_ws: connection closed during the handshake")
            head += chunk
        head, _, self.buffer = head.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0]:
            sys.exit(f"ha_ws: handshake refused: {lines[0]}")
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        if f"sec-websocket-accept: {accept}".lower() not in head.decode("latin-1").lower():
            sys.exit("ha_ws: bad handshake reply")

    def _read(self, n):
        while len(self.buffer) < n:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                sys.exit("ha_ws: timed out waiting for Home Assistant (for --events, fewer events came than asked for)")
            if not chunk:
                sys.exit("ha_ws: connection closed")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def send(self, obj):
        payload = json.dumps(obj).encode()
        header = bytearray([0x81])
        if len(payload) < 126:
            header.append(0x80 | len(payload))
        elif len(payload) < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(payload))
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", len(payload))
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def receive(self):
        """The next JSON message, joining fragments and skipping pings."""
        message = b""
        while True:
            first, second = self._read(2)
            length = second & 0x7F
            if length == 126:
                (length,) = struct.unpack(">H", self._read(2))
            elif length == 127:
                (length,) = struct.unpack(">Q", self._read(8))
            data = self._read(length)
            opcode = first & 0x0F
            if opcode == 0x8:
                sys.exit("ha_ws: the server closed the connection")
            if opcode == 0x9:
                continue  # a ping
            message += data
            if first & 0x80:
                return json.loads(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("commands", nargs="+", help="one JSON object per command, without an id")
    parser.add_argument("--events", type=int, default=0, help="after a subscribing command, wait for this many events too")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()

    token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HA_TOKEN")
    if not token:
        sys.exit("ha_ws: no token: SUPERVISOR_TOKEN (inside the add-on) or HA_TOKEN is not set")
    url = os.environ.get("HA_WS_URL") or "ws://supervisor/core/websocket"

    ws = Socket(url, args.timeout)
    ws.receive()  # auth_required
    ws.send({"type": "auth", "access_token": token})
    reply = ws.receive()
    if reply.get("type") != "auth_ok":
        sys.exit(f"ha_ws: authentication failed: {reply.get('message', reply.get('type'))}")

    failed = False
    for number, raw in enumerate(args.commands, start=1):
        command = json.loads(raw)
        command["id"] = number
        ws.send(command)
        events = 0
        while True:
            reply = ws.receive()
            if reply.get("id") != number:
                continue
            if reply["type"] == "event":
                print(json.dumps(reply["event"]))
                events += 1
                if events >= args.events:
                    break
                continue
            ok = reply.get("success", True)
            failed = failed or not ok
            print(json.dumps(reply.get("result") if ok else {"error": reply.get("error")}))
            if args.events and ok and events < args.events:
                continue
            break
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
