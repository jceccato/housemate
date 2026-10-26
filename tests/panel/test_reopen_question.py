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

    chats = [{"id": "ses_a", "title": "Sunset light"}, {"id": "ses_b", "title": "Bins"}, {"id": "ses_c", "title": "Quiet"}]

    def do_GET(self):
        self.reply({"/question": Server.pending, "/session": Server.chats}.get(self.path))

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


class Watch(unittest.TestCase):
    """The panel follows the chat on screen (its terminal title) and asks again once per unseen question."""

    def setUp(self):
        Reopen.setUp(self)

    def run_watch(self, titles):
        titles = list(titles)
        state = {"i": 0}

        def alive():
            return state["i"] < len(titles)

        def title():
            t = titles[state["i"]]
            state["i"] += 1
            return t

        reopen_question.watch(self.base, "s-x", title, alive, sleep=lambda s: None)

    def asked_again(self):
        return [p for p, _ in Server.calls if p.endswith("/prompt_async")]

    def test_opening_on_a_chat_with_a_waiting_question_asks_again(self):
        self.run_watch(["OpenCode", "OC | Sunset light", "OC | Sunset light"])
        self.assertEqual(self.asked_again(), ["/session/ses_a/prompt_async"])

    def test_switching_to_another_chat_with_a_waiting_question_asks_again_there(self):
        self.run_watch(["OC | Quiet", "OC | Quiet", "OC | Bins", "OC | Bins"])
        self.assertEqual(self.asked_again(), ["/session/ses_b/prompt_async"])

    def test_a_question_asked_while_the_chat_was_on_screen_is_not_asked_again_on_return(self):
        Server.pending = []
        titles = iter(["OC | Sunset light", "OC | Sunset light", "OC | Quiet", "OC | Sunset light", "OC | Sunset light"])
        seq = list(titles)
        state = {"i": 0}

        def title():
            t = seq[state["i"]]
            state["i"] += 1
            if state["i"] == 2:  # the question arrives while the chat is on screen
                Server.pending = [{"id": "que_live", "sessionID": "ses_a"}]
            return t

        reopen_question.watch(self.base, "s-x", title, lambda: state["i"] < len(seq), sleep=lambda s: None)
        self.assertEqual(self.asked_again(), [])

    def test_a_terminal_that_is_not_showing_a_chat_does_nothing(self):
        self.run_watch(["bash", "OpenCode", ""])
        self.assertEqual(Server.calls, [])


if __name__ == "__main__":
    unittest.main()
