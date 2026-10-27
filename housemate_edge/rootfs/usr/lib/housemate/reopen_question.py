"""Show a pending question to a panel that opened after it was asked.

OpenCode 1.19.4 shows a question only to a client that is attached when it is
asked; a client that attaches later is not told (the question stays pending on
the server, and the chat just says "Asked 1 question"). A job started by voice
or by the update review runs with no client, so a question it asks before the
person opens the panel would never be seen.

The launcher (housemate-agent) starts a watcher with the panel. The panel's
terminal title names the chat on screen ("OC | <title>"): when it changes to a
chat that has a question pending which this panel has not already seen, the
question is dismissed and the agent is asked to put it again, which the
attached panel shows. That covers opening the panel on a chat and switching
chats inside it. Nothing else is touched.

    reopen_question.py <opencode url> <session id>          once, for that chat
    reopen_question.py watch <opencode url> <tmux session>  until the panel closes
"""

import json
import re
import subprocess
import sys
import time
import urllib.request

TITLE_PREFIX = "OC | "

ASK_AGAIN = (
    "The person has just opened this chat. Ask your question again now, with the "
    "question tool, exactly as before, and wait for the answer."
)


def call(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        text = r.read().decode()
    return json.loads(text) if text else None


def pending(base, session):
    return [q for q in (call(base + "/question") or []) if q.get("sessionID") == session]


def reopen(base, session):
    """Dismiss the chat's pending question and ask the agent to ask again. Returns how many."""
    found = pending(base, session)
    if not found:
        return 0
    for q in found:
        call(f"{base}/question/{q['id']}/reject", "POST", {})
    call(f"{base}/session/{session}/prompt_async", "POST", {"parts": [{"type": "text", "text": ASK_AGAIN}]})
    return len(found)


def chat_on_screen(title):
    """The chat title in the panel's terminal title, or None."""
    return title[len(TITLE_PREFIX):] if title.startswith(TITLE_PREFIX) else None


def same_title(on_screen, title):
    """OpenCode shortens a long chat title in the terminal's title with an ellipsis, so a title
    that ends in one matches by its start."""
    if on_screen == title:
        return True
    if on_screen.endswith("\u2026") or on_screen.endswith("..."):
        stem = on_screen.rstrip(".\u2026").rstrip()
        return bool(stem) and title.startswith(stem)
    return False


def unseen_in(base, chat_ids, seen):
    """Questions pending in those chats which this panel has not seen."""
    return [q for q in (call(base + "/question") or []) if q.get("sessionID") in chat_ids and q["id"] not in seen]


def chats_called(base, title):
    return [c["id"] for c in (call(base + "/session") or []) if same_title(title, c.get("title") or "")]


def watch(base, tmux_session, pane_title, alive, sleep=time.sleep, every=2, opened_on=None):
    """Follow the chat on screen. `pane_title()` and `alive()` are the terminal's, injected for tests.
    A tab opened on a known chat (`opened_on`, from the tab's own name) starts with that chat as the one
    on screen, whatever its title looks like; after that the terminal title says which chat it is."""
    seen, last, on_screen = set(), None, None
    first_title = None
    while alive():
        try:
            title = pane_title()
            name = chat_on_screen(title)
            if opened_on and last is None:
                chats = [opened_on]
                first_title = name
                last = name or ""
                on_screen = chats
                for q in unseen_in(base, chats, seen):
                    reopen(base, q["sessionID"])
                    seen.add(q["id"])
            elif name is not None and name != last:
                last = name
                on_screen = chats_called(base, name)
                for q in unseen_in(base, on_screen, seen):
                    reopen(base, q["sessionID"])
                    seen.add(q["id"])
            if on_screen:
                # what is pending on the chat being looked at was seen when it was asked
                seen.update(q["id"] for q in unseen_in(base, on_screen, seen))
        except Exception as e:  # noqa: BLE001 - the panel works without this
            print(f"reopen_question: {e}", file=sys.stderr)
        sleep(every)


def tmux_watch(base, session):
    sock = ["tmux", "-L", "housemate"]

    def pane_title():
        return subprocess.run(sock + ["display-message", "-p", "-t", "=" + session + ":", "#{pane_title}"],
                              capture_output=True, text=True, timeout=5).stdout.strip()

    def alive():
        return subprocess.run(sock + ["has-session", "-t", "=" + session], capture_output=True).returncode == 0

    key = re.fullmatch(r"s-(ses_[A-Za-z0-9]+)", session)
    watch(base, session, pane_title, alive, opened_on=key.group(1) if key else None)


def main(argv):
    if len(argv) == 4 and argv[1] == "watch":
        tmux_watch(argv[2].rstrip("/"), argv[3])
        return 0
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        n = reopen(argv[1].rstrip("/"), argv[2])
    except Exception as e:  # noqa: BLE001 - the panel works without this
        print(f"reopen_question: {e}", file=sys.stderr)
        return 1
    if n:
        print(f"reopen_question: asked again ({n} pending)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
