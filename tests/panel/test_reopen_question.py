"""A question asked before the panel opened is put to the panel again."""

import json
import pathlib
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "housemate_edge/rootfs/usr/lib/housemate"))
import reopen_question  # noqa: E402


class Server(BaseHTTPRequestHandler):
    pending = []
    calls = []

    def log_message(self, *a):
        pass

    def reply(self, body=None, code=200):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(Server.pending if self.path == "/question" else None)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"null")
        Server.calls.append((self.path, body))
        self.reply(True if "/reject" in self.path else None, 200 if "/reject" in self.path else 204)


class Reopen(unittest.TestCase):
    def setUp(self):
        Server.pending = [{"id": "que_1", "sessionID": "ses_a"}, {"id": "que_2", "sessionID": "ses_b"}]
        Server.calls = []
        self.srv = HTTPServer(("127.0.0.1", 0), Server)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def test_a_pending_question_is_dismissed_and_asked_again_in_that_chat_only(self):
        self.assertEqual(reopen_question.reopen(self.base, "ses_a"), 1)
        paths = [p for p, _ in Server.calls]
        self.assertEqual(paths, ["/question/que_1/reject", "/session/ses_a/prompt_async"])
        self.assertIn("question tool", Server.calls[1][1]["parts"][0]["text"])

    def test_no_pending_question_means_nothing_is_sent(self):
        self.assertEqual(reopen_question.reopen(self.base, "ses_c"), 0)
        self.assertEqual(Server.calls, [])

    def test_a_server_that_is_not_there_is_not_an_error_for_the_panel(self):
        self.assertEqual(reopen_question.main(["x", "http://127.0.0.1:9", "ses_a"]), 1)


if __name__ == "__main__":
    unittest.main()
