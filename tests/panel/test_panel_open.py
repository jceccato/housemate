"""Which chat the panel opens: a marked one once, the welcome chat on a first run, else none."""

import json
import os
import pathlib
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "housemate_edge/rootfs/usr/lib/housemate"))
import panel_open  # noqa: E402


class Server(BaseHTTPRequestHandler):
    sessions = []
    posts = []

    def log_message(self, *a):
        pass

    def send(self, body, code=200):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.send([{"id": s} for s in Server.sessions])

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"null")
        Server.posts.append((self.path, body))
        if self.path == "/session":
            Server.sessions.append("ses_welcome")
            self.send({"id": "ses_welcome"})
        else:
            self.send(None, 204)


class Take(unittest.TestCase):
    def setUp(self):
        Server.sessions, Server.posts = ["ses_old", "ses_job"], []
        self.srv = HTTPServer(("127.0.0.1", 0), Server)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, value in (("OPENCODE", f"http://127.0.0.1:{self.srv.server_port}"),
                            ("MARK", f"{tmp.name}/c/.housemate/current-session"),
                            ("WELCOME", f"{tmp.name}/c/.housemate/welcome-session"),
                            ("SEEN", f"{tmp.name}/d/seen")):
            old = getattr(panel_open, name)
            setattr(panel_open, name, value)
            self.addCleanup(setattr, panel_open, name, old)

    def mark(self, sid):
        panel_open.write(panel_open.MARK, sid)

    def test_a_marked_chat_is_taken_once_and_taken_again_when_marked_again(self):
        self.mark("ses_job")
        self.assertEqual(panel_open.take(lambda: "complete"), "ses_job")
        self.assertEqual(panel_open.take(lambda: "complete"), "")
        os.utime(panel_open.MARK, ns=(1, 1))
        self.assertEqual(panel_open.take(lambda: "complete"), "ses_job")

    def test_a_mark_for_a_chat_that_is_gone_is_ignored(self):
        self.mark("ses_gone")
        self.assertEqual(panel_open.take(lambda: "complete"), "")

    def test_a_first_run_starts_onboarding_in_a_titled_chat_once(self):
        self.assertEqual(panel_open.take(lambda: "new"), "ses_welcome")
        self.assertEqual(Server.posts[0], ("/session", {"title": "Welcome to Housemate"}))
        self.assertIn("onboarding", Server.posts[1][1]["parts"][0]["text"])
        self.assertEqual(panel_open.take(lambda: "new"), "")  # made already: the launcher's usual chat is it
        self.assertEqual(len(Server.posts), 2)

    def test_onboarding_begun_declined_or_complete_starts_nothing(self):
        for status in ("in_progress", "complete", "declined"):
            self.assertEqual(panel_open.take(lambda s=status: s), "")
        self.assertEqual(Server.posts, [])

    def test_a_marked_chat_wins_over_the_welcome(self):
        self.mark("ses_job")
        self.assertEqual(panel_open.take(lambda: "new"), "ses_job")


if __name__ == "__main__":
    unittest.main()
